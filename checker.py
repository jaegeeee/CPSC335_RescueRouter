import os
import tempfile

import RR as rr

DONATIONS = "donations.csv"
RECIPIENTS = "recipients.csv"
VOLUNTEERS = "volunteers.csv"


def reset():
    """Clear RR lists so each check starts clean."""
    rr.Donation.clear()
    rr.Recipient.clear()
    rr.Volunteer.clear()
    rr.Assignment.clear()
    rr.Unassigned_Donations.clear()


def load(donations=DONATIONS):
    reset()
    rr.clean_uploaded_data(donations, 1)
    rr.clean_uploaded_data(RECIPIENTS, 2)
    rr.clean_uploaded_data(VOLUNTEERS, 3)


def formatting(title):
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


formatting("BASELINE — FIFO vs GREEDY")

load()
print(f"loaded: {len(rr.Donation)} donations, "
      f"{len(rr.Recipient)} recipients, {len(rr.Volunteer)} volunteers")

for label, fn in [("FIFO", rr.FIFO_sort), ("GREEDY", rr.greedy_sort)]:
    records, unmatched = fn()
    delivered = sum(r["delivery_quantity"] for r in records)
    print(f"\n{label}: {len(records)} assignment records, "
          f"{delivered} delivered, {len(unmatched)} unmatched")
    for r in records:
        print(f"    {r['donationID']} -> {r['recipientID']} "
              f"{r['volunteerID']}  qty {r['delivery_quantity']}")
    print("    unmatched:",
          [(d["donation_ID"], d["quantity"]) for d in unmatched])



#expiry check
formatting("CHECK 1 — is expiry enforced?")

print("Feeding one donation with shelf_life_minutes = 0.")
print("It is already expired the moment it is ready, so it should")
print("never be assigned.\n")

tmp = os.path.join(tempfile.gettempdir(), "_expired_donation.csv")
with open(tmp, "w", newline="") as f:
    f.write("donation_ID,donor_name,food_type,quantity,"
            "ready_time,shelf_life_minutes,pickup_area\n")
    f.write("D-9001,Expired Foods,prepared,30,17:00,0,North\n")

load(donations=tmp)
records, unmatched = rr.FIFO_sort()

print("  assignments:", records)
print("  unmatched:  ", [(d["donation_ID"], d["quantity"]) for d in unmatched])

if records:
    print("\n  >>> Expired food was assigned and delivered.")
    print("  >>> shelf_life_minutes is only used as the greedy sort key —")
    print("  >>> there is no expiry condition in assign().")
else:
    print("\n  OK — expiry is enforced.")

os.remove(tmp)


# assigned v unassigned check
formatting("CHECK 2 — do the assigned / unassigned counts reconcile?")

load()
total = len(rr.Donation)

for label, fn in [("FIFO", rr.FIFO_sort), ("GREEDY", rr.greedy_sort)]:
    records, unmatched = fn()
    assigned_ids = {r["donationID"] for r in records}
    unmatched_ids = {d["donation_ID"] for d in unmatched}
    both = sorted(assigned_ids & unmatched_ids)

    print(f"\n{label}: {total} donations in, "
          f"{len(records)} assignment records + "
          f"{len(unmatched)} unmatched = {len(records) + len(unmatched)}")
    if both:
        print(f"  >>> appears in BOTH lists: {both}")
        print("  >>> these were split across multiple pickups, so they are partly delivered and partly not.")
        print("  >>> Donation assigned has no single definition while this is true.")

# "car holds 100, so do 100 every trip" OR "car holds 100 so I'll do 100 units and thats it"
formatting("CHECK 3 — is vehicle_capacity per-pickup or a total budget?")

load()
before = {v["volunteer_ID"]: (v["vehicle_capacity"], v["max_pickups"])
          for v in rr.Volunteer}

records, _ = rr.FIFO_sort()

hauled = {}
for r in records:
    hauled[r["volunteerID"]] = hauled.get(r["volunteerID"], 0) \
                               + r["delivery_quantity"]

print("volunteer   per-pickup cap   max pickups   total hauled   "
      "capacity if per-pickup")
for vid, (cap, pickups) in sorted(before.items()):
    carried = hauled.get(vid, 0)
    print(f"  {vid}        {cap:>5}          {pickups:>5}        "
          f"{carried:>7}            {cap * pickups:>6}")

print("\n  >>> assign() does `vehicle_capacity -= delivery_quantity`,")
print("  >>> so capacity is spent down across the whole run. Under the")
print("  >>> documented schema it is a per-pickup limit, so each driver")
print("  >>> should be able to carry up to their capacity on every trip.")

print("\n" + "=" * 62)