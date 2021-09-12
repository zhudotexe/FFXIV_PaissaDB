-- metrics
-- Aug 28, 2021
-- Adds the following columns:
-- sweepers.last_seen = Column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())
--
-- Alters the following columns:
-- wardsweeps.event_id: add NOT NULL constraint

ALTER TABLE sweepers
    ADD last_seen timestamp WITHOUT TIME ZONE DEFAULT NOW();

ALTER TABLE wardsweeps
    ALTER COLUMN event_id SET NOT NULL;
