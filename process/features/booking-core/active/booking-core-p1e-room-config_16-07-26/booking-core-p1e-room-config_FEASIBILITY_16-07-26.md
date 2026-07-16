---
slug: booking-core-p1e-room-config
date: 2026-07-16
verdict: VIABLE
originating-phase: spec
---

# FEASIBILITY: Does `/roomsSummary` `noOfRooms` include out-of-service rooms?

## Hypothesis

OPERA Cloud's `GET /rm/config/v1/roomsSummary` endpoint's `noOfRooms` field counts ALL rooms
including out-of-service/pseudo rooms, not just sellable in-service rooms.

## Mechanism Under Test

Whether the `noOfRooms` aggregate count field on `configRoomsSummaryType` (from the `roomsSummary`
response) is computed from the raw room inventory including rooms currently flagged
`roomStatus: "OutOfOrder"`, or whether it is pre-filtered to exclude them.

## Probe Family

4 — External API shape capture (live 3rd-party API response).

## Probe Cost Class

`needs-live-provider`. Safety gate: explicit double opt-in already granted by the user earlier in
this session ("Xác nhận, tiến hành gọi") and documented in the SPEC's Constraints/Open Questions
sections. Gate met — probe executed.

## Probe Method

1. **Static spec check first** (`docs/OPERA Cloud Room Configuration API (26.2.0.0).json`):
   `configRoomsSummaryType.noOfRooms` description is just `"Current number of rooms."` — no
   OOS/pseudo exclusion language. The `/roomsSummary` query params include `pseudo` (filter to
   pseudo room type) and `physical` (filter to physical room type), but no OOS/OOO/status filter
   param exists on this endpoint. Per-room `roomStatus` (e.g. `OutOfOrder`, `Clean`, `Dirty`) only
   appears nested in `roomSummary[].roomType.roomStatus` (housekeeping status), not as a top-level
   count-exclusion flag. Spec alone was inconclusive on whether `noOfRooms` reflects filtered or
   unfiltered counts — live call was needed.
2. **Auth:** reused `BaseOperaClient._set_auth_headers()` unchanged (OAuth client-credentials +
   `x-app-key` + `x-hotelid`), per SPEC Constraints ("no new auth mechanism").
3. **Endpoint correction found during probe:** the spec's `basePath` is `/rm/config/v1` — the
   initial call to bare `/roomsSummary` 404'd. Corrected to `/rm/config/v1/roomsSummary`. (Note for
   PLAN/EXECUTE: the extractor implementation must include this `basePath` prefix — it is not
   implicit in `settings.opera_base_url`.)
4. **Live calls made** (hotelId = `settings.opera_hotel_id`, current `.env` credentials, read-only
   GET, no mutation):
   - `GET /rm/config/v1/roomsSummary?hotelId={id}&limit=1000` (unfiltered)
   - `GET /rm/config/v1/roomsSummary?hotelId={id}&limit=1000&pseudo=false`
   - `GET /rm/config/v1/roomsSummary?hotelId={id}&limit=1000&physical=true`
5. Compared the top-level `noOfRooms` aggregate against a manual count of the per-room
   `roomSummary[]` array, cross-tabulated by `roomType.roomStatus` and `roomType.pseudo`.

## Evidence Captured

| Query | `noOfRooms` | `roomSummary[]` length | roomStatus breakdown |
|---|---|---|---|
| unfiltered | 49 | 93 | (mixed pseudo+physical rooms) |
| `pseudo=false` | 49 | (not re-counted; same `noOfRooms`) | — |
| `physical=true` | 49 | 49 | `OutOfOrder: 6, Clean: 22, Dirty: 21` |

Physical-only room set (`physical=true`), full per-room roomStatus breakdown:
```
{'OutOfOrder': 6, 'Clean': 22, 'Dirty': 21}
```
Total = 6 + 22 + 21 = 49, matching `noOfRooms: 49` exactly.

Unfiltered call: `roomSummary[]` returns 93 records (49 physical + 44 pseudo rooms, room IDs
9000-9030 and 9500-9512, all `roomStatus: Clean` since pseudo rooms have no housekeeping status in
practice). `noOfRooms` stays at 49 in both the unfiltered and `physical=true` calls — i.e.
`noOfRooms` already excludes the 44 pseudo rooms by default (matches the physical count, not the
raw `roomSummary[]` array length).

**Key finding:** `noOfRooms` (49) = the physical room count INCLUDING all 6 rooms currently flagged
`roomStatus: "OutOfOrder"`. If `noOfRooms` had excluded OOO rooms, it would read 43, not 49.

## Verdict

**VIABLE** — hypothesis confirmed. `noOfRooms` includes out-of-service (`OutOfOrder`) rooms. It does
NOT include pseudo rooms (already excluded by default, matching the `physical=true` filtered
result). The dashboard's Occupancy% (OCC) calculation must subtract OOS rooms from the denominator
if it wants a "sellable rooms" occupancy base — `noOfRooms` alone is not that number.

## Resulting Design Constraint

- **What this licenses:** PLAN/EXECUTE may treat `roomsSummary.noOfRooms` as "total physical
  (non-pseudo) room count including out-of-service rooms" and may safely use `physical=true` as the
  query filter to exclude pseudo rooms (already proven redundant with the default/unfiltered call in
  this property's data, but explicit is safer for other properties). If OCC needs a sellable-only
  denominator, the design must independently fetch/derive an OOS count (e.g. via the per-room
  `roomSummary[].roomType.roomStatus == "OutOfOrder"` breakdown, or a separate OOO/OOS status API
  such as `outOfOrderServiceReasons`) and subtract it from `noOfRooms`.
- **What this forbids:** PLAN/EXECUTE must NOT assume `noOfRooms` is already a "sellable rooms"
  count — using it directly as the OCC denominator without OOS adjustment will overstate the room
  base and understate occupancy whenever any rooms are out of order/service. Must also not call the
  bare `/roomsSummary` path without the `/rm/config/v1` basePath prefix (404s).
- **What remains uncertain (known-gap):** Whether OOS status is *transient/day-specific* (OOO can be
  time-boxed to a date range in OPERA) or a snapshot-only signal from this one read is unknown — this
  probe captured a single point-in-time count (6 OOO rooms right now for this property). If the
  dashboard's OCC calc needs day-level OOS-adjusted room availability (not just a current snapshot),
  a follow-up probe against the OOO/OOS status or date-ranged availability API would be needed; this
  SPEC's stated scope (aggregate `noOfRooms` only, no per-room breakdown reporting) may not require
  that granularity — INNOVATE/PLAN should confirm against Acceptance Criterion 3/4's actual precision
  need.

VC-FEASIBILITY-VERDICT-READY: VIABLE — D:\ErasProjects\ErasOpera\process\features\booking-core\active\booking-core-p1e-room-config_16-07-26\booking-core-p1e-room-config_FEASIBILITY_16-07-26.md

**Status:** DONE
**Summary:** Live probe against OPERA Cloud confirmed `noOfRooms` (49) includes all 6 currently out-of-order rooms for this property but excludes 44 pseudo rooms — dashboard OCC calc must subtract OOS separately if it wants a sellable-room denominator.
**Concerns/Blockers:** None blocking. One known-gap noted in the VERDICT (transient vs snapshot OOS semantics) for INNOVATE/PLAN to weigh against Acceptance Criterion 3/4's precision needs.
