from pathlib import Path

import tomli_w

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import card_to_dict, metadata_dict


class TomlWriter:
    name = "toml"
    extension = "toml"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        # TOML can't represent None natively. Replace with empty string /
        # empty list while serializing.
        def scrub(obj):
            if isinstance(obj, dict):
                return {k: scrub(v) for k, v in obj.items() if v is not None}
            if isinstance(obj, list):
                return [scrub(v) for v in obj]
            return obj

        meta = scrub(metadata_dict(dataset))
        # Build a TOML-friendly structure: [metadata] then an array of cards.
        out = {
            "metadata": meta,
            "cards": [
                {"key": key, **scrub(card_to_dict(dataset.cards[key]))}
                for key in sorted(dataset.cards)
            ],
        }
        path.write_bytes(tomli_w.dumps(out).encode("utf-8"))
