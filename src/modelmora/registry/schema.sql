-- The durable registry (data-model.md "Durable: the registry (SQLite)").
--
-- Three tables only, matching data-model.md exactly: `model` never carries an
-- endpoint or anything that could point off this machine (FR-026) -- every record
-- names local weights, verified by digest (FR-022).

CREATE TABLE IF NOT EXISTS model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('text', 'image')),
    reads_images INTEGER NOT NULL DEFAULT 0 CHECK (reads_images IN (0, 1)),
    license_name TEXT,
    license_source TEXT,
    source TEXT NOT NULL,
    weights_digest TEXT NOT NULL,
    added_by TEXT NOT NULL,
    added_at TEXT NOT NULL,
    license_confirmed_by TEXT,
    license_confirmed_at TEXT,
    filter_disclosure TEXT NOT NULL DEFAULT 'none'
        CHECK (filter_disclosure IN ('none', 'disclosed', 'undisclosable')),
    UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS service_period (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL REFERENCES model (id),
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS default_model (
    slot TEXT PRIMARY KEY CHECK (slot IN ('text', 'text_with_images', 'image')),
    model_id INTEGER NOT NULL REFERENCES model (id)
);
