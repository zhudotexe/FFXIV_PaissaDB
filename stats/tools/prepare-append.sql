-- move events and plots tables
ALTER TABLE events
    RENAME TO tmp_events;

ALTER TABLE plots
    RENAME TO tmp_plots;

-- create temp target tables for append data
CREATE TABLE events
(
    id          integer NOT NULL,
    sweeper_id  bigint,
    "timestamp" timestamp WITHOUT TIME ZONE,
    event_type  eventtype,
    data        text
);

CREATE TABLE plots
(
    id                integer NOT NULL,
    world_id          integer,
    territory_type_id integer,
    ward_number       integer,
    plot_number       integer,
    "timestamp"       timestamp WITHOUT TIME ZONE,
    sweep_id          integer,
    event_id          integer,
    is_owned          boolean,
    has_built_house   boolean,
    house_price       integer,
    owner_name        character varying
);