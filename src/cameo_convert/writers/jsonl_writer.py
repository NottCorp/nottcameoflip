import json
from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import card_to_dict, metadata_dict


class JsonlWriter:
    name = "jsonl"
    extension = "jsonl"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            # First line is the metadata record so streaming consumers can
            # detect variant/release before the data lines.
            f.write(json.dumps({"_metadata": metadata_dict(dataset)}, ensure_ascii=False) + "\n")
            for key in sorted(dataset.cards):
                record = {"key": key, **card_to_dict(dataset.cards[key])}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
