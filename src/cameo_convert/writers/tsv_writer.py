from cameo_convert.writers.csv_writer import CsvWriter


class TsvWriter(CsvWriter):
    name = "tsv"
    extension = "tsv"
    delimiter = "\t"
