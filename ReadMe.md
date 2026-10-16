# RescueRoute

Matches time-sensitive surplus food donations to compatible recipient
organizations and volunteer drivers. Compares a FIFO baseline against a greedy
urgency-first strategy on the same input and explains every decision it makes.

## Running it

```
python3 RR.py
```

Menu-driven. Upload the three files (options 1-3), then option 4 runs both greedy and fifo
strategies and prints the comparison.

```
python3 -m unittest -v checker
```

Runs the test suite.

## Files

| File | What it does |
|---|---|
| `RR.py` | The application — loading, validation, matching, both strategies, output |
| `checker.py` | Tests (unittest) |
| `donations.csv` / `recipients.csv` / `volunteers.csv` | Sample input |

---

## Schema

### donations

| Field | Type | Notes |
|---|---|---|
| `donation_ID` | string | Unique, format `D-####` |
| `donor_name` | string | |
| `food_type` | string | One of: `prepared`, `produce`, `bakery`, `dairy`, `canned` |
| `quantity` | integer | Arbitrary units |
| `ready_time` | `HH:MM` | 24-hour, same simulated day |
| `shelf_life_minutes` | integer | Minutes from `ready_time` until it expires |
| `pickup_area` | string | `North`, `Central`, `South` |

Expiry is derived: `expires_at = donation["ready_time"] + timedelta(minutes=donation["shelf_life_minutes"])`

Storing shelf life rather than an absolute `expires_at` was done to match the project
description's "expiry/remaining shelf life" wording.

### recipients

| Field | Type | Notes |
|---|---|---|
| `recipient_ID` | string | `R-###` |
| `organization_name` | string | |
| `accepted_food_types` | string | **Semicolon**-separated; parsed to a `set` |
| `capacity` | integer | Total, depletes as donations are assigned |
| `pickup_area` | string | |
| `closing_time` | `HH:MM` | Nothing can be delivered after this |

### volunteers

| Field | Type | Notes |
|---|---|---|
| `volunteer_ID` | string | `V-###` |
| `volunteer_name` | string | |
| `vehicle_capacity` | integer | Per-pickup limit — how much fits in the car on one trip |
| `pickup_area` | string | |
| `available_from` / `available_until` | `HH:MM` | |
| `max_pickups` | integer | Total trips across the run |

CSV and JSON are both accepted. In JSON, `accepted_food_types` can be a list
instead of a semicolon string.

---

## Architecture

RR.py works in three stages:

**Load and clean** — `upload_file` dispatches to `csv_to_dict` or
`json_to_dict`. `clean_uploaded_data` then converts strings to the types the
rest of the program needs: quantities to `int`, times to `datetime`, accepted
food types to a `set`. We needed to do this because without it, every comparison becomes a string. 
This becomes an issue when comparing two numbers that are currently strings like `"100" < "50"`.

**Store** — donations, recipients and volunteers each live in a dict keyed by
ID for direct lookup. Sets are used for accepted food types like membership or testing and for duplicate ID detection. Assignments are a list so the output keeps its order.

**Match** — `FIFO_sort` and `greedy_sort` both build sorted copies and hand them
to one shared `assign` function. The only difference between the two strategies
is the order donations are considered in. Feasibility, capacity rules and
explanations are identical, so any difference in the results comes from
ordering alone.

Both strategies sort copies (`dict(d) for d in Donations.values()`), so the
loaded data is never modified and the second run starts from the same state as
the first. `test_project_data_quantities_reconcile` checks this.

