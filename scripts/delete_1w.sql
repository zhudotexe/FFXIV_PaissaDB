-- Deletes events older than 2 days from when this script is run, and all child rows (due to cascading).
DELETE
FROM paissadb.public.events
WHERE paissadb.public.events.timestamp < NOW() - '2 day'::interval;

-- only run this in the dead of night, because it locks the db!
VACUUM (FULL, VERBOSE) paissadb.public.events, paissadb.public.plots, paissadb.public.wardsweeps;
