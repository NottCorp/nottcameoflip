"""Invert per-Pokémon entries into per-card grouping per design doc §6.4.

D1: card identity = "Set|CardName|#" composite string.
D2: no reprint collapsing — every collector number gets its own Card entry;
    entries sharing the artwork_group_id remain grouped only via that ID.
"""

from __future__ import annotations

from cameo_convert.model import (
    Cameo,
    CameoEntry,
    Card,
    Flag,
    InvertedDataset,
)
from cameo_convert.normalize import (
    card_primary_pokemons,
    discover_species_from_card_names,
)


def card_identity(set_name: str, card_name: str | None, number: str) -> str:
    return f"{set_name}|{card_name or ''}|{number}"


def _known_species(entries: list[CameoEntry]) -> set[str]:
    """All Pokémon species names that appear in the source. Used by
    `card_primary_pokemons` to validate candidate fragments — without this
    filter, fragments like "Legendary Pokémon" or "Friends" would slip through.
    """
    species: set[str] = set()
    for e in entries:
        if e.subject_kind == "pokemon" and e.cameo_subject:
            species.add(e.cameo_subject)
        if e.parent_species:
            species.add(e.parent_species)
    return species


def invert(
    entries: list[CameoEntry],
    *,
    source_file: str,
    source_last_updated: str | None = None,
    release_tag: str = "",
    variant: str = "full",
    generator_version: str = "0.1.0",
) -> InvertedDataset:
    species = _known_species(entries)
    # Widen the species pool with names harvested from card names themselves
    # so cards like "Alakazam-EX" (where Alakazam never cameos) still resolve.
    species |= discover_species_from_card_names(
        {e.card_name for e in entries if e.card_name}, species
    )
    cards: dict[str, Card] = {}
    for e in entries:
        key = card_identity(e.set_name, e.card_name, e.collector_number)
        if key not in cards:
            cards[key] = Card(
                card_name=e.card_name,
                set_name=e.set_name,
                collector_number=e.collector_number,
                artwork_group_id=e.artwork_group_id,
                primary_pokemons=card_primary_pokemons(e.card_name, species),
            )
        if e.artwork_group_id and not cards[key].artwork_group_id:
            cards[key].artwork_group_id = e.artwork_group_id
        cards[key].cameos.append(
            Cameo(
                subject=e.cameo_subject,
                parent_species=e.parent_species,
                kind=e.subject_kind,
                ndex=e.ndex,
                region=e.region,
                notes=e.notes,
                flags=e.flags,
            )
        )
    return InvertedDataset(
        cards=cards,
        source_file=source_file,
        source_last_updated=source_last_updated,
        release_tag=release_tag,
        variant=variant,
        generator_version=generator_version,
    )


def artwork_groups(dataset: InvertedDataset) -> dict[str, list[Card]]:
    """Group cards by artwork_group_id. Useful for clients that want to
    collapse reprints (D2 leaves them un-collapsed by default).
    """
    out: dict[str, list[Card]] = {}
    for card in dataset.cards.values():
        if card.artwork_group_id:
            out.setdefault(card.artwork_group_id, []).append(card)
    return out
