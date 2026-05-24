"""Plain-text writer — grouped by primary Pokémon, one card per stanza."""

from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import group_by_primary_pokemon, metadata_dict


class TxtWriter:
    name = "txt"
    extension = "txt"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        meta = metadata_dict(dataset)
        lines: list[str] = []
        lines.append(f"# Cameo Pokémon Card Database — {dataset.variant} variant")
        lines.append(
            f"# Source: {meta['source_file']} | last updated {meta['source_last_updated']} | "
            f"release {meta['release_tag'] or '(local)'} | "
            f"{meta['total_cards']} cards | {meta['total_cameo_entries']} cameo entries"
        )
        lines.append("")

        for bucket_name, cards in group_by_primary_pokemon(dataset):
            lines.append(f"[{bucket_name}]")
            for card in cards:
                name = card.card_name or "(no card name)"
                lines.append(
                    f"{name} — {card.set_name} #{card.collector_number}:"
                )
                for c in card.cameos:
                    parent = (
                        f" (form of {c.parent_species})" if c.parent_species else ""
                    )
                    extras: list[str] = []
                    if c.ndex is not None:
                        extras.append(f"#{c.ndex}")
                    if c.region:
                        extras.append(c.region)
                    if c.notes:
                        extras.append(c.notes)
                    if c.flags:
                        extras.append("[" + ",".join(sorted(f.value for f in c.flags)) + "]")
                    extra_str = (" — " + " · ".join(extras)) if extras else ""
                    lines.append(f"    - {c.subject}{parent}{extra_str}")
                lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
