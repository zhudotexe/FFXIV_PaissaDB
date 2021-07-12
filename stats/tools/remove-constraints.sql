-- drop idxs, constraints
-- plots
drop index ix_plots_event_id_desc;
drop index ix_plots_sweep_id_desc;
drop index ix_plots_timestamp_desc;
drop index ix_plots_ward_number_plot_number_timestamp_desc;
drop index ix_plots_world_id_territory_type_id_ward_number_plot_number;
alter table plots drop constraint plots_pkey;
alter table plots drop constraint plots_event_id_fkey;
alter table plots drop constraint plots_sweep_id_fkey;
alter table plots drop constraint plots_territory_type_id_fkey;
alter table plots drop constraint plots_territory_type_id_plot_number_fkey;
alter table plots drop constraint plots_world_id_fkey;

-- events
drop index ix_events_event_type;
drop index ix_events_sweeper_id;
drop index ix_events_timestamp;
alter table events drop constraint events_sweeper_id_fkey;
alter table events drop constraint events_pkey cascade;
