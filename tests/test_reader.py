from pathlib import Path

import pytest

from cameo_convert.model import Flag
from cameo_convert.reader import read

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_sample.ods"


@pytest.fixture(scope="module")
def parsed():
    if not FIXTURE.exists():
        # Build on demand if not committed (e.g. fresh checkout).
        from tests.fixtures import build_tiny_sample

        build_tiny_sample.build(FIXTURE)
    entries, meta = read(FIXTURE)
    return entries, meta


def find(entries, **filters):
    out = [e for e in entries if all(getattr(e, k) == v for k, v in filters.items())]
    assert out, f"no entry matched {filters}"
    assert len(out) == 1, f"multiple entries matched {filters}: {out}"
    return out[0]


def test_entry_count(parsed):
    entries, _ = parsed
    # 9 Gen 1 entries (7 original + 2 reprint-sibling rows for Ivysaur's
    # "Reprint Test"), 2 Gen 10 entries (Futuremon + dual-name card),
    # 3 Trainers entries → 14.
    assert len(entries) == 14


def test_future_generation_picked_up_automatically(parsed):
    """If RotomAmiti adds a 'Gen 10' sheet later, the reader picks it up
    with no code change. _GEN_SHEET_RE matches any 'Gen <digits>'.
    """
    entries, _ = parsed
    futuremon = [e for e in entries if e.cameo_subject == "Futuremon"]
    # Now 2 entries: Future Card + the dual-named card under Futuremon's block.
    assert len(futuremon) == 2
    for e in futuremon:
        assert e.ndex == 1100
    cards = {e.card_name for e in futuremon}
    assert {"Future Card", "Bulbasaur & Ivysaur-GX"} == cards


def test_metadata(parsed):
    _, meta = parsed
    assert meta.last_updated == "2026-05-21"
    assert meta.up_to_date_with_set == "Chaos Rising"


def test_pokemon_block_merge_carries_ndex_and_species(parsed):
    entries, _ = parsed
    pokemon_entries = [e for e in entries if e.subject_kind == "pokemon"]
    bulb = [e for e in pokemon_entries if e.cameo_subject == "Bulbasaur"]
    assert len(bulb) == 4
    for e in bulb:
        assert e.ndex == 1


def test_jumbo_flag(parsed):
    entries, _ = parsed
    e = find(entries, card_name="Pokémon Valley")
    assert Flag.JUMBO in e.flags
    assert e.collector_number == "-"


def test_shared_artwork_two_rows_same_group(parsed):
    entries, _ = parsed
    reprints = [e for e in entries if e.card_name == "Town Volunteers"]
    assert len(reprints) == 2
    group_ids = {e.artwork_group_id for e in reprints}
    assert len(group_ids) == 1
    assert next(iter(group_ids)) is not None
    for e in reprints:
        assert Flag.SHARED_ARTWORK in e.flags


def test_italic_edge_case(parsed):
    entries, _ = parsed
    e = find(entries, card_name="Team Rocket's Meowth")
    assert Flag.ITALIC in e.flags
    assert e.notes == "silhouette"


def test_different_form_detected(parsed):
    entries, _ = parsed
    mega = [e for e in entries if e.cameo_subject == "Mega Bulbasaur"]
    assert len(mega) == 2
    for e in mega:
        assert Flag.DIFFERENT_FORM in e.flags
        assert e.parent_species == "Bulbasaur"
        assert e.ndex == 1


def test_non_english_via_parent_style_chain(parsed):
    entries, _ = parsed
    e = find(entries, card_name="JP-Only Card")
    assert Flag.NON_ENGLISH in e.flags


def test_non_numeric_collector_number(parsed):
    entries, _ = parsed
    e = find(entries, card_name="Some Galar Card")
    assert e.collector_number == "GG09"
    assert e.ndex == 2


def test_trainers_region_carries(parsed):
    entries, _ = parsed
    trainers = [e for e in entries if e.subject_kind == "trainer"]
    assert len(trainers) == 3
    assert all(e.region == "KANTO" for e in trainers)
    assert {e.cameo_subject for e in trainers} == {"Red", "Brock"}


def test_blank_card_name(parsed):
    entries, _ = parsed
    e = find(entries, set_name="Call of Legends")
    assert e.card_name is None
    assert Flag.BLANK_CARD_NAME in e.flags
