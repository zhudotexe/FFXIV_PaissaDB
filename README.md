# PaissaDB

PaissaDB is the companion API for the [PaissaHouse](https://github.com/zhudotexe/FFXIV_PaissaHouse) FFXIV plugin.

Note that PaissaDB only supports game servers that are marked as public in the NA game client; this means that
KR and CN servers are not supported.

## API Specification

You can find the Swagger docs at https://paissadb.zhu.codes/docs.

**Important: All ward IDs and plot IDs returned by PaissaDB are 0-indexed!**

### Endpoints

Note: Some endpoints expect a valid JWT (see PaissaHouse JWT below).

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
    iss: "PaissaDB";
    aud: "PaissaHouse";
    iat: number; // JWT generation timestamp
}
```

This JWT should be sent as an `Authorization` bearer header to all endpoints that require it. Note that the `iss` claim
is `PaissaDB` regardless of what service generates the token.

## Updating Game Data

Using [SaintCoinach.Cmd](https://github.com/ufx/SaintCoinach), run `SaintCoinach.Cmd.exe "<path to FFXIV>" rawexd`
and copy the following files to `gamedata/`:

- HousingLandSet.csv (used to generate `plotinfo`)
- PlaceName.csv (used to generate `districts`)
- TerritoryType.csv (used to generate `districts`)
- World.csv (used to generate `worlds`)

It is recommended to run this once after each patch.
