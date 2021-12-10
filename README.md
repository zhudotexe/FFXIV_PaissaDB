# PaissaDB

PaissaDB is the companion API for the [PaissaHouse](https://github.com/zhudotexe/FFXIV_PaissaHouse) FFXIV plugin.

Note that PaissaDB only supports game servers that are marked as public in the NA game client; this means that KR and CN
servers are not supported.

## API Specification

You can find the Swagger docs at https://paissadb.zhu.codes/docs.

**Important: All ward IDs and plot IDs returned by PaissaDB are 0-indexed!**

### Endpoints

Note: Some endpoints expect a valid JWT (see PaissaHouse JWT below).

#### POST /wardInfo

Takes a HousingWardInfo object from the game and ingests it. Requires a PaissaHouse JWT.

#### POST /hello

Called by PaissaHouse on startup to register sweeper's world and name. Requires a PaissaHouse JWT.

```typescript
{
    cid: int;
    name: string;
    world: string;
    worldId: int;
}
```

#### GET /worlds

Gets a list of known worlds, and for each world:

```typescript
{
    id: int;
    name: string;
    num_open_plots: int;
    oldest_plot_time: float; // the oldest datapoint of all plots on this world
    districts: DistrictSummary[];
}[];
```

#### GET /worlds/{world_id:int}

For the specified world, returns:

```typescript
{
    id: int;
    name: string;
    num_open_plots: int;
    oldest_plot_time: float; // the oldest datapoint of all plots on this world
    districts: DistrictDetail[];
}
```

#### GET /worlds/{world_id:int}/{district_id:int}

For the specified district in the specified world, returns a list of ``DistrictDetail``.

#### Websocket /ws?jwt={jwt}

Clients connected to this websocket will receive update events each time a house changes state (owned -> open or open ->
sold). Connecting to the websocket requires a valid JWT.

##### Plot Opened

Sent each time a plot transitions from owned to opened, or is seen for the first time and is open.

```typescript
{
    type: "plot_open";
    data: OpenPlotDetail;  // same as World Detail endpoint
}
```

##### Plot Sold

Sent each time a previously open plot transitions to owned.

```typescript
{
    type: "plot_sold";
    data: SoldPlotDetail;
}
```

##### Ping

Sent every minute, to keep the websocket open. If the client does not receive a ping for >120s, it should reconnect.

Note that this ping packet is not the standard ping defined in 
[RFC 6455 sec. 5.5.2](https://datatracker.ietf.org/doc/html/rfc6455#section-5.5.2). 
In addition to this ping packet, PaissaDB will send a RFC6455-compliant ping packet occasionally (and will respond to
pings from clients with a pong); it is up to the client to choose which ping implementation to use.

```typescript
{
    type: "ping";
}
```

### Schemas

#### DistrictSummary

```typescript
{
    id: int;
    name: string;
    num_open_plots: int;
    oldest_plot_time: float; // the oldest datapoint of all plots in this district
}
```

#### OpenPlotDetail

```typescript
{
    world_id: int;
    district_id: int;
    ward_number: int; // 0-indexed
    plot_number: int; // 0-indexed
    size: int; // 0 = Small, 1 = Medium, 2 = Large
    known_price: int;
    last_updated_time: float;
    est_time_open_min: float; // the earliest time this plot could have opened, given the update times and devalues
    est_time_open_max: float; // the latest time this plot could have opened, given the update times and devalues
    est_num_devals: int;  // the estimated number of devalues at the time of the request
}
```

#### DistrictDetail

```typescript
{
    id: int;
    name: string;
    num_open_plots: int;
    oldest_plot_time: float; // the oldest datapoint of all plots in this district
    open_plots: OpenPlotDetail[];
}
```

#### SoldPlotDetail

```typescript
{
    world_id: int;
    district_id: int;
    ward_number: int; // 0-indexed
    plot_number: int; // 0-indexed
    size: int; // 0 = Small, 1 = Medium, 2 = Large
    last_updated_time: float;
    est_time_sold_min: float; // the earliest time this plot could have sold, given the update times
    est_time_sold_max: float; // the latest time this plot could have sole, given the update times
}
```

### PaissaHouse JWT

Standard [JWT spec](https://jwt.io/) using HS256 for signature verification with the following payload:

```typescript
{
    cid: int; // character's content ID
    iss: "PaissaDB";
    aud: "PaissaHouse";
    iat: float; // JWT generation timestamp
}
```

This JWT should be sent as an `Authorization` bearer header to all endpoints that require it. Note that the `iss` claim
is `PaissaDB` regardless of what service generates the token.

## Updating Game Data

Using [SaintCoinach.Cmd](https://github.com/xivapi/SaintCoinach), run `SaintCoinach.Cmd.exe "<path to FFXIV>" rawexd`
and copy the following files to `gamedata/`:

- HousingLandSet.csv (used to generate `plotinfo`)
- PlaceName.csv (used to generate `districts`)
- TerritoryType.csv (used to generate `districts`)
- World.csv (used to generate `worlds`)

It is recommended to run this once after each patch.
