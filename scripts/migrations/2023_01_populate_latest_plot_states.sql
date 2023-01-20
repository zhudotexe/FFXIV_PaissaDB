-- world_dc_names
-- Jan 19, 2023
--
-- Populates the latest_plot_states table based on the latest plot states in plot_states
INSERT INTO latest_plot_states (world_id, territory_type_id, ward_number, plot_number, state_id)
SELECT DISTINCT ON (world_id, territory_type_id, ward_number, plot_number) world_id,
                                                                           territory_type_id,
                                                                           ward_number,
                                                                           plot_number,
                                                                           id
FROM plot_states
ORDER BY world_id, territory_type_id, ward_number, plot_number, last_seen DESC
ON CONFLICT ON CONSTRAINT uc_latest_plot_states DO NOTHING;
