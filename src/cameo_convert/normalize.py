"""String normalization layers per design doc §6.8."""

from __future__ import annotations

import re
import unicodedata

_APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'"}
_GENDER = {"♀": "-f", "♂": "-m"}


def canonicalize(name: str) -> str:
    """Layer 1: display form. NFC + apostrophe fix + whitespace collapse."""
    s = unicodedata.normalize("NFC", name)
    for src, dst in _APOSTROPHES.items():
        s = s.replace(src, dst)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def match_key(name: str) -> str:
    """Layer 2: lookup form. Case- and accent-insensitive, alphanumeric only."""
    s = canonicalize(name)
    for src, dst in _GENDER.items():
        s = s.replace(src, dst)
    s = _strip_accents(s.casefold())
    return re.sub(r"[^a-z0-9]", "", s)


def slug(name: str) -> str:
    """Layer 3: filename/URL form. Hyphenated, lossy."""
    s = canonicalize(name)
    for src, dst in _GENDER.items():
        s = s.replace(src, dst)
    s = _strip_accents(s.casefold())
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# --- Card-name → primary Pokémon resolution ---
#
# Pokémon TCG card names embed species names with various decorations:
#   "Xerneas-EX"               (card variant suffix)
#   "Brock's Vulpix"           (Trainer possessive)
#   "Mega Charizard X"         (form prefix + form letter)
#   "Reshiram & Zekrom-GX"     (dual-name, both should count)
#   "Zoroark and Legendary Pokémon"  ("Legendary Pokémon" is not a species)
# card_primary_pokemons() strips the decorations and validates against the set
# of known species names so non-species fragments ("Legendary Pokémon",
# "Friends", trainer-only names) get dropped.

# Anchored at end of fragment, case-insensitive. Order matters: longest first
# so "VSTAR" beats "V", "V-UNION" beats "V", etc.
_CARD_VARIANT_SUFFIXES = [
    r"\s*V-UNION",
    r"\s*VSTAR",
    r"\s*VMAX",
    r"\s*BREAK",
    r"\s*LEGEND",
    r"\s+Prime",
    r"-EX",
    r"\s+EX",
    r"-GX",
    r"\s+GX",
    r"\s+ex",
    r"\s+V",
    r"\s+LV\.X",
    r"\s+δ",
    r"\s*[☆★]",
]
_VARIANT_SUFFIX_RE = re.compile(
    r"(?:" + "|".join(_CARD_VARIANT_SUFFIXES) + r")+$"
)

# Form prefixes that wrap a base species. "Mega Charizard X" → "Charizard"
# requires both prefix and trailing form-letter stripping; do them together.
_FORM_PREFIXES = [
    "Mega ",
    "Primal ",
    "Alolan ",
    "Galarian ",
    "Hisuian ",
    "Paldean ",
    "Gigantamax ",
    "Origin ",
    "Origin Forme ",
    "Dawn Wings ",
    "Dusk Mane ",
    "Ultra ",
    "Shadow ",
    "Dark ",
    "Light ",
    "Crystal ",
    "Radiant ",
    "Eternamax ",
]
_FORM_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _FORM_PREFIXES) + r")", re.IGNORECASE
)

# Mega trailing form letters: "Mega Charizard X" / "Mega Charizard Y".
_MEGA_FORM_LETTER_RE = re.compile(r"\s+[XY]$")

# Split a card name into species candidates. "Reshiram & Zekrom-GX" splits to
# two fragments; "Zoroark and Legendary Pokémon" splits to two fragments
# (the second gets filtered by known_species validation).
_SPLIT_RE = re.compile(r"\s+(?:&|and)\s+", re.IGNORECASE)

# Trainer possessive prefix: "Brock's Vulpix", "Illusion's Zorua",
# "Team Rocket's Meowth". Strip everything up to and including the "'s ".
_POSSESSIVE_RE = re.compile(r"^[^']+'s\s+")


def _strip_possessive(name: str) -> str:
    return _POSSESSIVE_RE.sub("", name)


def _strip_form_prefix(name: str) -> str:
    had_mega = name.lower().startswith("mega ") or name.lower().startswith("primal ")
    out = _FORM_PREFIX_RE.sub("", name)
    if had_mega:
        out = _MEGA_FORM_LETTER_RE.sub("", out)
    return out


def _strip_variant_suffix(name: str) -> str:
    # Apply repeatedly until stable — e.g. "Pikachu-EX V" should peel both.
    prev = None
    out = name
    while out != prev:
        prev = out
        out = _VARIANT_SUFFIX_RE.sub("", out).rstrip()
    return out


def _reduce_to_species(fragment: str) -> str:
    fragment = canonicalize(fragment)
    fragment = _strip_possessive(fragment)
    fragment = _strip_variant_suffix(fragment)
    fragment = _strip_form_prefix(fragment)
    fragment = _strip_variant_suffix(fragment)  # second pass after prefix strip
    return fragment.strip()


# Single-word or hyphenated Pokémon-shaped name (catches Alakazam, Ho-Oh).
# Used only as a heuristic to widen the species pool — see
# `discover_species_from_card_names`.
_POKEMON_NAME_SHAPE = re.compile(
    r"^[A-Z][a-z]+(?:-[A-Z][a-z]+)?$"
)


def card_primary_pokemons(
    card_name: str | None, known_species: set[str] | frozenset[str]
) -> list[str]:
    """Resolve a card name to the list of base Pokémon species it represents.

    Examples (assuming `known_species` contains the real species set):
        "Xerneas-EX"                      → ["Xerneas"]
        "Reshiram & Zekrom-GX"            → ["Reshiram", "Zekrom"]
        "Brock's Vulpix"                  → ["Vulpix"]
        "Mega Charizard X"                → ["Charizard"]
        "Zoroark and Legendary Pokémon"   → ["Zoroark"]
        "Pokémon Valley"                  → []
        None                              → []
    """
    if not card_name:
        return []
    species_by_key = {match_key(s): s for s in known_species if s}
    out: list[str] = []
    seen: set[str] = set()
    for fragment in _SPLIT_RE.split(card_name):
        reduced = _reduce_to_species(fragment)
        key = match_key(reduced)
        if key and key in species_by_key:
            canonical = species_by_key[key]
            if canonical not in seen:
                seen.add(canonical)
                out.append(canonical)
    return out


def discover_species_from_card_names(
    card_names, known_species: set[str] | frozenset[str]
) -> set[str]:
    """Extract additional Pokémon-shaped names from a pool of card names.

    Pokémon like Alakazam or Volcanion never appear as cameo subjects in
    RotomAmiti's source (they don't cameo on anyone else's card), so
    `known_species` from cameo entries misses them. But their *cards*
    ("Alakazam-EX", "Volcanion-EX") show up in the data — and after the
    standard reduce the leftover ("Alakazam", "Volcanion") looks Pokémon-shaped.

    This is a heuristic and *will* produce some false positives — e.g.
    "Zeraora and Friends" leaves "Friends" looking Pokémon-shaped, so "Friends"
    becomes a tentative species. The cost is one extra spurious bucket per
    false positive, which is preferable to losing Alakazam-EX entirely.
    """
    known_keys = {match_key(s) for s in known_species if s}
    extras: set[str] = set()
    for cn in card_names:
        if not cn:
            continue
        for fragment in _SPLIT_RE.split(cn):
            reduced = _reduce_to_species(fragment)
            if not reduced:
                continue
            key = match_key(reduced)
            if key in known_keys:
                continue
            if _POKEMON_NAME_SHAPE.match(reduced):
                extras.add(reduced)
    return extras
