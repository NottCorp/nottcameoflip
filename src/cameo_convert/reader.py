"""ODS reader: source spreadsheet → list[CameoEntry].

Walks content.xml directly via xml.etree because we need cell formatting
(italic style, blue background) and merge geometry — pandas/odfpy's high-level
APIs drop both.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from cameo_convert.log import get_logger
from cameo_convert.model import CameoEntry, Flag

log = get_logger(__name__)

NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
NS_STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
NS_FO = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
NS_META = "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
NS_DC = "http://purl.org/dc/elements/1.1/"

NON_ENGLISH_BG = "#cfe2f3"

# Matches "Gen 1" through "Gen 99+" — Pokémon generations are added as new
# sheets in the source spreadsheet; this lets us pick them up automatically.
_GEN_SHEET_RE = re.compile(r"^Gen \d+$")

# Sentinel cap on how far a covered-cell repeat can extend in a row. Real data
# uses values like 1018 to fill out to the sheet width, which we'd otherwise
# allocate as empty list entries. 64 is generous for a 6-column sheet.
MAX_COL = 64


@dataclass
class _StyleProps:
    italic: bool = False
    bg_color: str | None = None


@dataclass
class _Cell:
    text: str
    style: str | None
    col_span: int
    row_span: int


@dataclass(frozen=True)
class SourceMetadata:
    last_updated: str | None  # YYYY-MM-DD from meta.xml dc:date
    up_to_date_with_set: str | None  # parsed from Main sheet, informational


def read(ods_path: str | Path) -> tuple[list[CameoEntry], SourceMetadata]:
    """Read an .ods file → (entries, source_metadata)."""
    ods_path = Path(ods_path)
    with zipfile.ZipFile(ods_path) as z:
        with z.open("content.xml") as f:
            content_tree = ET.parse(f)
        try:
            with z.open("meta.xml") as f:
                meta_tree = ET.parse(f)
        except KeyError:
            meta_tree = None

    styles = _build_style_map(content_tree.getroot())
    tables = content_tree.getroot().findall(f".//{{{NS_TABLE}}}table")

    log.debug("resolved %d cell styles from automatic-styles", len(styles))
    entries: list[CameoEntry] = []
    main_text = ""
    unknown_sheets: list[str] = []
    for tbl in tables:
        name = tbl.get(f"{{{NS_TABLE}}}name") or ""
        if name == "Main":
            main_text = _flatten_main(tbl)
            continue
        # Match "Gen 1" through "Gen 99" (and beyond) — future generations
        # are picked up automatically; no code change needed when Gen 10 lands.
        if _GEN_SHEET_RE.match(name):
            before = len(entries)
            entries.extend(_read_gen_sheet(name, tbl, styles))
            log.debug("sheet %s → %d entries", name, len(entries) - before)
        elif name == "Trainers":
            before = len(entries)
            entries.extend(_read_trainers_sheet(tbl, styles))
            log.debug("sheet %s → %d entries", name, len(entries) - before)
        else:
            unknown_sheets.append(name)
    if unknown_sheets:
        log.warning("ignoring unrecognized sheet(s): %r — add handling in reader.read() if these contain cameo data", unknown_sheets)

    last_updated = None
    if meta_tree is not None:
        d = meta_tree.find(f".//{{{NS_DC}}}date")
        if d is not None and d.text:
            last_updated = d.text.split("T", 1)[0]
    return entries, SourceMetadata(
        last_updated=last_updated,
        up_to_date_with_set=_extract_uptodate_set(main_text),
    )


def _build_style_map(root: ET.Element) -> dict[str, _StyleProps]:
    """Walk office:automatic-styles and resolve parent-style inheritance.

    Per appendix §12: italic detection keys off fo:font-style, bg color off
    fo:background-color. 117 styles in the real source have parents.
    """
    raw: dict[str, dict] = {}
    for ns_block in (
        root.findall(f"{{{NS_OFFICE}}}automatic-styles"),
        root.findall(f"{{{NS_OFFICE}}}styles"),
    ):
        for block in ns_block:
            for s in block.findall(f"{{{NS_STYLE}}}style"):
                name = s.get(f"{{{NS_STYLE}}}name")
                if not name:
                    continue
                parent = s.get(f"{{{NS_STYLE}}}parent-style-name")
                italic = None
                bg = None
                tp = s.find(f"{{{NS_STYLE}}}text-properties")
                if tp is not None:
                    fs = tp.get(f"{{{NS_FO}}}font-style")
                    if fs == "italic":
                        italic = True
                    elif fs is not None:
                        italic = False
                cp = s.find(f"{{{NS_STYLE}}}table-cell-properties")
                if cp is not None:
                    bg_val = cp.get(f"{{{NS_FO}}}background-color")
                    if bg_val is not None and bg_val != "transparent":
                        bg = bg_val
                raw[name] = {"parent": parent, "italic": italic, "bg": bg}

    resolved: dict[str, _StyleProps] = {}

    def resolve(name: str, seen: frozenset[str] = frozenset()) -> _StyleProps:
        if name in resolved:
            return resolved[name]
        if name in seen or name not in raw:
            return _StyleProps()
        r = raw[name]
        parent_props = (
            resolve(r["parent"], seen | {name}) if r["parent"] else _StyleProps()
        )
        italic = r["italic"] if r["italic"] is not None else parent_props.italic
        bg = r["bg"] if r["bg"] is not None else parent_props.bg_color
        out = _StyleProps(italic=italic, bg_color=bg)
        resolved[name] = out
        return out

    for name in raw:
        resolve(name)
    return resolved


def _cell_text(cell: ET.Element) -> str:
    parts: list[str] = []
    for p in cell.iter(f"{{{NS_TEXT}}}p"):
        parts.append("".join(p.itertext()))
    return "\n".join(parts).strip()


def _flatten_main(tbl: ET.Element) -> str:
    """Concatenate all text from the Main sheet for date extraction."""
    out: list[str] = []
    for row in tbl.findall(f"{{{NS_TABLE}}}table-row"):
        for cell in row.iter(f"{{{NS_TEXT}}}p"):
            txt = "".join(cell.itertext()).strip()
            if txt:
                out.append(txt)
    return " ".join(out)


_UPTODATE = re.compile(
    r"up[\s-]*to[\s-]*date with all English releases up to and including\s+([^.,]+?)[\.,]",
    re.IGNORECASE,
)


def _extract_uptodate_set(main_text: str) -> str | None:
    m = _UPTODATE.search(main_text)
    return m.group(1).strip() if m else None


def _walk_row(row: ET.Element) -> list[_Cell]:
    """Expand a row into a fixed-width cell list with merges left intact.

    Covered-table-cell placeholders are emitted as empty _Cells so column
    indices line up. number-columns-repeated on the trailing filler is capped
    at MAX_COL to avoid wasting memory on the 1000+ empty cells past the data.
    """
    cells: list[_Cell] = []
    for c in row:
        tag = c.tag
        if tag not in (
            f"{{{NS_TABLE}}}table-cell",
            f"{{{NS_TABLE}}}covered-table-cell",
        ):
            continue
        rep = int(c.get(f"{{{NS_TABLE}}}number-columns-repeated", "1"))
        col_span = int(c.get(f"{{{NS_TABLE}}}number-columns-spanned", "1"))
        row_span = int(c.get(f"{{{NS_TABLE}}}number-rows-spanned", "1"))
        style = c.get(f"{{{NS_TABLE}}}style-name")
        text = (
            _cell_text(c) if tag == f"{{{NS_TABLE}}}table-cell" else ""
        )
        # Cap trailing empty repeats so we don't allocate huge lists.
        if rep > 1 and not text and tag == f"{{{NS_TABLE}}}table-cell" and style is None:
            rep = min(rep, max(0, MAX_COL - len(cells)))
        for _ in range(rep):
            cells.append(_Cell(text=text, style=style, col_span=col_span, row_span=row_span))
            if len(cells) >= MAX_COL:
                return cells
    return cells


class _MergeTracker:
    """Per-column countdown of how many rows the current vertical merge covers."""

    def __init__(self) -> None:
        self.active: dict[int, tuple[str, str | None, int]] = {}
        # col_index -> (value, style, rows_remaining)

    def fill(self, row_cells: list[_Cell]) -> list[_Cell]:
        """Fill covered-cell slots from any active vertical merges."""
        out: list[_Cell] = []
        for i, c in enumerate(row_cells):
            if i in self.active:
                val, style, _ = self.active[i]
                out.append(_Cell(text=val, style=style, col_span=1, row_span=1))
            else:
                out.append(c)
        return out

    def record(self, row_cells: list[_Cell]) -> None:
        """Decrement active merges and register new ones from this row."""
        for i in list(self.active.keys()):
            val, style, remaining = self.active[i]
            remaining -= 1
            if remaining <= 0:
                del self.active[i]
            else:
                self.active[i] = (val, style, remaining)
        for i, c in enumerate(row_cells):
            if c.row_span > 1 and c.text:
                self.active[i] = (c.text, c.style, c.row_span - 1)


def _is_italic(style: str | None, styles: dict[str, _StyleProps]) -> bool:
    return bool(style and styles.get(style, _StyleProps()).italic)


def _bg(style: str | None, styles: dict[str, _StyleProps]) -> str | None:
    return styles.get(style or "", _StyleProps()).bg_color


def _read_gen_sheet(
    name: str, tbl: ET.Element, styles: dict[str, _StyleProps]
) -> list[CameoEntry]:
    """Gen N sheet: cols [Ndex, Cameo Pokémon, Card name, Set, #, Notes]."""
    rows = tbl.findall(f"{{{NS_TABLE}}}table-row")
    out: list[CameoEntry] = []
    tracker = _MergeTracker()
    current_artwork_group: str | None = None
    current_artwork_remaining = 0

    for ri, row in enumerate(rows):
        if ri == 0:
            # Header. Skip but track merges (none expected on header).
            tracker.record(_walk_row(row))
            continue
        raw_cells = _walk_row(row)
        filled = tracker.fill(raw_cells)
        # Pad to 6 cols
        while len(filled) < 6:
            filled.append(_Cell(text="", style=None, col_span=1, row_span=1))

        ndex_txt = filled[0].text
        species_txt = filled[1].text
        card_name_txt = filled[2].text
        set_txt = filled[3].text
        num_txt = filled[4].text
        notes_txt = filled[5].text

        # Track artwork group from col 2 merges. A col-2 cell with row_span > 1
        # on the *raw* row (not the filled one) opens a new group.
        raw_card_cell = raw_cells[2] if len(raw_cells) > 2 else None
        if raw_card_cell is not None and raw_card_cell.row_span > 1 and raw_card_cell.text:
            current_artwork_group = f"{name}|{set_txt}|{card_name_txt}|r{ri}"
            current_artwork_remaining = raw_card_cell.row_span
        if current_artwork_remaining > 0:
            artwork_group = current_artwork_group
            current_artwork_remaining -= 1
            if current_artwork_remaining == 0:
                current_artwork_group = None
        else:
            artwork_group = None

        tracker.record(raw_cells)

        # Skip entirely empty rows.
        if not any([species_txt, card_name_txt, set_txt, num_txt]):
            continue
        # Skip rows where we have no usable set/number (true blank).
        if not set_txt and not num_txt:
            continue

        ndex = _parse_int(ndex_txt)
        flags = _flags_for(filled, styles, card_name_txt, artwork_group)
        cameo_subject = species_txt

        out.append(
            CameoEntry(
                cameo_subject=cameo_subject,
                parent_species=None,
                subject_kind="pokemon",
                ndex=ndex,
                region=None,
                card_name=card_name_txt or None,
                set_name=set_txt,
                collector_number=num_txt or "-",
                notes=notes_txt or None,
                flags=flags,
                artwork_group_id=artwork_group,
                bg_color_raw=_bg(filled[2].style, styles),
            )
        )

    return _resolve_different_forms(out)


def _read_trainers_sheet(
    tbl: ET.Element, styles: dict[str, _StyleProps]
) -> list[CameoEntry]:
    """Trainers sheet: cols [Region, Cameo Trainer, Card name, Set, #, Notes].

    Region is merged across that region's whole block (KANTO, JOHTO, ...).
    """
    rows = tbl.findall(f"{{{NS_TABLE}}}table-row")
    out: list[CameoEntry] = []
    tracker = _MergeTracker()
    current_artwork_group: str | None = None
    current_artwork_remaining = 0

    for ri, row in enumerate(rows):
        if ri == 0:
            tracker.record(_walk_row(row))
            continue
        raw_cells = _walk_row(row)
        filled = tracker.fill(raw_cells)
        while len(filled) < 6:
            filled.append(_Cell(text="", style=None, col_span=1, row_span=1))

        region = filled[0].text or None
        trainer = filled[1].text
        card_name_txt = filled[2].text
        set_txt = filled[3].text
        num_txt = filled[4].text
        notes_txt = filled[5].text

        raw_card_cell = raw_cells[2] if len(raw_cells) > 2 else None
        if raw_card_cell is not None and raw_card_cell.row_span > 1 and raw_card_cell.text:
            current_artwork_group = f"Trainers|{set_txt}|{card_name_txt}|r{ri}"
            current_artwork_remaining = raw_card_cell.row_span
        if current_artwork_remaining > 0:
            artwork_group = current_artwork_group
            current_artwork_remaining -= 1
            if current_artwork_remaining == 0:
                current_artwork_group = None
        else:
            artwork_group = None

        tracker.record(raw_cells)

        if not any([trainer, card_name_txt, set_txt, num_txt]):
            continue
        if not set_txt and not num_txt:
            continue

        flags = _flags_for(filled, styles, card_name_txt, artwork_group)
        out.append(
            CameoEntry(
                cameo_subject=trainer,
                parent_species=None,
                subject_kind="trainer",
                ndex=None,
                region=region,
                card_name=card_name_txt or None,
                set_name=set_txt,
                collector_number=num_txt or "-",
                notes=notes_txt or None,
                flags=flags,
                artwork_group_id=artwork_group,
                bg_color_raw=_bg(filled[2].style, styles),
            )
        )
    return out


def _flags_for(
    filled: list[_Cell],
    styles: dict[str, _StyleProps],
    card_name_txt: str,
    artwork_group: str | None,
) -> frozenset[Flag]:
    flags: set[Flag] = set()
    if _is_italic(filled[2].style, styles):
        flags.add(Flag.ITALIC)
    # Non-English bg: source uses same bg across the row, so a single sample
    # suffices but we check a few cells for resilience.
    for i in (2, 3, 4):
        if _bg(filled[i].style, styles) == NON_ENGLISH_BG:
            flags.add(Flag.NON_ENGLISH)
            break
    notes = (filled[5].text or "").lower()
    if "jumbo" in notes:
        flags.add(Flag.JUMBO)
    if not card_name_txt:
        flags.add(Flag.BLANK_CARD_NAME)
    if artwork_group:
        flags.add(Flag.SHARED_ARTWORK)
    return frozenset(flags)


def _resolve_different_forms(entries: list[CameoEntry]) -> list[CameoEntry]:
    """Stamp DIFFERENT_FORM + parent_species on entries whose cameo_subject
    differs from the first species seen for that Ndex (e.g. Mega Venusaur
    under Venusaur's Ndex=3 block).
    """
    first_subject_for_ndex: dict[int, str] = {}
    out: list[CameoEntry] = []
    for e in entries:
        if e.ndex is None or not e.cameo_subject:
            out.append(e)
            continue
        parent = first_subject_for_ndex.setdefault(e.ndex, e.cameo_subject)
        if e.cameo_subject == parent:
            out.append(e)
        else:
            out.append(
                CameoEntry(
                    cameo_subject=e.cameo_subject,
                    parent_species=parent,
                    subject_kind=e.subject_kind,
                    ndex=e.ndex,
                    region=e.region,
                    card_name=e.card_name,
                    set_name=e.set_name,
                    collector_number=e.collector_number,
                    notes=e.notes,
                    flags=frozenset(e.flags | {Flag.DIFFERENT_FORM}),
                    artwork_group_id=e.artwork_group_id,
                    bg_color_raw=e.bg_color_raw,
                )
            )
    return out


def _parse_int(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None
