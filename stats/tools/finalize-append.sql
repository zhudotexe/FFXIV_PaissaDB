-- remove indexes for better insert performance
DROP INDEX IF EXISTS ix_plot_states_last_seen_desc;
DROP INDEX IF EXISTS ix_plot_states_loc_last_seen_desc;
ALTER TABLE tmp_plot_states
    DROP CONSTRAINT IF EXISTS plot_states_territory_type_id_plot_number_fkey;
ALTER TABLE tmp_plot_states
    DROP CONSTRAINT IF EXISTS plot_states_world_id_fkey;
ALTER TABLE tmp_plot_states
    DROP CONSTRAINT IF EXISTS plot_states_territory_type_id_fkey;
DROP INDEX IF EXISTS ix_events_event_type;
DROP INDEX IF EXISTS ix_events_sweeper_id;
DROP INDEX IF EXISTS ix_events_timestamp;

-- copy append data into real tables
INSERT INTO tmp_events
SELECT *
FROM events
ON CONFLICT DO NOTHING;

INSERT INTO tmp_plot_states
SELECT *
FROM plot_states
ON CONFLICT DO NOTHING;

-- delete temp tables
DROP TABLE events;
DROP TABLE plot_states;

-- rename the temp tables back to the real tables
ALTER TABLE tmp_events
    RENAME TO events;

ALTER TABLE tmp_plot_states
    RENAME TO plot_states;

-- recreate the indexes
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
