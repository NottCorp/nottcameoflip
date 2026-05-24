"""SQLite writer per §6.3 — two tables: `cards`, `cameos`."""

import sqlite3
from pathlib import Path

from cameo_convert.model import InvertedDataset
from cameo_convert.writers.base import metadata_dict


_DDL = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE cards (
    key TEXT PRIMARY KEY,
    card_name TEXT,
    set_name TEXT NOT NULL,
    collector_number TEXT NOT NULL,
    artwork_group_id TEXT,
    primary_pokemons TEXT  -- comma-joined; see card_primary_pokemons for normalized list
);
CREATE TABLE card_primary_pokemons (
    card_key TEXT NOT NULL REFERENCES cards(key),
    pokemon TEXT NOT NULL,
    ord INTEGER NOT NULL,
    PRIMARY KEY (card_key, ord)
);
CREATE TABLE cameos (
    card_key TEXT NOT NULL REFERENCES cards(key),
    subject TEXT NOT NULL,
    parent_species TEXT,
    kind TEXT NOT NULL,
    ndex INTEGER,
    region TEXT,
    notes TEXT,
    flags TEXT
);
CREATE INDEX idx_cameos_subject ON cameos(subject);
CREATE INDEX idx_cameos_ndex ON cameos(ndex);
CREATE INDEX idx_cards_set ON cards(set_name);
CREATE INDEX idx_cards_artwork_group ON cards(artwork_group_id);
CREATE INDEX idx_cpp_pokemon ON card_primary_pokemons(pokemon);
"""


class SqliteWriter:
    name = "sqlite"
    extension = "sqlite"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        if path.exists():
            path.unlink()
        con = sqlite3.connect(path)
        try:
            con.executescript(_DDL)
            con.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                [(k, str(v) if v is not None else None) for k, v in metadata_dict(dataset).items()],
            )
            for key in sorted(dataset.cards):
                card = dataset.cards[key]
                con.execute(
                    "INSERT INTO cards(key, card_name, set_name, collector_number, "
                    "artwork_group_id, primary_pokemons) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        key,
                        card.card_name,
                        card.set_name,
                        card.collector_number,
                        card.artwork_group_id,
                        ",".join(card.primary_pokemons) or None,
                    ),
                )
                con.executemany(
                    "INSERT INTO card_primary_pokemons(card_key, pokemon, ord) "
                    "VALUES (?, ?, ?)",
                    [(key, p, i) for i, p in enumerate(card.primary_pokemons)],
                )
                con.executemany(
                    "INSERT INTO cameos(card_key, subject, parent_species, kind, ndex, region, notes, flags) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            key,
                            c.subject,
                            c.parent_species,
                            c.kind,
                            c.ndex,
                            c.region,
                            c.notes,
                            ",".join(sorted(f.value for f in c.flags)) or None,
                        )
                        for c in card.cameos
                    ],
                )
            con.commit()
        finally:
            con.close()
