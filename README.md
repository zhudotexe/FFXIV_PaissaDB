# PaissaDB

PaissaDB is the companion website for the [PaissaHouse](https://github.com/zhudotexe/FFXIV_PaissaHouse) FFXIV plugin

## API Specification

You can find the Swagger docs at https://paissadb.zhu.codes/docs.

### Endpoints (Draft)

Note: all endpoints should be prefixed with the relevant APi version (`/v1`). Some endpoints expect a valid JWT (see
PaissaHouse JWT).

#### POST /wardInfo

Takes a HousingWardInfo object from the game and ingests it. Requires a PaissaHouse JWT.

Returns `201` on success, `400` if invalid data, `401` if missing JWT, or `403` if invalid JWT.

#### POST /hello

Called by PaissaHouse on startup to register sweeper's world and name. Requires a PaissaHouse JWT.

```typescript
{
    cid: number;
    name: string;
    world: string;
    worldId: number;
}
```

#### GET /worlds

Gets a list of known worlds, and for each world:

- the world name
- the number of open plots per district
- last sweep time per district

#### GET /worlds/{world_id:int}

For the specified world, returns:

- the world name
- the list of district names
- the list of open plots per district
    - last updated time
    - selling price
    - estimated time open
    - estimated primetime
    - house size
    - ward id
    - plot id

#### TODO: Websocket @ /

Clients connected to this websocket will receive update events each time a house changes state (owned -> open or open ->
sold). Spec TBD.

### PaissaHouse JWT

Standard [JWT spec](https://jwt.io/) using HS256 for signature verification with the following payload:

```typescript
{
    cid: number | null; // character's content ID; may be null or omitted for anonymous contribution
    iss: "PaissaHouse";
    aud: "PaissaDB";
    iat: number; // JWT generation timestamp
}
```

This JWT should be sent as an `Authorization` bearer header to all endpoints that require it.
