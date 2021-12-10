-- metrics
-- Dec 9, 2021
--
-- ok actually just delete the db and recreate it

DROP SCHEMA paissadb.public;

CREATE SCHEMA paissadb.public;
COMMENT ON SCHEMA paissadb.public IS 'standard public schema';
ALTER SCHEMA paissadb.public OWNER TO postgres;
GRANT CREATE, USAGE ON SCHEMA paissadb.public TO PUBLIC;
