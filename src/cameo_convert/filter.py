"""Clean vs Full variant filters per design doc §6.2, D3, and the
reprint-sibling rule added in the second-pass plan."""

from __future__ import annotations

from cameo_convert.model import Card, Flag, InvertedDataset

_CLEAN_EXCLUDED_FLAGS = frozenset(
    {Flag.NON_ENGLISH, Flag.ITALIC, Flag.BLANK_CARD_NAME}
)


def _cameo_is_clean(cameo) -> bool:
    return not (cameo.flags & _CLEAN_EXCLUDED_FLAGS)


def _card_has_clean_cameo(card: Card) -> bool:
    return any(_cameo_is_clean(c) for c in card.cameos)


def clean(dataset: InvertedDataset) -> InvertedDataset:
    """English-only collector view (D3) with reprint-sibling preservation.

    Filtering rules:
    - Cards with no card_name (BLANK_CARD_NAME): always dropped.
    - A card whose artwork group has any English-only ("clean") sibling card
      is kept in full — all cameos preserved, even flagged ones. This is the
      "Town Volunteers (JP reprint) survives because Town Volunteers (EN)
      survives" rule.
    - All other cards have their cameos filtered by clean-excluded flags;
      cards left with zero cameos drop.
    """
    # Pre-compute which artwork groups have at least one fully-clean card.
    english_groups: set[str] = set()
    for card in dataset.cards.values():
        if card.artwork_group_id and card.card_name is not None and _card_has_clean_cameo(card):
            english_groups.add(card.artwork_group_id)

    new_cards: dict[str, Card] = {}
    for key, card in dataset.cards.items():
        if card.card_name is None:
            continue
        if card.artwork_group_id and card.artwork_group_id in english_groups:
            new_cards[key] = Card(
                card_name=card.card_name,
                set_name=card.set_name,
                collector_number=card.collector_number,
                artwork_group_id=card.artwork_group_id,
                cameos=list(card.cameos),
                primary_pokemons=list(card.primary_pokemons),
            )
            continue
        kept = [c for c in card.cameos if _cameo_is_clean(c)]
        if not kept:
            continue
        new_cards[key] = Card(
            card_name=card.card_name,
            set_name=card.set_name,
            collector_number=card.collector_number,
            artwork_group_id=card.artwork_group_id,
            cameos=kept,
            primary_pokemons=list(card.primary_pokemons),
        )
    return InvertedDataset(
        cards=new_cards,
        source_file=dataset.source_file,
        source_last_updated=dataset.source_last_updated,
        release_tag=dataset.release_tag,
        variant="clean",
        generator_version=dataset.generator_version,
    )


def full(dataset: InvertedDataset) -> InvertedDataset:
    """Pass through every entry with every flag preserved."""
    return InvertedDataset(
        cards=dict(dataset.cards),
        source_file=dataset.source_file,
        source_last_updated=dataset.source_last_updated,
        release_tag=dataset.release_tag,
        variant="full",
        generator_version=dataset.generator_version,
    )
