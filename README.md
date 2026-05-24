# cameo-convert

Invert RotomAmiti's Cameo Pokémon Card Database from a Pokémon-indexed lookup
("which cards feature Pikachu as a cameo?") into a card-indexed lookup
("which Pokémon cameo is on this card?").

> **Credit & source of truth.** The underlying database is
> [RotomAmiti's Cameo Pokémon Card Database](https://docs.google.com/spreadsheets/d/18nIkOgqQrHZTz0TrH_gL1e1nL1RcHiCmPF5finAjToY/edit?gid=1923267969#gid=1923267969).
> This package is a downstream transformer; all collector knowledge belongs to
> RotomAmiti. The mirrored snapshot lives at [`data/cameo-database.ods`](data/cameo-database.ods).

See [`docs/design.pdf`](docs/design.pdf) for the full design doc (approved spec).

## Quickstart (Makefile)

Easiest path — the Makefile bootstraps a virtualenv on first use, then exposes
every common task:

```sh
make            # list targets
make run        # generate all 28 files in dist/
make quick      # fast: clean variant, json+csv+md+sqlite, no bundles
make verify     # clean run + assert 28 files + spot-check §6.4 example
make test       # pytest -q
make clean      # remove dist/ + caches
```

The first `make` call creates `.venv/`, installs `cameo-convert -e ".[dev]"`,
and is skipped on subsequent calls (unless `pyproject.toml` changes). Override
defaults inline:

```sh
make run RELEASE_TAG=v0.1.0 OUTPUT_DIR=/tmp/out
make run INPUT=/path/to/some-other.ods
```

Full target list:

| Target | Purpose |
|---|---|
| `install` | Create `.venv` and install package + dev deps |
| `test` | Run pytest |
| `run` | Generate all 28 files in `$(OUTPUT_DIR)` |
| `quick` | Fast iteration subset (no bundles) |
| `smoke` | Mirror the CI smoke test (writes to `/tmp/dist`) |
| `verify` | Clean + run + assert file count + spot-check §6.4 example |
| `goldens` | Regenerate `tests/goldens/*.json` |
| `fixture` | Rebuild `tests/fixtures/tiny_sample.ods` |
| `fetch-sets` | Refresh `data/set_release_dates.json` from pokemontcg.io |
| `shell` | Python REPL with the package importable |
| `clean` | Remove `$(OUTPUT_DIR)` + Python caches |
| `distclean` | `clean` + remove `.venv/` |

## Install (manual, without Make)

```sh
pip install -e .
```

Optional: `pip install -e ".[dev]"` for the test stack.

## Use (manual, without Make)

```sh
python -m cameo_convert \
    --input data/cameo-database.ods \
    --output-dir dist/ \
    --release-tag v1.0.0 \
    --formats json,jsonl,yaml,toml,xml,csv,tsv,md,html,txt,sqlite,xlsx,ods \
    --variants clean,full \
    --bundle zip,tar.gz
```

All flags have defaults — `python -m cameo_convert` with no arguments writes
every variant in every format to `dist/`.

## Output

Each run emits **28 files** per release:

| Count | Kind |
|---:|---|
| 13 × 2 = 26 | format × variant individual files |
| 2 | `all-formats.zip` + `all-formats.tar.gz` bundles |

### Formats

| Format | Best for |
|---|---|
| JSON / JSONL | Programmatic consumption |
| YAML | Human-editable configs |
| TOML | Static config consumers |
| XML | Legacy tooling |
| CSV / TSV | Spreadsheet import (long format) |
| Markdown | Reading on GitHub |
| HTML | Self-contained browser page with client-side filter |
| Plain text | Lowest common denominator |
| SQLite | Local SQL querying (tables: `cards`, `cameos`, `metadata`) |
| XLSX / ODS | Round-trip to spreadsheet apps |

### Variants

- **Clean** — English-only collector view. Excludes italic edge cases
  (toy / silhouette / costume / partial frame), non-English-only cards, and
  rows with blank card names.
- **Full** — every entry from the source with all flags preserved as metadata.

## Website

A GitHub Pages site at **https://nottcorp.github.io/nottcameoflip/** displays
the latest release: tag, date, notes, asset downloads (format × variant
picker), a release-history archive, and the database itself in a filterable
table — no download required.

The site rebuilds on `release: [published]` via
`.github/workflows/pages.yml` (also runnable via manual dispatch).
Source lives in `web/`; the
generator (`scripts/build_site.py`) fetches the GitHub Releases API and
the full-variant JSON asset from the latest release, then writes a
self-contained `_site/`.

Build it locally:

```sh
make site         # writes _site/
make site-serve   # builds then serves on http://localhost:8000
```

`make site` reads `GITHUB_TOKEN` (or falls back to `gh auth token`) and
defaults to the `NottCorp/nottcameoflip` repo; override with
`GITHUB_REPOSITORY=owner/repo make site`.

One-time setup: in repo Settings → Pages, set **Source** to "GitHub
Actions".

## Releases

`.github/workflows/release.yml` fires on `push: tags: 'v*'`. It creates
(or updates) a **draft** GitHub Release for the pushed tag and attaches
all 28 files as assets. The maintainer then visits Releases, writes the
notes, and clicks Publish. Filenames carry the release tag, e.g.
`cameo-convert-v1.2.3-cards-clean.json`.

---

## Runbooks

### Update the database to a newer RotomAmiti snapshot

1. Download the latest `.ods` from
   [RotomAmiti's Google Sheets](https://docs.google.com/spreadsheets/d/18nIkOgqQrHZTz0TrH_gL1e1nL1RcHiCmPF5finAjToY/edit?gid=1923267969#gid=1923267969)
   (File → Download → ODF Spreadsheet).
2. Replace `data/cameo-database.ods` with the downloaded file. Keep that exact
   filename — the apostrophe and `é` in RotomAmiti's original break CI shell
   quoting (decision D8).
3. Run a local conversion to sanity-check the diff:
   ```sh
   make verify OUTPUT_DIR=/tmp/dist
   ```
   Confirm totals roughly match expectations and no new unknown sheets/colors
   are warned. (Unknown sheets emit a `UserWarning`; unknown background
   colors pass through to `bg_color_raw` in the IR.)
4. Commit and open a PR.
5. After merge, cut a GitHub Release (see "Cut a release" below).

### Cut a release

1. Bump `version` in `pyproject.toml` and the matching `__version__` in
   `src/cameo_convert/__init__.py`.
2. `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The `release.yml` workflow fires on tag push. It builds all 28 files,
   creates a **draft** GitHub Release named `vX.Y.Z`, auto-generates the
   release notes (commits + PRs since the previous release tag), and
   attaches the 28 files. Watch the Actions tab for the green check.
4. On GitHub, open **Releases**, find the new draft, review/edit the
   auto-generated notes, choose "Set as the latest release" or "Set as a
   pre-release", then click **Publish release**.

You never have to create the draft yourself — the workflow does. Don't
manually publish before the workflow finishes, or asset uploads fail
(published releases are immutable).

### Re-run a release that failed

```sh
gh workflow run release.yml -f release_tag=vX.Y.Z
```

This re-runs against the existing draft for that tag, replacing the
asset list. If the draft was already published (and is now immutable),
delete the release on GitHub first; the next workflow run will create a
fresh draft for the same tag.

### Handle a new Pokémon generation (Gen 10, Gen 11, ...)

No code change required. The reader detects sheets matching `^Gen \d+$`
automatically — drop a new generation sheet into the source `.ods`, run the
conversion, and verify the new entries appear:

```sh
make quick OUTPUT_DIR=/tmp/dist
jq '.cards | to_entries | map(select(.value.cameos[].ndex > 1025)) | length' \
   /tmp/dist/cameo-convert-cards-full.json
```

If RotomAmiti changes the schema (e.g. introduces a new edge-case flag), see
"Add a new flag" below.

### Refresh set release dates (and add manual aliases for unmatched sets)

Cards in human-facing outputs (MD/HTML/TXT) sort chronologically by set
release date. Dates live in `data/set_release_dates.json`, sourced from
[pokemontcg.io](https://pokemontcg.io/).

```sh
make fetch-sets
```

This GETs `/v2/sets`, merges with the existing JSON (preserving any manual
`source_aliases` you added), and writes back. Review the diff and commit.

The API covers ~170 sets — mostly English releases. Many source sets won't
match automatically (Japanese promos, championship decks, special
collections). To add a manual alias, edit `data/set_release_dates.json`:

```json
{
  "sets": {
    "xy-black-star-promos": {
      "release_date": "2014-02-05",
      "display_name": "XY Black Star Promos",
      "series": "XY",
      "ptcgo_code": "XYP",
      "source_aliases": ["XY Black Star Promos", "XY Promos", "XY-P Promos"]
    }
  }
}
```

`source_aliases` is a list of EXACT source set names that should resolve to
this entry. The resolver tries (1) the slugified source name as a key, then
(2) the source name in any `source_aliases` list.

To add a brand-new entry for a set not in the API, add a top-level key under
`sets` with at least `release_date` and `source_aliases`. The next `make
fetch-sets` will preserve it.

Cards whose set name doesn't resolve get `release_date: null` and sort to the
end of their Pokémon bucket (alphabetically). Coverage today: ~57% of source
sets (134/238) — the remaining 100+ are Japanese promo sets and similar.

### Add a new output format

1. Create `src/cameo_convert/writers/<name>_writer.py` with a class exposing
   `name: str`, `extension: str`, and `write(dataset: InvertedDataset, path: Path) -> None`.
2. Register it in `src/cameo_convert/writers/__init__.py`'s `REGISTRY`.
3. Add a row in this README's Formats table.
4. The CLI's `--formats` default automatically expands to include it via
   `ALL_FORMATS`.
5. Add a test in `tests/test_writers.py` (the parametrized
   `test_writer_produces_file` will pick it up automatically; add format-
   specific assertions if the shape warrants them).
6. Update the design doc's format count if you're changing the canonical
   release-asset count of 28.

### Add a new flag (e.g. RotomAmiti adopts a new visual convention)

1. Add the variant to `Flag` in `src/cameo_convert/model.py`.
2. Update `_flags_for` (or the relevant reader helper) in
   `src/cameo_convert/reader.py` to detect the new convention.
3. Decide whether the Clean variant should exclude it; if so, add to
   `_CLEAN_EXCLUDED_FLAGS` in `src/cameo_convert/filter.py`.
4. Add a row to `tests/fixtures/build_tiny_sample.py` exercising the new
   convention; rebuild the fixture with
   `python tests/fixtures/build_tiny_sample.py`.
5. Add a `test_reader.py` assertion for the new flag.

### Debug a parse failure

```sh
python -c "from cameo_convert.reader import read; e, m = read('data/cameo-database.ods'); print(len(e), m)"
```

For deeper inspection, the reader uses `xml.etree.ElementTree` so you can
crack open `content.xml` directly:

```sh
unzip -p data/cameo-database.ods content.xml | head -200
```

The reader emits a `UserWarning` for any sheet whose name is not `Main`,
`Trainers`, or matches `^Gen \d+$`. If the warning fires on a sheet you
expect handled, add it to `reader.read()`.

### Run the test suite

```sh
make test
```

## License

MIT (see [`LICENSE`](LICENSE)). The bundled source `.ods` is RotomAmiti's
work; credit belongs to them.
