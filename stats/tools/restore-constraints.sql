-- move data containing tables
ALTER TABLE events
    RENAME TO tmp_events;

ALTER TABLE plot_states
    RENAME TO tmp_plot_states;

-- recreate the tables we want
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


-- create primary keys
ALTER TABLE ONLY events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY plot_states
    ADD CONSTRAINT plots_pkey PRIMARY KEY (id);

-- copy data from tmp tables, deduping on pk
INSERT INTO events
SELECT *
FROM tmp_events
ON CONFLICT DO NOTHING;

INSERT INTO tmp_plot_states
SELECT *
FROM plot_states
ON CONFLICT DO NOTHING;

-- create non-primary indexes
CREATE INDEX ix_events_event_type ON events USING btree (event_type);
CREATE INDEX ix_events_sweeper_id ON events USING btree (sweeper_id);
CREATE INDEX ix_events_timestamp ON events USING btree ("timestamp");

CREATE INDEX ix_plot_states_loc_last_seen_desc
    ON plot_states USING btree (world_id ASC, territory_type_id ASC, ward_number ASC, plot_number ASC, last_seen DESC);
CREATE INDEX ix_plot_states_last_seen_desc
    ON plot_states USING btree (last_seen DESC);
ALTER TABLE plot_states
    ADD CONSTRAINT plot_states_territory_type_id_plot_number_fkey
        FOREIGN KEY (territory_type_id, plot_number) REFERENCES plotinfo;
ALTER TABLE plot_states
    ADD CONSTRAINT plot_states_world_id_fkey
        FOREIGN KEY (world_id) REFERENCES worlds;
ALTER TABLE plot_states
    ADD CONSTRAINT plot_states_territory_type_id_fkey
        FOREIGN KEY (territory_type_id) REFERENCES districts;

-- create additional statgen indexes
-- CREATE INDEX ix_plots_owner_name ON public.plots USING btree (owner_name);
-- CREATE INDEX ix_plots_world_id_owner_name_timestamp ON public.plots USING btree (world_id, owner_name, "timestamp");

-- delete tmp tables
DROP TABLE tmp_events;
DROP TABLE tmp_plot_states;
