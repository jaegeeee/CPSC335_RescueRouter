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

## Algorithm design
 
### A. FIFO baseline
 
Donations are processed in `ready_time` order. Each one takes the first feasible
recipient and volunteer.
 
### B. Greedy urgency-first
 
**The rule, precisely:** schedule donations in ascending order of
`shelf_life_minutes` where least remaining shelf life gets put first. Ties are broken by
Python's stable sort, which preserves the order the donations were loaded in.
 
Within a donation, recipients are tried in ascending `closing_time` order and
volunteers in ascending `available_from` order. That means the recipient closing
soonest gets served first, which leaves later-closing recipients available for
donations that come up later in the queue.
 
**What it optimizes.** At each step it makes the choice that minimises the chance of the next donation spoiling,
without any regard to what that costs later. It never asks whether serving this donation blocks a better one.
 
**Why it's reasonable.** The thing that makes this problem hard is that
donations expire. A donation with 45 minutes left can be taken before it expires, and 
one with 300 minutes can wait through several other assignments and still be fine. Serving the urgent one 
first costs the patient one very little and saves food that FIFO would lose outright. On our sample data greedy rescues 375 units
to FIFO's 385.
 
**Fairness and starvation.** Donations with long shelf lives are repeatedly deferred. 
Under greedy a patient donation can sit at the back of the queue while every urgent donation ahead
of it consumes capacity, and then find nothing left. Tt is starved precisely because it was in good condition. Our sample data
shows this: D-1002 (90 units, 240 minutes of shelf life) is fully delivered
under FIFO and completely unassigned under greedy.
`test_starved_donation_explains_deferral` covers this case directly, and every deferred donation carries a `priority_reason` saying which 
donation displaced it and why.

## Limitations
 
- **Not a real food-safety or routing system.** All data is simulated. Nothing
  here is approved for real food handling or operational use.
- **No travel time.** Same-area pickups are treated as instant, and cross-area
  matches are simply infeasible. Real distance would change which matches are
  reachable before expiry.
- **Single simulated day.** All times are `HH:MM` on one day. Anything crossing
  midnight would break.
- **No global optimisation.** Both strategies are one-pass and never revisit a
  decision.
- **No persistence.** Data lives in memory for the session only.
- **Assumptions of timing.** We are running based off of the assumption that
  we have all the data before the first delivery is initiated.

## Complexity
 
Let **D** = donations, **R** = recipients, **V** = volunteers, and **A** = total
assignment records produced.
 
**Sorting:** `O(D log D + R log R + V log V)`, done once per strategy.
 
**Matching:** for each donation the inner loops scan recipients and volunteers
until a feasible pair is found — `O(R * V)` in the worst case. 
Splitting means a donation may re-enter that scan more than once, but each extra pass produces an
assignment record, and every record consumes either recipient capacity or one of
a volunteer's pickups. So the number of passes across the whole run is bounded by `D + A`, giving O((D + A) * R * V)
 
**Dominant work:** the recipient × volunteer scan inside the matching loop.
Every feasibility check is `O(1)` — dict lookups, set membership for food types,
and integer/datetime comparisons
---



**Team Contributions:**
Jerry: Created the github repository and initial algorithms structures in the RR.py. Created the upload file logics and helper functions. Created the the terminal outputs interface.Made changes to algorithm and code after meeting.
