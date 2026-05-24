"""Generate the GitHub Pages site under _site/.

Fetches releases via the GitHub REST API, downloads the latest published
release's clean-variant JSON asset for inline browsing, copies web/* into
the output directory, and writes data/{releases.json,cards.json}.

Usage:
    python scripts/build_site.py --out _site/

Environment:
    GITHUB_TOKEN       Token for GitHub API (falls back to `gh auth token`)
    GITHUB_REPOSITORY  owner/repo (defaults to NottCorp/nottcameoflip)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_REPO = "NottCorp/nottcameoflip"
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web"


def resolve_token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], check=True, capture_output=True, text=True
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def api_get(url: str, token: str | None, *, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def fetch_releases(repo: str, token: str | None) -> list[dict]:
    """Return all releases (paginated) for the repo, newest first."""
    out: list[dict] = []
    page = 1
    while True:
        url = f"{API}/repos/{repo}/releases?per_page=100&page={page}"
        try:
            raw = api_get(url, token)
        except urllib.error.HTTPError as e:
            print(f"warn: GitHub API returned {e.code} for {url}", file=sys.stderr)
            break
        batch = json.loads(raw)
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def slim_release(r: dict) -> dict:
    """Project a release record down to what the page needs."""
    return {
        "tag_name": r.get("tag_name"),
        "name": r.get("name"),
        "html_url": r.get("html_url"),
        "draft": r.get("draft", False),
        "prerelease": r.get("prerelease", False),
        "published_at": r.get("published_at"),
        "created_at": r.get("created_at"),
        "body": r.get("body", ""),
        "assets": [
            {
                "name": a.get("name"),
                "size": a.get("size"),
                "content_type": a.get("content_type"),
                "browser_download_url": a.get("browser_download_url"),
            }
            for a in r.get("assets", []) or []
        ],
    }


def pick_latest(releases: list[dict]) -> dict | None:
    for r in releases:
        if not r.get("draft") and not r.get("prerelease"):
            return r
    return releases[0] if releases else None


def find_clean_json_asset(release: dict) -> dict | None:
    tag = release.get("tag_name") or ""
    expected = f"cameo-convert-{tag}-cards-clean.json"
    for a in release.get("assets", []) or []:
        if a.get("name") == expected:
            return a
    # Tolerate variant without tag in name.
    for a in release.get("assets", []) or []:
        if a.get("name") == "cameo-convert-cards-clean.json":
            return a
    return None


def download(url: str, token: str | None) -> bytes:
    return api_get(url, token, accept="application/octet-stream")


def copy_web_sources(out: Path) -> None:
    if not WEB_SRC.is_dir():
        raise SystemExit(f"web/ source dir not found at {WEB_SRC}")
    for item in WEB_SRC.iterdir():
        dest = out / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def empty_cards_payload() -> dict:
    return {
        "metadata": {
            "total_cards": 0,
            "total_cameo_entries": 0,
            "source_last_updated": "—",
            "generated_at": None,
            "note": "No published release yet — publish a tag to populate this view.",
        },
        "cards": {},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="_site", help="Output directory (default: _site)")
    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO),
        help="owner/repo (default from $GITHUB_REPOSITORY or NottCorp/nottcameoflip)",
    )
    args = ap.parse_args(argv)

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    token = resolve_token()
    if not token:
        print(
            "warn: no GITHUB_TOKEN/GH_TOKEN and `gh auth token` failed; "
            "API calls will be unauthenticated (rate-limited)",
            file=sys.stderr,
        )

    print(f"Fetching releases for {args.repo}…", file=sys.stderr)
    releases_raw = fetch_releases(args.repo, token)
    releases = [slim_release(r) for r in releases_raw if not r.get("draft")]
    print(f"  {len(releases)} non-draft release(s)", file=sys.stderr)

    copy_web_sources(out)

    write_json(out / "data" / "releases.json", {"repo": args.repo, "releases": releases})

    latest = pick_latest(releases)
    cards_payload: dict | None = None
    if latest:
        asset = find_clean_json_asset(latest)
        if asset and asset.get("browser_download_url"):
            print(f"  downloading {asset['name']}…", file=sys.stderr)
            try:
                blob = download(asset["browser_download_url"], token)
                cards_payload = json.loads(blob.decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                print(f"warn: could not fetch clean JSON asset: {e}", file=sys.stderr)
        else:
            print(
                f"warn: no clean-variant JSON asset on {latest.get('tag_name')}",
                file=sys.stderr,
            )
    if cards_payload is None:
        cards_payload = empty_cards_payload()

    write_json(out / "data" / "cards.json", cards_payload)

    print(f"Site written to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
