import csv
from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import FLAT_COLUMNS, flat_rows


class CsvWriter:
    name = "csv"
    extension = "csv"
    delimiter = ","

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FLAT_COLUMNS, delimiter=self.delimiter)
            w.writeheader()
            for row in flat_rows(dataset):
                w.writerow(row)
