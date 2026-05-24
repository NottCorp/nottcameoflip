"""Writer registry.

To add a new format: create writers/{name}_writer.py exporting a class with
attributes `name`, `extension`, and method `write(dataset, path)`, then
register it here.
"""

from cameo_convert.writers.base import Writer
from cameo_convert.writers.csv_writer import CsvWriter
from cameo_convert.writers.html_writer import HtmlWriter
from cameo_convert.writers.json_writer import JsonWriter
from cameo_convert.writers.jsonl_writer import JsonlWriter
from cameo_convert.writers.md_writer import MarkdownWriter
from cameo_convert.writers.ods_writer import OdsWriter
from cameo_convert.writers.sqlite_writer import SqliteWriter
from cameo_convert.writers.toml_writer import TomlWriter
from cameo_convert.writers.tsv_writer import TsvWriter
from cameo_convert.writers.txt_writer import TxtWriter
from cameo_convert.writers.xlsx_writer import XlsxWriter
from cameo_convert.writers.xml_writer import XmlWriter
from cameo_convert.writers.yaml_writer import YamlWriter

REGISTRY: dict[str, type[Writer]] = {
    JsonWriter.name: JsonWriter,
    JsonlWriter.name: JsonlWriter,
    YamlWriter.name: YamlWriter,
    TomlWriter.name: TomlWriter,
    XmlWriter.name: XmlWriter,
    CsvWriter.name: CsvWriter,
    TsvWriter.name: TsvWriter,
    MarkdownWriter.name: MarkdownWriter,
    HtmlWriter.name: HtmlWriter,
    TxtWriter.name: TxtWriter,
    SqliteWriter.name: SqliteWriter,
    XlsxWriter.name: XlsxWriter,
    OdsWriter.name: OdsWriter,
}

ALL_FORMATS = tuple(REGISTRY.keys())

__all__ = ["REGISTRY", "ALL_FORMATS", "Writer"]
