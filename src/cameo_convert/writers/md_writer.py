"""Markdown writer — grouped by primary Pokémon, then by card.

Cards with multiple primary_pokemons (e.g. "Reshiram & Zekrom-GX") appear
under each species' bucket. Generic Trainer cards with no primary go in a
trailing bucket so they're still browsable.
"""

from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import group_by_primary_pokemon, metadata_dict


class MarkdownWriter:
    name = "md"
    extension = "md"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        meta = metadata_dict(dataset)
        lines: list[str] = []
        lines.append(f"# Cameo Pokémon Card Database — {dataset.variant} variant")
        lines.append("")
        lines.append(
            f"_Source: `{meta['source_file']}` • last updated {meta['source_last_updated']} • "
            f"generated {meta['generated_at']} • release `{meta['release_tag']}` • "
            f"{meta['total_cards']} cards • {meta['total_cameo_entries']} cameo entries_"
        )
        lines.append("")
        lines.append(
            "_Cards are grouped by **primary Pokémon** — the species the card is "
            "named after. Multi-named cards (e.g. \"Reshiram & Zekrom-GX\") appear "
            "under each species._"
        )
        lines.append("")
        for bucket_name, cards in group_by_primary_pokemon(dataset):
            lines.append(f"## {bucket_name}")
            lines.append("")
            for card in cards:
                name = card.card_name or "_(no card name)_"
                lines.append(f"### {name} — {card.set_name} #{card.collector_number}")
                if card.artwork_group_id:
                    lines.append(f"_shared artwork group: `{card.artwork_group_id}`_")
                    lines.append("")
                lines.append("| Cameo | Kind | Ndex / Region | Notes | Flags |")
                lines.append("|---|---|---|---|---|")
                for c in card.cameos:
                    region_or_ndex = (
                        str(c.ndex) if c.ndex is not None else (c.region or "")
                    )
                    parent = (
                        f" (form of {c.parent_species})" if c.parent_species else ""
                    )
                    flags = ", ".join(sorted(f.value for f in c.flags)) or "—"
                    lines.append(
                        f"| {c.subject}{parent} | {c.kind} | {region_or_ndex} | "
                        f"{c.notes or ''} | {flags} |"
                    )
                lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
