-- metrics
-- Dec 9, 2021
--
-- ok actually just delete the db and recreate it

DROP SCHEMA public;

CREATE SCHEMA public;
COMMENT ON SCHEMA public IS 'standard public schema';
ALTER SCHEMA public OWNER TO postgres;
GRANT CREATE, USAGE ON SCHEMA public TO PUBLIC;
