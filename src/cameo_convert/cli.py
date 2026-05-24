"""Command-line entry point per design doc §6.6."""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

from cameo_convert import __version__
from cameo_convert import sets as set_module
from cameo_convert.filter import clean, full
from cameo_convert.log import configure as configure_logging
from cameo_convert.log import get_logger
from cameo_convert.normalize import slug
from cameo_convert.reader import read
from cameo_convert.transform import invert
from cameo_convert.writers import ALL_FORMATS, REGISTRY

log = get_logger(__name__)

ALL_VARIANTS = ("clean", "full")
ALL_BUNDLES = ("zip", "tar.gz")


def _comma_list(arg: str) -> list[str]:
    return [s.strip() for s in arg.split(",") if s.strip()]


def _filename(release_tag: str, variant: str, extension: str) -> str:
    base = "cameo-convert"
    if release_tag:
        return f"{base}-{slug(release_tag) or release_tag}-cards-{variant}.{extension}"
    return f"{base}-cards-{variant}.{extension}"


def _bundle_name(release_tag: str, kind: str) -> str:
    base = "cameo-convert"
    if release_tag:
        return f"{base}-{slug(release_tag) or release_tag}-all-formats.{kind}"
    return f"{base}-all-formats.{kind}"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cameo-convert",
        description="Invert the Cameo Pokémon Card Database (Pokémon-indexed → card-indexed).",
    )
    p.add_argument(
        "--input",
        default="data/cameo-database.ods",
        type=Path,
        help="Path to the source .ods (default: %(default)s)",
    )
    p.add_argument(
        "--output-dir",
        default=Path("dist"),
        type=Path,
        help="Where to write output files (default: %(default)s)",
    )
    p.add_argument(
        "--release-tag",
        default="",
        help="Release tag included in filenames (default: empty → no tag segment)",
    )
    p.add_argument(
        "--formats",
        default=",".join(ALL_FORMATS),
        type=_comma_list,
        help="Comma-separated formats (default: all 13)",
    )
    p.add_argument(
        "--variants",
        default=",".join(ALL_VARIANTS),
        type=_comma_list,
        help="Comma-separated variants (default: clean,full)",
    )
    p.add_argument(
        "--bundle",
        default=",".join(ALL_BUNDLES),
        type=_comma_list,
        help="Bundle archive kinds: any of zip,tar.gz (default: both)",
    )
    p.add_argument(
        "--log-level",
        default=None,
        help="Project log level (DEBUG/INFO/WARNING/CRITICAL). Default: DEBUG. "
        "Env override: CAMEO_CONVERT_LOG_LEVEL.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)

    unknown_formats = set(args.formats) - set(ALL_FORMATS)
    if unknown_formats:
        log.critical("unknown formats: %s (known: %s)", sorted(unknown_formats), sorted(ALL_FORMATS))
        return 2
    unknown_variants = set(args.variants) - set(ALL_VARIANTS)
    if unknown_variants:
        log.critical("unknown variants: %s", sorted(unknown_variants))
        return 2
    unknown_bundles = set(args.bundle) - set(ALL_BUNDLES) - {""}
    if unknown_bundles:
        log.critical("unknown bundle kinds: %s", sorted(unknown_bundles))
        return 2

    if not args.input.exists():
        log.critical("input not found: %s", args.input)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    log.info("reading %s", args.input)
    entries, meta = read(args.input)
    log.info(
        "parsed %d entries (source last_updated=%s, up-to-date-with=%s)",
        len(entries), meta.last_updated, meta.up_to_date_with_set,
    )

    set_dates = set_module.load(set_module.DEFAULT_JSON_PATH)
    if len(set_dates) == 0:
        log.warning(
            "%s missing or empty — release dates will be unresolved (run `make fetch-sets`)",
            set_module.DEFAULT_JSON_PATH,
        )
    else:
        log.info("loaded %d known set release dates", len(set_dates))

    # The real source .ods doesn't carry a dc:date in meta.xml, so fall back
    # to the "up-to-date with all English releases up to and including X" set
    # named in the Main sheet — that's how RotomAmiti versions snapshots.
    source_last_updated = meta.last_updated or meta.up_to_date_with_set

    base = invert(
        entries,
        source_file=args.input.name,
        source_last_updated=source_last_updated,
        release_tag=args.release_tag,
        generator_version=__version__,
        set_date_resolver=set_dates,
    )

    datasets = {}
    if "clean" in args.variants:
        datasets["clean"] = clean(base)
    if "full" in args.variants:
        datasets["full"] = full(base)

    produced: list[Path] = []
    for variant in args.variants:
        ds = datasets[variant]
        log.debug("variant %s: %d cards / %d cameo entries", variant, ds.total_cards, ds.total_cameo_entries)
        for fmt in args.formats:
            writer = REGISTRY[fmt]()
            path = args.output_dir / _filename(args.release_tag, variant, writer.extension)
            writer.write(ds, path)
            produced.append(path)
            log.info("wrote %s (%s bytes)", path.name, f"{path.stat().st_size:,}")

    for kind in args.bundle:
        if not kind:
            continue
        bundle_path = args.output_dir / _bundle_name(args.release_tag, kind)
        if bundle_path.exists():
            bundle_path.unlink()
        if kind == "zip":
            with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in produced:
                    z.write(f, arcname=f.name)
        elif kind == "tar.gz":
            with tarfile.open(bundle_path, "w:gz") as t:
                for f in produced:
                    t.add(f, arcname=f.name)
        log.info("bundled %s (%s bytes)", bundle_path.name, f"{bundle_path.stat().st_size:,}")

    total = len(produced) + sum(1 for k in args.bundle if k)
    log.info("done — %d files written to %s/", total, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
