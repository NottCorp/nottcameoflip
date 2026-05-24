"""Writer protocol + shared serialization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from cameo_convert.model import Card, Flag, InvertedDataset


class Writer(Protocol):
    extension: str
    name: str

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        ...


def dataset_to_dict(dataset: InvertedDataset) -> dict:
    """Canonical nested dict matching the JSON schema in §6.4."""
    return {
        "metadata": metadata_dict(dataset),
        "cards": {
            key: card_to_dict(card) for key, card in sorted(dataset.cards.items())
        },
    }


def metadata_dict(dataset: InvertedDataset) -> dict:
    return {
        "source_file": dataset.source_file,
        "source_last_updated": dataset.source_last_updated,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generator_version": dataset.generator_version,
        "release_tag": dataset.release_tag,
        "variant": dataset.variant,
        "total_cards": dataset.total_cards,
        "total_cameo_entries": dataset.total_cameo_entries,
    }


def card_to_dict(card: Card) -> dict:
    return {
        "card_name": card.card_name,
        "set": card.set_name,
        "collector_number": card.collector_number,
        "artwork_group_id": card.artwork_group_id,
        "primary_pokemons": list(card.primary_pokemons),
        "cameos": [cameo_to_dict(c) for c in card.cameos],
    }


def cameo_to_dict(cameo) -> dict:
    return {
        "subject": cameo.subject,
        "parent_species": cameo.parent_species,
        "kind": cameo.kind,
        "ndex": cameo.ndex,
        "region": cameo.region,
        "notes": cameo.notes,
        "flags": sorted(f.value for f in cameo.flags),
    }


# Flat-format columns used by csv/tsv/xlsx/ods/txt/md.
FLAT_COLUMNS = [
    "card_name",
    "primary_pokemons",
    "set",
    "collector_number",
    "artwork_group_id",
    "subject",
    "relation",  # "literal" or "species_parent" — distinguishes D7 double-rows
    "kind",
    "ndex",
    "region",
    "notes",
    "flags",
]


def flat_rows(dataset: InvertedDataset) -> Iterator[dict]:
    """Yield one (card, cameo) row per source entry; for different-form
    cameos emit a second row with relation=species_parent per D7.
    """
    for key in sorted(dataset.cards):
        card = dataset.cards[key]
        for cameo in card.cameos:
            yield _flat_row(card, cameo, subject=cameo.subject, relation="literal")
            if cameo.parent_species and cameo.parent_species != cameo.subject:
                yield _flat_row(
                    card,
                    cameo,
                    subject=cameo.parent_species,
                    relation="species_parent",
                )


_GENERIC_BUCKET = "(no primary Pokémon)"


def group_by_primary_pokemon(
    dataset: InvertedDataset,
) -> list[tuple[str, list[Card]]]:
    """Bucket cards by their primary Pokémon. Cards with multiple primaries
    (e.g. "Reshiram & Zekrom-GX") appear in each bucket. Cards with no primary
    go in a final generic bucket. Within each bucket: sort by set then card.
    Returns buckets sorted by lowest cameo ndex (proxy for Pokédex ordering),
    then alphabetically; generic bucket always last.
    """
    buckets: dict[str, list[Card]] = {}
    bucket_min_ndex: dict[str, int] = {}
    for card in dataset.cards.values():
        keys = card.primary_pokemons if card.primary_pokemons else [_GENERIC_BUCKET]
        for k in keys:
            buckets.setdefault(k, []).append(card)
            # Track the lowest ndex appearing in any cameo of any card under
            # this bucket — proxy for Pokédex ordering.
            for cameo in card.cameos:
                if cameo.ndex is not None:
                    cur = bucket_min_ndex.get(k)
                    if cur is None or cameo.ndex < cur:
                        bucket_min_ndex[k] = cameo.ndex
    sorted_buckets = sorted(
        buckets.keys(),
        key=lambda k: (
            k == _GENERIC_BUCKET,  # generic bucket always last
            bucket_min_ndex.get(k, 10**9),  # no ndex info → alpha sort
            k.lower(),
        ),
    )
    return [
        (
            k,
            sorted(
                buckets[k],
                key=lambda c: (
                    c.set_name,
                    c.card_name or "",
                    c.collector_number,
                ),
            ),
        )
        for k in sorted_buckets
    ]


def _flat_row(card: Card, cameo, *, subject: str, relation: str) -> dict:
    return {
        "card_name": card.card_name or "",
        "primary_pokemons": ",".join(card.primary_pokemons),
        "set": card.set_name,
        "collector_number": card.collector_number,
        "artwork_group_id": card.artwork_group_id or "",
        "subject": subject,
        "relation": relation,
        "kind": cameo.kind,
        "ndex": cameo.ndex if cameo.ndex is not None else "",
        "region": cameo.region or "",
        "notes": cameo.notes or "",
        "flags": ",".join(sorted(f.value for f in cameo.flags)),
    }
