-- world_dc_names
-- Aug 11, 2025
--
-- Add an owner_is_fc column to plot_states
ALTER TABLE plot_states
    ADD owner_is_fc boolean;
