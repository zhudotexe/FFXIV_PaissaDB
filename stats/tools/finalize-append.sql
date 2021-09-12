-- copy append data into real tables
INSERT INTO tmp_events
SELECT *
FROM events
ON CONFLICT DO NOTHING;

INSERT INTO tmp_plots
SELECT *
FROM plots
ON CONFLICT DO NOTHING;

-- delete temp tables
DROP TABLE events;
DROP TABLE plots;

-- rename the temp tables back to the real tables
ALTER TABLE tmp_events
    RENAME TO events;

ALTER TABLE tmp_plots
    RENAME TO plots;
