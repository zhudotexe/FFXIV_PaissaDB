-- drop idxs, constraints
-- plots
DROP INDEX IF EXISTS ix_plots_event_id_desc;
DROP INDEX IF EXISTS ix_plots_sweep_id_desc;
DROP INDEX IF EXISTS ix_plots_timestamp_desc;
DROP INDEX IF EXISTS ix_plots_ward_number_plot_number_timestamp_desc;
DROP INDEX IF EXISTS ix_plots_world_id_territory_type_id_ward_number_plot_number;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_pkey;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_event_id_fkey;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_sweep_id_fkey;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_territory_type_id_fkey;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_territory_type_id_plot_number_fkey;
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_world_id_fkey;

-- plots statgen indices
DROP INDEX IF EXISTS ix_plots_owner_name;
DROP INDEX IF EXISTS ix_plots_world_id_owner_name_timestamp;

-- events
DROP INDEX IF EXISTS ix_events_event_type;
DROP INDEX IF EXISTS ix_events_sweeper_id;
DROP INDEX IF EXISTS ix_events_timestamp;
ALTER TABLE events
    DROP CONSTRAINT IF EXISTS events_sweeper_id_fkey;
ALTER TABLE events
    DROP CONSTRAINT IF EXISTS events_pkey CASCADE;
