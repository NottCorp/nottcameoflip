# cameo-convert

Invert RotomAmiti's Cameo Pokémon Card Database from a Pokémon-indexed lookup
("which cards feature Pikachu as a cameo?") into a card-indexed lookup
("which Pokémon cameo on this card?").

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

## Releases

`.github/workflows/release.yml` runs on every published GitHub Release and
uploads all 28 files as release assets. Filenames carry the release tag, e.g.
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
2. `git tag vX.Y.Z && git push --tags`.
3. On GitHub, **Releases → Draft a new release**, pick the tag, write release
   notes, click **Publish release** (not "Save as pre-release" — the workflow
   only fires on the `released` event, which excludes pre-releases by design;
   see §7.1 of the design doc).
4. The `release.yml` workflow generates the 28 files and uploads them as
   assets. Confirm the assets list on the release page.

### Re-run a release that failed

```sh
gh workflow run release.yml -f release_tag=vX.Y.Z
```

This uses the `workflow_dispatch` input added per §7.2 of the design doc; it
re-attaches assets to the existing tag without creating a new release.

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
