import xml.etree.ElementTree as ET
from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import card_to_dict, metadata_dict


class XmlWriter:
    name = "xml"
    extension = "xml"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        root = ET.Element("cameo_database")
        meta_el = ET.SubElement(root, "metadata")
        for k, v in metadata_dict(dataset).items():
            child = ET.SubElement(meta_el, k)
            child.text = "" if v is None else str(v)
        cards_el = ET.SubElement(root, "cards")
        for key in sorted(dataset.cards):
            cd = card_to_dict(dataset.cards[key])
            card_el = ET.SubElement(cards_el, "card", attrib={"key": key})
            for field in ("card_name", "set", "collector_number", "artwork_group_id"):
                child = ET.SubElement(card_el, field)
                child.text = "" if cd[field] is None else str(cd[field])
            cameos_el = ET.SubElement(card_el, "cameos")
            for c in cd["cameos"]:
                cameo_el = ET.SubElement(cameos_el, "cameo")
                for field in ("subject", "parent_species", "kind", "ndex", "region", "notes"):
                    child = ET.SubElement(cameo_el, field)
                    child.text = "" if c[field] is None else str(c[field])
                flags_el = ET.SubElement(cameo_el, "flags")
                for f in c["flags"]:
                    flag_el = ET.SubElement(flags_el, "flag")
                    flag_el.text = f
        ET.indent(root, space="  ")
        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)
