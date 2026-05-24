"""Build tests/fixtures/tiny_sample.ods, a minimal fixture covering every edge
case the reader has to handle. Hand-authored as a zip of XML so we don't need
LibreOffice in the test environment.

Edge cases exercised:
- Pokémon block with multiple cards (col 0/1 merged).
- Shared-artwork reprint group (col 2 merged across 2 rows).
- Italic card name + Notes = "silhouette".
- Light-blue background (non-English).
- Different-form cameo: "Mega Bulbasaur" under Bulbasaur's Ndex=1 block.
- Blank card name (None card_name + BLANK_CARD_NAME flag).
- Non-numeric collector number (-, GG09).
- Jumbo via Notes.
- Trainers sheet with region merge + per-character merge.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from textwrap import dedent

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

META = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:dc="http://purl.org/dc/elements/1.1/" office:version="1.2">
 <office:meta>
  <dc:date>2026-05-21T00:00:00</dc:date>
 </office:meta>
</office:document-meta>
"""

CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.2">
 <office:automatic-styles>
  <style:style style:name="ce-italic" style:family="table-cell">
   <style:text-properties fo:font-style="italic"/>
  </style:style>
  <style:style style:name="ce-blue" style:family="table-cell">
   <style:table-cell-properties fo:background-color="#cfe2f3"/>
  </style:style>
  <style:style style:name="ce-blue-parent" style:family="table-cell">
   <style:table-cell-properties fo:background-color="#cfe2f3"/>
  </style:style>
  <style:style style:name="ce-blue-child" style:family="table-cell" style:parent-style-name="ce-blue-parent"/>
 </office:automatic-styles>
 <office:body>
  <office:spreadsheet>
   <table:table table:name="Main">
    <table:table-row>
     <table:table-cell><text:p>Welcome to the test fixture</text:p></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:table-cell><text:p>The sheet is currently up-to-date with all English releases up to and including Chaos Rising, and all Japanese releases up to and including Abyss Eye.</text:p></table:table-cell>
    </table:table-row>
   </table:table>
   <table:table table:name="Gen 1">
    <table:table-row>
     <table:table-cell><text:p>Ndex</text:p></table:table-cell>
     <table:table-cell><text:p>Cameo Pokémon</text:p></table:table-cell>
     <table:table-cell><text:p>Card name</text:p></table:table-cell>
     <table:table-cell><text:p>Set</text:p></table:table-cell>
     <table:table-cell><text:p>#</text:p></table:table-cell>
     <table:table-cell><text:p>Notes</text:p></table:table-cell>
    </table:table-row>
    <!-- Bulbasaur block: Ndex=1 spans 6 rows; Cameo=Bulbasaur spans 4 rows, then Mega Bulbasaur spans 2 rows -->
    <table:table-row>
     <table:table-cell table:number-rows-spanned="6"><text:p>1</text:p></table:table-cell>
     <table:table-cell table:number-rows-spanned="4"><text:p>Bulbasaur</text:p></table:table-cell>
     <table:table-cell><text:p>Pokémon Valley</text:p></table:table-cell>
     <table:table-cell><text:p>Miscellaneous Promos</text:p></table:table-cell>
     <table:table-cell><text:p>-</text:p></table:table-cell>
     <table:table-cell><text:p>Jumbo</text:p></table:table-cell>
    </table:table-row>
    <!-- Reprint group: same Card name spans 2 rows -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell table:number-rows-spanned="2"><text:p>Town Volunteers</text:p></table:table-cell>
     <table:table-cell><text:p>Aquapolis</text:p></table:table-cell>
     <table:table-cell><text:p>136</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell><text:p>Aquapolis Reprint</text:p></table:table-cell>
     <table:table-cell><text:p>200</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <!-- Italic edge case row -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell table:style-name="ce-italic"><text:p>Team Rocket's Meowth</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-italic"><text:p>Wizards Promos</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-italic"><text:p>18</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-italic"><text:p>silhouette</text:p></table:table-cell>
    </table:table-row>
    <!-- Different-form: Mega Bulbasaur under Ndex=1 -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:table-cell table:number-rows-spanned="2"><text:p>Mega Bulbasaur</text:p></table:table-cell>
     <table:table-cell><text:p>Some Card</text:p></table:table-cell>
     <table:table-cell><text:p>Made Up Set</text:p></table:table-cell>
     <table:table-cell><text:p>1</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <!-- Non-English bg row + inherited style (uses parent style chain) -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell table:style-name="ce-blue-child"><text:p>JP-Only Card</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-blue"><text:p>Japanese Set</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-blue"><text:p>JP1</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <!-- New Pokémon block: Ivysaur Ndex=2; non-numeric collector # (GG09).
         Ivysaur block now spans 3 rows: Galar card, reprint pair (English +
         non-English sibling that should survive Clean via the sibling rule). -->
    <table:table-row>
     <table:table-cell><text:p>2</text:p></table:table-cell>
     <table:table-cell table:number-rows-spanned="3"><text:p>Ivysaur</text:p></table:table-cell>
     <table:table-cell><text:p>Some Galar Card</text:p></table:table-cell>
     <table:table-cell><text:p>Crown Zenith</text:p></table:table-cell>
     <table:table-cell><text:p>GG09</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <!-- Shared-artwork reprint: English original + non-English sibling.
         The non-English sibling should survive Clean per the reprint-sibling rule. -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell table:number-rows-spanned="2"><text:p>Reprint Test</text:p></table:table-cell>
     <table:table-cell><text:p>English Set</text:p></table:table-cell>
     <table:table-cell><text:p>5</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell table:style-name="ce-blue"><text:p>Japanese Set</text:p></table:table-cell>
     <table:table-cell table:style-name="ce-blue"><text:p>JP5</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
   </table:table>
   <table:table table:name="Gen 10">
    <table:table-row>
     <table:table-cell><text:p>Ndex</text:p></table:table-cell>
     <table:table-cell><text:p>Cameo Pokémon</text:p></table:table-cell>
     <table:table-cell><text:p>Card name</text:p></table:table-cell>
     <table:table-cell><text:p>Set</text:p></table:table-cell>
     <table:table-cell><text:p>#</text:p></table:table-cell>
     <table:table-cell><text:p>Notes</text:p></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:table-cell table:number-rows-spanned="2"><text:p>1100</text:p></table:table-cell>
     <table:table-cell table:number-rows-spanned="2"><text:p>Futuremon</text:p></table:table-cell>
     <table:table-cell><text:p>Future Card</text:p></table:table-cell>
     <table:table-cell><text:p>Future Set</text:p></table:table-cell>
     <table:table-cell><text:p>1</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <!-- Multi-name card: "Bulbasaur & Ivysaur-GX" should normalize to
         primary_pokemons = [Bulbasaur, Ivysaur] (both known species). -->
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell><text:p>Bulbasaur &amp; Ivysaur-GX</text:p></table:table-cell>
     <table:table-cell><text:p>Cosmic Eclipse</text:p></table:table-cell>
     <table:table-cell><text:p>999</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
   </table:table>
   <table:table table:name="Trainers">
    <table:table-row>
     <table:table-cell><text:p/></table:table-cell>
     <table:table-cell><text:p>Cameo Trainer</text:p></table:table-cell>
     <table:table-cell><text:p>Card name</text:p></table:table-cell>
     <table:table-cell><text:p>Set</text:p></table:table-cell>
     <table:table-cell><text:p>#</text:p></table:table-cell>
     <table:table-cell><text:p>Notes</text:p></table:table-cell>
    </table:table-row>
    <!-- KANTO region spans 3 rows; Red spans 2 rows; Brock spans 1 row -->
    <table:table-row>
     <table:table-cell table:number-rows-spanned="3"><text:p>KANTO</text:p></table:table-cell>
     <table:table-cell table:number-rows-spanned="2"><text:p>Red</text:p></table:table-cell>
     <table:table-cell><text:p>Red's Pikachu</text:p></table:table-cell>
     <table:table-cell><text:p>SM-P Promos</text:p></table:table-cell>
     <table:table-cell><text:p>270</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:covered-table-cell/>
     <table:covered-table-cell/>
     <table:table-cell><text:p/></table:table-cell>
     <table:table-cell><text:p>Call of Legends</text:p></table:table-cell>
     <table:table-cell><text:p>77</text:p></table:table-cell>
     <table:table-cell><text:p>blank card</text:p></table:table-cell>
    </table:table-row>
    <table:table-row>
     <table:covered-table-cell/>
     <table:table-cell><text:p>Brock</text:p></table:table-cell>
     <table:table-cell><text:p>Blaine's Quiz #3</text:p></table:table-cell>
     <table:table-cell><text:p>Gym Challenge</text:p></table:table-cell>
     <table:table-cell><text:p>112</text:p></table:table-cell>
     <table:table-cell><text:p/></table:table-cell>
    </table:table-row>
   </table:table>
  </office:spreadsheet>
 </office:body>
</office:document-content>
"""


def build(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z:
        # mimetype must be first and uncompressed per ODS spec.
        z.writestr("mimetype", MIMETYPE)
    with zipfile.ZipFile(out_path, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/manifest.xml", dedent(MANIFEST).strip())
        z.writestr("meta.xml", dedent(META).strip())
        z.writestr("content.xml", dedent(CONTENT).strip())


if __name__ == "__main__":
    build(Path(__file__).parent / "tiny_sample.ods")
    print(f"wrote {Path(__file__).parent / 'tiny_sample.ods'}")
