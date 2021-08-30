-- move data containing tables
ALTER TABLE events
    RENAME TO tmp_events;

ALTER TABLE plots
    RENAME TO tmp_plots;

-- recreate the tables we want
CREATE TABLE public.events
(
    id          integer NOT NULL,
    sweeper_id  bigint,
    "timestamp" timestamp WITHOUT TIME ZONE,
    event_type  public.eventtype,
    data        text
);

CREATE TABLE public.plots
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

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.plots
    ADD CONSTRAINT plots_pkey PRIMARY KEY (id);

CREATE INDEX ix_events_event_type ON public.events USING btree (event_type);
CREATE INDEX ix_events_sweeper_id ON public.events USING btree (sweeper_id);
CREATE INDEX ix_events_timestamp ON public.events USING btree ("timestamp");

CREATE INDEX ix_plots_event_id_desc ON public.plots USING btree (event_id DESC);
CREATE INDEX ix_plots_sweep_id_desc ON public.plots USING btree (sweep_id DESC);
CREATE INDEX ix_plots_timestamp_desc ON public.plots USING btree ("timestamp" DESC);
CREATE INDEX ix_plots_ward_number_plot_number_timestamp_desc ON public.plots USING btree (ward_number, plot_number, "timestamp" DESC);
CREATE INDEX ix_plots_world_id_territory_type_id_ward_number_plot_number ON public.plots USING btree (world_id, territory_type_id, ward_number, plot_number);

ALTER TABLE ONLY public.plots
    ADD CONSTRAINT plots_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events (id) ON DELETE CASCADE;

-- create additional statgen indexes
-- todo optimize the chonky queries here

-- copy data from tmp tables
INSERT INTO events
SELECT *
FROM tmp_events
ON CONFLICT DO NOTHING;

INSERT INTO plots
SELECT *
FROM tmp_plots
ON CONFLICT DO NOTHING;

-- delete tmp tables
DROP TABLE tmp_events;
DROP TABLE tmp_plots;
VACUUM FULL;
