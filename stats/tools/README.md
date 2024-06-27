# Tools

These are not really stat generators in their own right, they're SQL scripts and stuff to import and shuffle around data
from cold storage for analysis.

Note: `<host>` can be `paissadb` if running postgres locally or a postgres uri, like
`postgresql://prism.lan:5432/paissadb`.

Last data timestamp imported: `paissadb-data-1638477984.sql`

Last pre-Endwalker data: `paissadb-data-1638477984.sql`
Last pre-Dawntrail data: `paissadb-1719435132.sql.gz` (includes all Endwalker data - last
id `plot_states 3673581; events 22382986`)

## 1st Time Import

Create tables from scratch and insert data.

```bash
psql <host> -f paissadb-schema-1625642101.sql
psql <host> -f remove-constraints.sql
psql <host> -1 -c 'set session_replication_role = replica;' -f paissadb-data-(...).sql
psql <host> -1 -f restore-constraints.sql
```

Run the main server once to import world/district gamedata if not previously done.

## Append Data

Append data from new files to existing tables, deduplicating rows.

```bash
psql <host> -1 -f prepare-append.sql
psql <host> -1 -c "set session_replication_role = replica;" -f paissadb-data-(...).sql
psql <host> -1 -f finalize-append.sql
```

## Big Dump

```bash
pg_dump --data-only --no-owner -t plot_states -t events -v -Z 9 -f paissadb-data-endwalker.sql.gz paissadb
```
