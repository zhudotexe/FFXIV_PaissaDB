# PaissaDB

[![Discord](https://img.shields.io/discord/927834873916440646?color=5865F2&label=discord&logo=discord&logoColor=white)](https://discord.gg/9rduk8aDek)

PaissaDB is the companion API for the [PaissaHouse](https://github.com/zhudotexe/FFXIV_PaissaHouse) FFXIV plugin.

Note that PaissaDB only supports game servers that are marked as public in the NA game client; this means that KR and CN
servers are not supported.

## API Specification

You can find the Swagger docs at https://paissadb.zhu.codes/docs.

**Important: All ward IDs and plot IDs returned by PaissaDB are 0-indexed!**

### Endpoints

Note: Some endpoints expect a valid JWT (see PaissaHouse JWT below).

#### POST /ingest

Takes a list of packets (subclasses of `schemas.ffxiv.BaseFFXIVPacket`) from the game and ingests them. Requires a
PaissaHouse JWT.

#### POST /hello

Called by PaissaHouse on startup to register sweeper's world and name. Requires a PaissaHouse JWT.

```python
class Hello:
    cid: int
    name: str
    world: str
    worldId: int
```

#### GET /worlds

Gets a list of known worlds, and for each world, returns a ``WorldSummary``.

#### GET /worlds/{world_id:int}

For the specified world, returns a ``WorldDetail``.

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
    data: OpenPlotDetail;
}
```

##### Plot Update

Sent each time a plot with the lottery purchase system updates its entry count or lottery state.

```typescript
{
    type: "plot_update";
    data: PlotUpdate;
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
[RFC 6455 sec. 5.5.2](https://datatracker.ietf.org/doc/html/rfc6455#section-5.5.2). In addition to this ping packet,
PaissaDB will send a RFC6455-compliant ping packet occasionally (and will respond to pings from clients with a pong); it
is up to the client to choose which ping implementation to use.

```typescript
{
    type: "ping";
}
```

### Schemas

#### WorldSummary

```python
class WorldSummary:
    id: int
    name: str
```

#### OpenPlotDetail

```python
class OpenPlotDetail:
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int  # 0 = small, 1 = medium, 2 = large
    price: int
    last_updated_time: float  # UNIX timestamp
    est_time_open_min: float  # UNIX timestamp
    est_time_open_max: float  # UNIX timestamp
    purchase_system: PurchaseSystem 
    lotto_entries: int | None  # None if unknown or FCFS
    lotto_phase: int | None  # None if unknown or FCFS; 1 = entry, 2 = results, 3 = unavailable until next entry phase
    lotto_phase_until: int | None  # None if unknown or FCFS; UNIX timestamp
```

#### PlotUpdate

Only sent for lottery-based plots whenever the number of lottery entries increases or the lotto phase changes or is 
resolved for the first time.

```python
class PlotUpdate:
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int  # 0 = small, 1 = medium, 2 = large
    price: int
    last_updated_time: float  # UNIX timestamp
    purchase_system: PurchaseSystem
    lotto_entries: int | None
    lotto_phase: int | None  # 1 = entry, 2 = results, 3 = unavailable until next entry phase
    previous_lotto_phase: int | None  # 1 = entry, 2 = results, 3 = unavailable until next entry phase
    lotto_phase_until: int | None  # UNIX timestamp
```

#### SoldPlotDetail

```python
class SoldPlotDetail:
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int  # 0 = small, 1 = medium, 2 = large
    last_updated_time: float  # UNIX timestamp
    est_time_sold_min: float  # UNIX timestamp
    est_time_sold_max: float  # UNIX timestamp
```

#### PurchaseSystem

The purchase system of a plot can be determined by examining the 3 lower bits of the `purchase_system` field.
If the lowest bit is set (`purchase_system & 1`), it is a lottery plot; otherwise, it is an FCFS plot.
If the second lowest bit is set (`purchase_system & 2`), the plot is available for purchase by free companies.
If the third lowest bit is set (`purchase_system & 4`), the plot is available for purchase by individuals.

```python
# FCFS = 0  (implicit by lack of lottery tag)
LOTTERY = 1
FREE_COMPANY = 2
INDIVIDUAL = 4
```

#### DistrictDetail

```python
class DistrictDetail:
    id: int
    name: str
    num_open_plots: int
    oldest_plot_time: float
    open_plots: List[OpenPlotDetail]
```

#### WorldDetail

```python
class WorldDetail:
    id: int
    name: str
    districts: List[DistrictDetail]
    num_open_plots: int
    oldest_plot_time: float
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

## Developer Notes

Q: How do I tell if a plot is available for purchase for the first time?

A: If you receive a packet that meets any of the following conditions, the packet represents the first packet sent
while the plot is available for purchase, and you should send notifications to interested parties:

1. The `type` is `plot_open` and the `purchase_system` is FCFS (`purchase_system & 1 == 0`)
2. The `type` is `plot_open` and the `purchase_system` is Lottery (`purchase_system & 1 == 1`), and
   1. Its `lotto_phase` is Available (1)
3. The `type` is `plot_update` and the `purchase_system` is Lottery (`purchase_system & 1 == 1`), and
   1. Its `lotto_phase` is Available (1), and
   2. Its `previous_lotto_phase` is *not* Available (1)

This means that the packet that indicates whether or not a plot is available for purchase may be a `plot_open` *or*
`plot_update` packet, and that a `plot_open` packet may not represent a plot that is available for purchase.

## Updating Game Data

Using [SaintCoinach.Cmd](https://github.com/xivapi/SaintCoinach), run `SaintCoinach.Cmd.exe "<path to FFXIV>" rawexd`
and copy the following files to `gamedata/`:

- HousingLandSet.csv (used to generate `plotinfo`)
- PlaceName.csv (used to generate `districts`)
- TerritoryType.csv (used to generate `districts`)
- World.csv (used to generate `worlds`)

It is recommended to run this once after each patch.
