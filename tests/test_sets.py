import json
from pathlib import Path

from cameo_convert.sets import (
    SetDateResolver,
    SetEntry,
    _api_to_entries,
    _heuristic_aliases,
    load,
    merge,
    write,
)

FIXTURE = Path(__file__).parent / "fixtures" / "set_release_dates.json"


def test_resolver_slug_match():
    r = load(FIXTURE)
    assert r("Aquapolis") == "2003-01-15"
    assert r("Crown Zenith") == "2023-01-20"


def test_resolver_alias_match():
    r = load(FIXTURE)
    # Source name "SM-P Promos" doesn't slugify to "sm-black-star-promos"
    # but appears in the entry's source_aliases.
    assert r("SM-P Promos") == "2017-02-03"
    assert r("SM Promos") == "2017-02-03"


def test_resolver_returns_none_for_unknown():
    r = load(FIXTURE)
    assert r("Some Unreleased Set") is None
    assert r("") is None


def test_resolver_load_missing_file_yields_empty():
    r = load(Path("/nonexistent/path/that/does/not/exist.json"))
    assert len(r) == 0
    assert r("anything") is None


def test_api_to_entries_normalizes_date_format():
    raw = [
        {"name": "Test Set", "releaseDate": "2021/03/19", "series": "X", "ptcgoCode": "TS"},
        {"name": "Other", "releaseDate": "", "series": "X"},
    ]
    out = _api_to_entries(raw)
    assert out["test-set"].release_date == "2021-03-19"
    assert out["other"].release_date is None


def test_heuristic_aliases_for_black_star_promos():
    aliases = _heuristic_aliases("BW Black Star Promos")
    assert "BW Black Star Promos" in aliases
    assert "BW Promos" in aliases


def test_heuristic_aliases_for_base():
    aliases = _heuristic_aliases("Base")
    assert "Base Set" in aliases


def test_merge_preserves_manual_aliases(tmp_path):
    # Existing JSON has a manually-curated alias "MY SOURCE ALIAS"
    p = tmp_path / "existing.json"
    p.write_text(
        json.dumps({
            "_meta": {},
            "sets": {
                "aquapolis": {
                    "release_date": "2003-01-15",
                    "display_name": "Aquapolis (old)",
                    "series": "E-Card",
                    "ptcgo_code": "AQ",
                    "source_aliases": ["MY SOURCE ALIAS", "Aquapolis"],
                },
                "manual-only": {
                    "release_date": "1995-01-01",
                    "display_name": "Manual Only",
                    "series": "Manual",
                    "ptcgo_code": "MAN",
                    "source_aliases": ["Manual Only", "Manual Alias"],
                },
            },
        }),
        encoding="utf-8",
    )
    existing = load(p)
    fresh = _api_to_entries([
        {"name": "Aquapolis", "releaseDate": "2003-01-15", "series": "E-Card", "ptcgoCode": "AQ"},
        {"name": "Brand New Set", "releaseDate": "2026-05-01", "series": "SV", "ptcgoCode": "BNS"},
    ])
    merged = merge(existing, fresh)

    # Manual alias survives
    assert "MY SOURCE ALIAS" in merged["aquapolis"].source_aliases
    # New API set added
    assert "brand-new-set" in merged
    # Manual-only entry survived
    assert "manual-only" in merged


def test_write_then_load_roundtrip(tmp_path):
    entries = {
        "aquapolis": SetEntry(
            slug="aquapolis",
            release_date="2003-01-15",
            display_name="Aquapolis",
            series="E-Card",
            ptcgo_code="AQ",
            source_aliases=("Aquapolis",),
        ),
    }
    p = tmp_path / "out.json"
    write(entries, p)
    r = load(p)
    assert r("Aquapolis") == "2003-01-15"


def test_resolver_alias_beats_slug():
    # If a name matches BOTH a slug and an alias of a different entry,
    # alias should win (operator intent is explicit).
    entries = (
        SetEntry(
            slug="apple",
            release_date="1999-01-01",
            display_name="Apple",
            series=None,
            ptcgo_code=None,
            source_aliases=("Apple",),
        ),
        SetEntry(
            slug="banana",
            release_date="2020-01-01",
            display_name="Banana",
            series=None,
            ptcgo_code=None,
            source_aliases=("apple",),  # intentionally collides with apple slug
        ),
    )
    r = SetDateResolver(entries)
    # "apple" matches banana's alias exactly → 2020
    assert r("apple") == "2020-01-01"
    # "Apple" matches apple's slug
    assert r("Apple") == "1999-01-01"
