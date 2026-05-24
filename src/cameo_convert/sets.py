"""Set release-date resolver + fetcher.

Reads ``data/set_release_dates.json`` and resolves a source set name (as it
appears in RotomAmiti's spreadsheet) to a release date (YYYY-MM-DD).

The JSON file is keyed by ``slug(api_name)`` so it's grep-friendly and easy to
extend manually for sets the public API doesn't carry (Japanese promos,
championship decks, etc.).

CLI:

    python -m cameo_convert.sets fetch

Hits ``https://api.pokemontcg.io/v2/sets`` and merges into the existing JSON,
preserving any manually-added ``source_aliases`` and manual-only entries.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from cameo_convert.log import configure as configure_logging
from cameo_convert.log import get_logger
from cameo_convert.normalize import slug

log = get_logger(__name__)

API_URL = "https://api.pokemontcg.io/v2/sets"
DEFAULT_JSON_PATH = Path("data/set_release_dates.json")


@dataclass(frozen=True)
class SetEntry:
    slug: str
    release_date: str | None
    display_name: str
    series: str | None
    ptcgo_code: str | None
    source_aliases: tuple[str, ...]


class SetDateResolver:
    """Resolves source set names to release dates.

    Lookup order:
    1. ``slug(source_name)`` matches a key in ``sets``.
    2. ``source_name`` appears in any entry's ``source_aliases`` list.
    3. Returns ``None``.
    """

    def __init__(self, entries: Iterable[SetEntry]) -> None:
        self._by_slug: dict[str, SetEntry] = {}
        self._by_alias: dict[str, SetEntry] = {}
        for e in entries:
            self._by_slug[e.slug] = e
            for alias in e.source_aliases:
                self._by_alias[alias] = e

    def __call__(self, source_set_name: str) -> str | None:
        return self.release_date(source_set_name)

    def release_date(self, source_set_name: str) -> str | None:
        entry = self.entry(source_set_name)
        return entry.release_date if entry else None

    def entry(self, source_set_name: str) -> SetEntry | None:
        if not source_set_name:
            return None
        # Exact alias hit first — aliases are how operators express
        # "this source name is the same set as this api entry".
        e = self._by_alias.get(source_set_name)
        if e is not None:
            return e
        return self._by_slug.get(slug(source_set_name))

    def __len__(self) -> int:
        return len(self._by_slug)


def load(json_path: Path | str = DEFAULT_JSON_PATH) -> SetDateResolver:
    """Load the JSON file into a resolver. Missing file → empty resolver."""
    path = Path(json_path)
    if not path.exists():
        return SetDateResolver(())
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for s, body in data.get("sets", {}).items():
        entries.append(
            SetEntry(
                slug=s,
                release_date=body.get("release_date"),
                display_name=body.get("display_name") or s,
                series=body.get("series"),
                ptcgo_code=body.get("ptcgo_code"),
                source_aliases=tuple(body.get("source_aliases") or []),
            )
        )
    return SetDateResolver(entries)


def fetch_from_api(url: str = API_URL, timeout: float = 30.0) -> list[dict]:
    """GET pokemontcg.io's /v2/sets, return the raw list of set dicts."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "cameo-convert/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("data", [])


def _heuristic_aliases(name: str) -> list[str]:
    """Common patterns where the API name differs from RotomAmiti's source.

    Examples covered:
        "BW Black Star Promos" → "BW Promos"
        "Base" → "Base Set"
    Heuristics live here (not in the JSON) so re-fetches automatically include
    them. Operators add additional one-off aliases by editing the JSON.
    """
    aliases: list[str] = [name]
    if " Black Star Promos" in name:
        aliases.append(name.replace(" Black Star Promos", " Promos"))
    if name == "Base":
        aliases.append("Base Set")
    return aliases


def _api_to_entries(api_sets: list[dict]) -> dict[str, SetEntry]:
    """Convert raw pokemontcg.io set records to slug-keyed SetEntries."""
    out: dict[str, SetEntry] = {}
    for s in api_sets:
        name = s.get("name") or ""
        if not name:
            continue
        s_slug = slug(name)
        # Normalize release date YYYY/MM/DD → YYYY-MM-DD; some entries may be
        # missing or partially populated.
        raw = s.get("releaseDate") or ""
        release_date = raw.replace("/", "-") if raw else None
        out[s_slug] = SetEntry(
            slug=s_slug,
            release_date=release_date,
            display_name=name,
            series=s.get("series"),
            ptcgo_code=s.get("ptcgoCode"),
            source_aliases=tuple(_heuristic_aliases(name)),
        )
    return out


def merge(
    existing_resolver: SetDateResolver, fresh: dict[str, SetEntry]
) -> dict[str, SetEntry]:
    """Combine the on-disk JSON with a fresh API pull.

    Rules:
    - Keep every existing entry's ``source_aliases`` (operators add these by
      hand; we never drop them).
    - For overlapping slugs, the API supplies release_date / display_name /
      series / ptcgo_code; the existing aliases are unioned with API aliases.
    - Manual-only entries (slugs not in API) survive untouched.
    """
    out: dict[str, SetEntry] = {}
    # Start with everything from the existing file.
    for slug_key, entry in existing_resolver._by_slug.items():
        out[slug_key] = entry
    # Overlay fresh data.
    for slug_key, new_entry in fresh.items():
        prev = out.get(slug_key)
        if prev is None:
            out[slug_key] = new_entry
            continue
        merged_aliases = tuple(
            dict.fromkeys((*prev.source_aliases, *new_entry.source_aliases))
        )
        out[slug_key] = SetEntry(
            slug=slug_key,
            release_date=new_entry.release_date or prev.release_date,
            display_name=new_entry.display_name or prev.display_name,
            series=new_entry.series or prev.series,
            ptcgo_code=new_entry.ptcgo_code or prev.ptcgo_code,
            source_aliases=merged_aliases,
        )
    return out


def write(entries: dict[str, SetEntry], path: Path | str = DEFAULT_JSON_PATH) -> None:
    """Pretty-print the JSON, sorted by slug, with a _meta header."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "source": API_URL,
            "fetched_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "set_count": len(entries),
        },
        "sets": {
            s: {
                "release_date": e.release_date,
                "display_name": e.display_name,
                "series": e.series,
                "ptcgo_code": e.ptcgo_code,
                "source_aliases": list(e.source_aliases),
            }
            for s, e in sorted(entries.items())
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def cmd_fetch(args: argparse.Namespace) -> int:
    path = Path(args.json)
    log.info("fetching %s", API_URL)
    try:
        raw = fetch_from_api()
    except urllib.error.URLError as ex:
        log.critical("API request failed: %s", ex)
        return 1
    fresh = _api_to_entries(raw)
    log.info("received %d sets from API", len(fresh))
    existing = load(path)
    log.debug("existing JSON has %d sets", len(existing))
    merged = merge(existing, fresh)
    write(merged, path)
    log.info("wrote %s (%d sets total)", path, len(merged))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m cameo_convert.sets",
        description="Manage set release dates (fetch + merge from pokemontcg.io).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    fetch = sub.add_parser("fetch", help="Fetch from API and merge into the JSON file.")
    fetch.add_argument(
        "--json",
        default=str(DEFAULT_JSON_PATH),
        help=f"Path to the set_release_dates.json (default: {DEFAULT_JSON_PATH})",
    )
    fetch.set_defaults(func=cmd_fetch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
