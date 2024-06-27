-- drop idxs, constraints
-- plot_states
DROP INDEX IF EXISTS ix_plot_states_last_seen_desc;
DROP INDEX IF EXISTS ix_plot_states_loc_last_seen_desc;
ALTER TABLE plot_states
    DROP CONSTRAINT IF EXISTS plot_states_territory_type_id_plot_number_fkey;
ALTER TABLE plot_states
    DROP CONSTRAINT IF EXISTS plot_states_world_id_fkey;
ALTER TABLE plot_states
    DROP CONSTRAINT IF EXISTS plot_states_territory_type_id_fkey;

-- events
DROP INDEX IF EXISTS ix_events_event_type;
DROP INDEX IF EXISTS ix_events_sweeper_id;
DROP INDEX IF EXISTS ix_events_timestamp;
ALTER TABLE events
    DROP CONSTRAINT IF EXISTS events_sweeper_id_fkey;
ALTER TABLE events
    DROP CONSTRAINT IF EXISTS events_pkey CASCADE;
