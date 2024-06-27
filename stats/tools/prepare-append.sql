-- move events and plots tables
ALTER TABLE events
    RENAME TO tmp_events;

ALTER TABLE plot_states
    RENAME TO tmp_plot_states;

-- create temp target tables for append data
CREATE TABLE events
(
    id          INTEGER NOT NULL,
    sweeper_id  BIGINT,
    "timestamp" TIMESTAMP WITHOUT TIME ZONE,
    event_type  eventtype,
    data        TEXT
);

CREATE TABLE plot_states
(
    id                INTEGER NOT NULL,
    world_id          INTEGER,
    territory_type_id INTEGER,
    ward_number       INTEGER,
    plot_number       INTEGER,
    last_seen         TIMESTAMP WITHOUT TIME ZONE,
    first_seen        TIMESTAMP WITHOUT TIME ZONE,
    is_owned          BOOLEAN,
    last_seen_price   INTEGER,
    owner_name        CHARACTER VARYING,
    purchase_system   INTEGER,
    lotto_entries     INTEGER,
    lotto_phase       INTEGER,
    lotto_phase_until INTEGER
);
