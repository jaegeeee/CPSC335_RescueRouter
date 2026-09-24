# RescueRoute — Sample Input Data

Test data for the RescueRoute project. 

**note:** names here are a suggestion.

## Schema

### donations

| Field | Type | Notes |
|---|---|---|
| `donation_id` | string | Unique, format `D-####` |
| `donor_name` | string | |
| `food_type` | string | One of: `prepared`, `produce`, `bakery`, `dairy`, `canned` |
| `quantity` | integer | Arbitrary units |
| `ready_time` | `HH:MM` | 24-hour, same simulated day |
| `shelf_life_minutes` | integer | Minutes from `ready_time` until it expires |
| `area` | string | `North`, `Central`, `South` |

Expiry is derived: `expires_at = ready_time + shelf_life_minutes`.

Storing shelf life rather than an absolute `expires_at` matches the project description's
"expiry/remaining shelf life" wording.

### recipients

| Field | Type | Notes |
|---|---|---|
| `recipient_id` | string | `R-###` |
| `organization_name` | string | |
| `accepted_food_types` | string | **Semicolon**-separated; parse to a `set` |
| `capacity` | integer | Total, depletes as donations are assigned |
| `area` | string | |
| `closing_time` | `HH:MM` | Nothing can be delivered after this |

### volunteers

| Field | Type | Notes |
|---|---|---|
| `volunteer_id` | string | `V-###` |
| `volunteer_name` | string | |
| `vehicle_capacity` | integer | Per-pickup limit |
| `area` | string | |
| `available_from` / `available_until` | `HH:MM` | |
| `max_pickups` | integer | Total pickups across the run |

## Assumptions about this data

1. **Same area required.** Travel time is 0 within an area; cross-area is
   infeasible. (Can change later)
2. `scheduled_time = max(donation.ready_time, volunteer.available_from)`
3. Feasible requires all of: food type accepted · recipient has remaining
   capacity ≥ quantity · volunteer `vehicle_capacity` ≥ quantity · volunteer
   under `max_pickups` · `scheduled_time ≤ expires_at` · `≤ closing_time` ·
   `≤ available_until`
