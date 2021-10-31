-- remove indexes for better insert performance
DROP INDEX IF EXISTS ix_plots_event_id_desc;
DROP INDEX IF EXISTS ix_plots_sweep_id_desc;
DROP INDEX IF EXISTS ix_plots_timestamp_desc;
DROP INDEX IF EXISTS ix_plots_ward_number_plot_number_timestamp_desc;
DROP INDEX IF EXISTS ix_plots_world_id_territory_type_id_ward_number_plot_number;
DROP INDEX IF EXISTS ix_plots_owner_name;
DROP INDEX IF EXISTS ix_plots_world_id_owner_name_timestamp;
ALTER TABLE tmp_plots
    DROP CONSTRAINT IF EXISTS plots_event_id_fkey;
DROP INDEX IF EXISTS ix_events_event_type;
DROP INDEX IF EXISTS ix_events_sweeper_id;
DROP INDEX IF EXISTS ix_events_timestamp;

-- copy append data into real tables
INSERT INTO tmp_events
SELECT *
FROM events
ON CONFLICT DO NOTHING;

INSERT INTO tmp_plots
SELECT *
FROM plots
ON CONFLICT DO NOTHING;

-- delete temp tables
DROP TABLE events;
DROP TABLE plots;

-- rename the temp tables back to the real tables
ALTER TABLE tmp_events
    RENAME TO events;

ALTER TABLE tmp_plots
    RENAME TO plots;

-- recreate the indexes
CREATE INDEX ix_events_event_type ON events USING btree (event_type);
CREATE INDEX ix_events_sweeper_id ON events USING btree (sweeper_id);
CREATE INDEX ix_events_timestamp ON events USING btree ("timestamp");

CREATE INDEX ix_plots_event_id_desc ON plots USING btree (event_id DESC);
CREATE INDEX ix_plots_sweep_id_desc ON plots USING btree (sweep_id DESC);
CREATE INDEX ix_plots_timestamp_desc ON plots USING btree ("timestamp" DESC);
CREATE INDEX ix_plots_ward_number_plot_number_timestamp_desc ON plots USING btree (ward_number, plot_number, "timestamp" DESC);
CREATE INDEX ix_plots_world_id_territory_type_id_ward_number_plot_number ON plots USING btree (world_id, territory_type_id, ward_number, plot_number);
-- CREATE INDEX ix_plots_owner_name ON plots USING btree (owner_name);
CREATE INDEX ix_plots_world_id_owner_name_timestamp ON plots USING btree (world_id, owner_name, "timestamp");

ALTER TABLE ONLY plots
    ADD CONSTRAINT plots_event_id_fkey FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE;
