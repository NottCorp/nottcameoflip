from pathlib import Path

from cameo_convert.filter import clean, full
from cameo_convert.model import Flag
from cameo_convert.reader import read
from cameo_convert.transform import artwork_groups, card_identity, invert

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_sample.ods"


def _load():
    entries, meta = read(FIXTURE)
    return invert(
        entries,
        source_file=str(FIXTURE),
        source_last_updated=meta.last_updated,
    )


def test_card_identity_format():
    assert card_identity("Aquapolis", "Town Volunteers", "136") == "Aquapolis|Town Volunteers|136"
    assert card_identity("X", None, "1") == "X||1"


def test_invert_groups_by_card_identity():
    ds = _load()
    # Reprint group: 2 different collector numbers ⇒ 2 separate cards (D2).
    keys = {k for k in ds.cards if "Town Volunteers" in k}
    assert keys == {"Aquapolis|Town Volunteers|136", "Aquapolis Reprint|Town Volunteers|200"}


def test_invert_collapses_same_identity_to_one_card():
    # If two entries share the exact (set, card, #) they collapse to one Card
    # with both cameos in it. Build a hand-rolled example.
    from cameo_convert.model import CameoEntry

    e1 = CameoEntry(
        cameo_subject="Pikachu",
        parent_species=None,
        subject_kind="pokemon",
        ndex=25,
        region=None,
        card_name="Some Card",
        set_name="Some Set",
        collector_number="1",
        notes=None,
        flags=frozenset(),
        artwork_group_id=None,
    )
    e2 = CameoEntry(
        cameo_subject="Eevee",
        parent_species=None,
        subject_kind="pokemon",
        ndex=133,
        region=None,
        card_name="Some Card",
        set_name="Some Set",
        collector_number="1",
        notes=None,
        flags=frozenset(),
        artwork_group_id=None,
    )
    ds = invert([e1, e2], source_file="x")
    assert ds.total_cards == 1
    card = next(iter(ds.cards.values()))
    assert {c.subject for c in card.cameos} == {"Pikachu", "Eevee"}


def test_artwork_group_propagates():
    ds = _load()
    groups = artwork_groups(ds)
    # Town Volunteers group should have 2 cards
    matching = [g for g in groups.values() if len(g) == 2]
    assert matching, "expected at least one shared-artwork group with 2 cards"
    g = matching[0]
    assert all(c.card_name == "Town Volunteers" for c in g)


def test_clean_drops_italic_non_english_and_blank():
    ds = _load()
    cleaned = clean(ds)
    # Italic "Team Rocket's Meowth" must be gone.
    assert "Wizards Promos|Team Rocket's Meowth|18" not in cleaned.cards
    # Non-English JP-Only Card must be gone.
    assert "Japanese Set|JP-Only Card|JP1" not in cleaned.cards
    # Blank-card-name row from Trainers (Call of Legends) must be gone.
    assert all(c.card_name is not None for c in cleaned.cards.values())
    assert cleaned.variant == "clean"


def test_clean_keeps_regular_cards():
    ds = _load()
    cleaned = clean(ds)
    assert "Aquapolis|Town Volunteers|136" in cleaned.cards
    assert "Miscellaneous Promos|Pokémon Valley|-" in cleaned.cards  # Jumbo is not excluded


def test_full_passes_everything():
    ds = _load()
    f = full(ds)
    assert f.total_cards == ds.total_cards
    assert f.variant == "full"


def test_primary_pokemons_populated_for_named_cards():
    ds = _load()
    # Possessive Trainer card → species
    red_pikachu = ds.cards["SM-P Promos|Red's Pikachu|270"]
    assert red_pikachu.primary_pokemons == ["Pikachu"]
    # Italic edge-case Trainer card still gets primary
    meowth = ds.cards["Wizards Promos|Team Rocket's Meowth|18"]
    assert meowth.primary_pokemons == ["Meowth"]


def test_primary_pokemons_multi_for_dual_named_card():
    # "Bulbasaur & Ivysaur-GX" → both species
    ds = _load()
    dual = ds.cards["Cosmic Eclipse|Bulbasaur & Ivysaur-GX|999"]
    assert dual.primary_pokemons == ["Bulbasaur", "Ivysaur"]


def test_primary_pokemons_empty_for_generic_card_names():
    ds = _load()
    # "Pokémon Valley" isn't named after any species in known_species
    valley = ds.cards["Miscellaneous Promos|Pokémon Valley|-"]
    assert valley.primary_pokemons == []


def test_clean_preserves_non_english_reprint_sibling():
    ds = _load()
    cleaned = clean(ds)
    # "Reprint Test" exists as English Set #5 AND Japanese Set #JP5.
    # The Japanese sibling should survive Clean because its artwork-group
    # peer is English.
    assert "English Set|Reprint Test|5" in cleaned.cards
    assert "Japanese Set|Reprint Test|JP5" in cleaned.cards
    # ... but standalone non-English (JP-Only Card) is still dropped.
    assert "Japanese Set|JP-Only Card|JP1" not in cleaned.cards
