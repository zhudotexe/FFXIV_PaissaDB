-- world_dc_names
-- May 28, 2022
--
-- Adds the following columns:
-- worlds.datacenter_id = Column(Integer)
-- worlds.datacenter_name = Column(String)

ALTER TABLE paissadb.public.worlds
    ADD COLUMN datacenter_id INTEGER,
    ADD COLUMN datacenter_name VARCHAR;
