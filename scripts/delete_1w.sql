-- Deletes events older than one week from when this script is run, and all child rows (due to cascading).
DELETE
FROM paissadb.public.events
WHERE paissadb.public.events.timestamp < now() - '7 day'::interval;

VACUUM FULL;  -- only run this in the dead of night, because it locks the db!
