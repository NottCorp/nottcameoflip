from pathlib import Path

import yaml

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import dataset_to_dict


class YamlWriter:
    name = "yaml"
    extension = "yaml"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        path.write_text(
            yaml.safe_dump(
                dataset_to_dict(dataset),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
