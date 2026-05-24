import json
from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import dataset_to_dict


class JsonWriter:
    name = "json"
    extension = "json"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        path.write_text(
            json.dumps(dataset_to_dict(dataset), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
