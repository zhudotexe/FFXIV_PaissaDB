-- Deletes events and plot states older than 9 days from when this script is run.
DELETE
FROM paissadb.public.events
WHERE paissadb.public.events.timestamp < EXTRACT(EPOCH FROM NOW() - '9 day'::interval);

DELETE
FROM plot_states
WHERE lotto_phase_until < EXTRACT(EPOCH FROM NOW() - '9 day'::interval);

-- only run this in the dead of night, because it locks the db!
VACUUM (FULL, VERBOSE) paissadb.public.events;
VACUUM (FULL, VERBOSE) paissadb.public.plot_states;
