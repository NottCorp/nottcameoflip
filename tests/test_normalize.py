import unicodedata

import pytest

from cameo_convert.normalize import (
    canonicalize,
    card_primary_pokemons,
    match_key,
    slug,
)


# Smart apostrophes spelled with escapes so this file is robust to editor reflow.
_RIGHT_SQ = "’"  # right single quotation mark
_LEFT_SQ = "‘"  # left single quotation mark
_MOD_APOS = "ʼ"  # modifier letter apostrophe
_FEMALE = "♀"
_MALE = "♂"

# Build NFD form of "Pokémon" explicitly so the canonicalize test really
# exercises NFC normalization regardless of how the source file was saved.
_POKEMON_NFD = unicodedata.normalize("NFD", "Pokémon")
_POKEMON_NFC = unicodedata.normalize("NFC", "Pokémon")


CANONICALIZE_CASES = [
    (f"Farfetch{_RIGHT_SQ}d", "Farfetch'd"),
    (f"Sirfetch{_RIGHT_SQ}d", "Sirfetch'd"),
    (f"{_LEFT_SQ}Pokemon{_RIGHT_SQ}", "'Pokemon'"),
    (f"Mime{_MOD_APOS}s", "Mime's"),
    (_POKEMON_NFD, _POKEMON_NFC),
    ("Mr.  Mime", "Mr. Mime"),
    ("  Pokémon  ", "Pokémon"),
]

MATCH_KEY_CASES = [
    ("Farfetch'd", "farfetchd"),
    ("Flabébé", "flabebe"),
    ("Mr. Mime", "mrmime"),
    ("Ho-Oh", "hooh"),
    ("Type: Null", "typenull"),
    ("Iron Jugulis", "ironjugulis"),
    ("Tapu Koko", "tapukoko"),
    ("Porygon-Z", "porygonz"),
    (f"Nidoran{_FEMALE}", "nidoranf"),
    (f"Nidoran{_MALE}", "nidoranm"),
    ("Pokémon", "pokemon"),
]

SLUG_CASES = [
    ("Farfetch'd", "farfetchd"),
    ("Sirfetch'd", "sirfetchd"),
    ("Iron Jugulis", "iron-jugulis"),
    ("Mr. Mime", "mr-mime"),
    ("Ho-Oh", "ho-oh"),
    ("Type: Null", "type-null"),
    ("Flabébé", "flabebe"),
    (f"Nidoran{_FEMALE}", "nidoran-f"),
    ("Tapu Koko", "tapu-koko"),
    ("Pokémon", "pokemon"),
    ("Tauros (Paldean Combat Breed)", "tauros-paldean-combat-breed"),
    ("Mime Jr.", "mime-jr"),
]


@pytest.mark.parametrize("inp,expected", CANONICALIZE_CASES)
def test_canonicalize(inp, expected):
    assert canonicalize(inp) == expected


@pytest.mark.parametrize("inp,expected", MATCH_KEY_CASES)
def test_match_key(inp, expected):
    assert match_key(inp) == expected


@pytest.mark.parametrize("inp,expected", SLUG_CASES)
def test_slug(inp, expected):
    assert slug(inp) == expected


@pytest.mark.parametrize(
    "name",
    [s for s, _ in CANONICALIZE_CASES + MATCH_KEY_CASES + SLUG_CASES],
)
def test_idempotence(name):
    assert canonicalize(canonicalize(name)) == canonicalize(name)
    assert match_key(match_key(name)) == match_key(name)
    assert slug(slug(name)) == slug(name)


def test_form_aware_warning_documented():
    # §6.8 edge case: form names do not equal parent species under match_key.
    assert match_key("Tauros (Paldean Combat Breed)") == "taurospaldeancombatbreed"
    assert match_key("Tauros") == "tauros"
    assert match_key("Tauros (Paldean Combat Breed)") != match_key("Tauros")


# A representative species pool used by all card_primary_pokemons tests.
_KNOWN_SPECIES = frozenset({
    "Bulbasaur",
    "Charizard",
    "Vulpix",
    "Pikachu",
    "Meowth",
    "Mewtwo",
    "Zorua",
    "Zoroark",
    "Xerneas",
    "Reshiram",
    "Zekrom",
    "Latias",
    "Latios",
    "Groudon",
    "Rayquaza",
})


CARD_PRIMARY_CASES = [
    # plain species name
    ("Pikachu", ["Pikachu"]),
    # card-variant suffixes
    ("Xerneas-EX", ["Xerneas"]),
    ("Charizard-GX", ["Charizard"]),
    ("Pikachu V", ["Pikachu"]),
    ("Charizard VMAX", ["Charizard"]),
    ("Mewtwo VSTAR", ["Mewtwo"]),
    ("Zoroark BREAK", ["Zoroark"]),
    ("Mewtwo ex", ["Mewtwo"]),
    # multi-name "X & Y" / "X and Y" — both species kept
    ("Reshiram & Zekrom-GX", ["Reshiram", "Zekrom"]),
    ("Latias and Latios", ["Latias", "Latios"]),
    # multi-name where second fragment is not a species
    ("Zoroark and Legendary Pokémon", ["Zoroark"]),
    # possessive ("Trainer's Pokémon" style)
    ("Brock's Vulpix", ["Vulpix"]),
    ("Illusion's Zorua", ["Zorua"]),
    ("N's Zoroark ex", ["Zoroark"]),
    ("Team Rocket's Meowth", ["Meowth"]),
    # form prefixes
    ("Mega Charizard X", ["Charizard"]),
    ("Mega Charizard Y", ["Charizard"]),
    ("Alolan Vulpix", ["Vulpix"]),
    ("Hisuian Zoroark", ["Zoroark"]),
    ("Primal Groudon", ["Groudon"]),
    # cards that aren't named after any Pokémon → empty list
    ("Pokémon Valley", []),
    ("Energy Switch", []),
    ("Town Volunteers", []),
    # edge: empty / None
    ("", []),
    (None, []),
]


@pytest.mark.parametrize("card_name,expected", CARD_PRIMARY_CASES)
def test_card_primary_pokemons(card_name, expected):
    assert card_primary_pokemons(card_name, _KNOWN_SPECIES) == expected


def test_card_primary_pokemons_preserves_canonical_species_spelling():
    # Even if the input casing differs, the returned name matches what's in
    # known_species (so downstream consumers can sort by Ndex via species map).
    assert card_primary_pokemons("XERNEAS-EX", _KNOWN_SPECIES) == ["Xerneas"]


def test_card_primary_pokemons_dedupes():
    # If the same species appears twice (e.g. "Pikachu & Pikachu") we don't
    # emit it twice.
    assert card_primary_pokemons("Pikachu & Pikachu", _KNOWN_SPECIES) == ["Pikachu"]
