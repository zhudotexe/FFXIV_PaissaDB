-- purchase_system
-- Feb 19, 2022
-- Adds the following columns:
-- plot_states.purchase_system = Column(Integer)
--
-- Deletes the following columns:
-- plot_states.is_fcfs

ALTER TABLE plot_states
    ADD COLUMN purchase_system INTEGER NOT NULL DEFAULT 6,
    DROP COLUMN is_fcfs,
    ALTER COLUMN purchase_system DROP DEFAULT;
