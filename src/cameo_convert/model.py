"""Intermediate representation per design doc §6.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Flag(str, Enum):
    ITALIC = "italic"
    NON_ENGLISH = "non_english"
    JUMBO = "jumbo"
    BLANK_CARD_NAME = "blank_card"
    DIFFERENT_FORM = "different_form"
    SHARED_ARTWORK = "shared_artwork"


SubjectKind = Literal["pokemon", "trainer"]


@dataclass(frozen=True)
class CameoEntry:
    cameo_subject: str
    parent_species: str | None
    subject_kind: SubjectKind
    ndex: int | None
    region: str | None
    card_name: str | None
    set_name: str
    collector_number: str
    notes: str | None
    flags: frozenset[Flag]
    artwork_group_id: str | None
    bg_color_raw: str | None = None


@dataclass(frozen=True)
class Cameo:
    subject: str
    parent_species: str | None
    kind: SubjectKind
    ndex: int | None
    region: str | None
    notes: str | None
    flags: frozenset[Flag]


@dataclass
class Card:
    card_name: str | None
    set_name: str
    collector_number: str
    artwork_group_id: str | None
    cameos: list[Cameo] = field(default_factory=list)
    # Base Pokémon species the card is named after. Multi-named cards like
    # "Reshiram & Zekrom-GX" populate both. Generic Trainer cards: [].
    primary_pokemons: list[str] = field(default_factory=list)
    # YYYY-MM-DD release date, resolved via cameo_convert.sets.SetDateResolver
    # against data/set_release_dates.json. None if the source set name has no
    # matching entry (add a manual alias to fix one-off cases).
    release_date: str | None = None

    @property
    def identity(self) -> str:
        return f"{self.set_name}|{self.card_name or ''}|{self.collector_number}"


@dataclass
class InvertedDataset:
    cards: dict[str, Card]
    source_file: str
    source_last_updated: str | None = None
    release_tag: str = ""
    variant: str = "full"
    generator_version: str = "0.1.0"

    @property
    def total_cards(self) -> int:
        return len(self.cards)

    @property
    def total_cameo_entries(self) -> int:
        return sum(len(c.cameos) for c in self.cards.values())
