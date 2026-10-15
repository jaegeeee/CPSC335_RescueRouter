#Run with:  python3 -m unittest -v test_rescue_router
import os
import tempfile
import unittest

import RR as rr

HERE = os.path.dirname(os.path.abspath(__file__))

DONATION_HEADER = "donation_ID,donor_name,food_type,quantity,ready_time,shelf_life_minutes,pickup_area"
RECIPIENT_HEADER = "recipient_ID,organization_name,accepted_food_types,capacity,pickup_area,closing_time"
VOLUNTEER_HEADER = "volunteer_ID,volunteer_name,vehicle_capacity,pickup_area,available_from,available_until,max_pickups"

# Defaults: one recipient and one Volunteer in North that can take anything reasonable.
DEFAULT_RECIPIENT = "R-1,Shelter,prepared;bakery,100,North,22:00"
DEFAULT_VOLUNTEER = "V-1,Driver,100,North,16:00,22:00,5"


class RescueRouterTest(unittest.TestCase):
    def setUp(self):
        rr.Donations.clear()
        rr.Recipients.clear()
        rr.Volunteers.clear()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, name, header, rows):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", newline="") as f:
            f.write("\n".join([header] + rows) + "\n")
        return path

    def load(self, donations, recipients=(DEFAULT_RECIPIENT,), volunteers=(DEFAULT_VOLUNTEER,)):
        """Load rows through RR's real CSV upload/cleaning path."""
        self.assertTrue(rr.clean_uploaded_data(self.write_csv("d.csv", DONATION_HEADER, list(donations)), 1))
        self.assertTrue(rr.clean_uploaded_data(self.write_csv("r.csv", RECIPIENT_HEADER, list(recipients)), 2))
        self.assertTrue(rr.clean_uploaded_data(self.write_csv("v.csv", VOLUNTEER_HEADER, list(volunteers)), 3))

    # 1. Normal compatible match
    def test_normal_compatible_match(self):
        self.load(["D-1,Cafe,prepared,40,17:00,180,North"])
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(unmatched, [])
        self.assertEqual(len(assignments), 1)
        a = assignments[0]
        self.assertEqual((a["donation_ID"], a["recipient_ID"], a["volunteer_ID"]), ("D-1", "R-1", "V-1"))
        self.assertEqual(a["delivery_quantity"], 40)
        self.assertEqual(f"{a['scheduled_time']:%H:%M}", "17:00")  # max(ready 17:00, available 16:00)
        self.assertEqual(a["status"], "assigned")

    # 2. Duplicate donation ID
    def test_duplicate_donation_id_keeps_one_record(self):
        self.load([
            "D-1,Cafe,prepared,40,17:00,180,North",
            "D-1,Cafe Copy,prepared,99,17:00,180,North",
        ])
        self.assertEqual(len(rr.Donations), 1)
        assignments, _ = rr.FIFO_sort()
        # The duplicate must not be delivered twice.
        self.assertEqual([a["donation_ID"] for a in assignments].count("D-1"), 1)

    # 3a. Already expired donation
    def test_expired_donation_is_not_assigned(self):
        self.load(["D-1,Old Food,prepared,30,17:00,0,North"])
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(assignments, [])
        self.assertEqual(unmatched[0]["status"], "unassigned")
        self.assertIn("donation expires at or before the scheduled time", unmatched[0]["decision_reason"])

    # 3b. Nearly expired: food is fine at ready time but expires before the volunteer is free
    def test_nearly_expired_donation_expires_before_volunteer_arrives(self):
        self.load(
            ["D-1,Cafe,prepared,30,17:00,30,North"],  # expires 17:30
            volunteers=["V-1,Late Driver,100,North,17:45,22:00,5"],
        )
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(assignments, [])
        self.assertIn("donation expires at or before the scheduled time", unmatched[0]["decision_reason"])

    # 4. No compatible recipient food type
    def test_no_compatible_food_type(self):
        self.load(["D-1,Dairy Farm,dairy,20,17:00,180,North"])
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(assignments, [])
        self.assertIn("recipient does not accept dairy", unmatched[0]["decision_reason"])

    # 5. Insufficient recipient capacity
    def test_insufficient_recipient_capacity_partially_assigns(self):
        self.load(
            ["D-1,Cafe,prepared,50,17:00,180,North"],
            recipients=["R-1,Small Shelter,prepared,20,North,22:00"],
        )
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(sum(a["delivery_quantity"] for a in assignments), 20)
        self.assertEqual(unmatched[0]["quantity"], 30)
        self.assertEqual(unmatched[0]["status"], "partially assigned")

    # 6. No volunteer with enough vehicle capacity
    def test_no_volunteer_with_enough_vehicle_capacity(self):
        self.load(
            ["D-1,Cafe,prepared,30,17:00,180,North"],
            volunteers=["V-1,Bike Courier,10,North,16:00,22:00,1"],
        )
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["delivery_quantity"], 10)
        self.assertEqual(unmatched[0]["quantity"], 20)
        self.assertEqual(unmatched[0]["status"], "partially assigned")

    def test_volunteer_with_zero_capacity_is_rejected(self):
        self.load(
            ["D-1,Cafe,prepared,30,17:00,180,North"],
            volunteers=["V-1,No Car,0,North,16:00,22:00,3"],
        )
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(assignments, [])
        self.assertIn("volunteer has no vehicle capacity or pickups remaining", unmatched[0]["decision_reason"])

    # 7. Two donations competing for the same capacity
    def test_two_donations_compete_for_same_capacity(self):
        self.load(
            ["D-1,Early,prepared,40,17:00,180,North",
             "D-2,Late,prepared,40,17:30,180,North"],
            recipients=["R-1,Shelter,prepared,50,North,22:00"],
        )
        assignments, unmatched = rr.FIFO_sort()

        delivered = {}
        for a in assignments:
            delivered[a["donation_ID"]] = delivered.get(a["donation_ID"], 0) + a["delivery_quantity"]
        self.assertEqual(delivered, {"D-1": 40, "D-2": 10})  # first in line gets it all
        self.assertEqual([(d["donation_ID"], d["quantity"]) for d in unmatched], [("D-2", 30)])

    # 8a. Empty input file
    def test_empty_donation_file_loads_nothing(self):
        path = os.path.join(self.tmp.name, "empty.csv")
        open(path, "w").close()

        self.assertTrue(rr.clean_uploaded_data(path, 1))
        self.assertEqual(rr.Donations, {})
        self.assertEqual(rr.FIFO_sort(), ([], []))

    # 8b. Empty recipient and volunteer lists
    def test_empty_recipients_and_volunteers(self):
        self.load(["D-1,Cafe,prepared,40,17:00,180,North"], recipients=[], volunteers=[])
        assignments, unmatched = rr.FIFO_sort()

        self.assertEqual(assignments, [])
        reason = unmatched[0]["decision_reason"]
        self.assertIn("no recipients were loaded", reason)
        self.assertIn("no volunteers were loaded", reason)

    # 9. FIFO and greedy produce different results
    def test_fifo_and_greedy_differ(self):
        self.load(
            ["D-1,Bakery,bakery,40,17:00,300,North",       # arrives first, long shelf life
             "D-2,Caterer,prepared,40,17:30,60,North"],    # arrives later, spoils fast
            recipients=["R-1,Shelter,prepared;bakery,40,North,22:00"],
        )
        fifo, _ = rr.FIFO_sort()
        greedy, _ = rr.greedy_sort()

        self.assertEqual([a["donation_ID"] for a in fifo], ["D-1"])
        self.assertEqual([a["donation_ID"] for a in greedy], ["D-2"])

    # 10. Fairness / starvation: deferred donation explains why
    def test_starved_donation_explains_deferral(self):
        self.load(
            ["D-1,Bakery,bakery,40,17:00,300,North",
             "D-2,Caterer,prepared,40,17:30,60,North"],
            recipients=["R-1,Shelter,prepared;bakery,40,North,22:00"],
        )
        _, unmatched = rr.greedy_sort()

        self.assertEqual(len(unmatched), 1)
        starved = unmatched[0]
        self.assertEqual(starved["donation_ID"], "D-1")
        self.assertEqual(starved["status"], "unassigned")
        self.assertEqual(starved["priority_reason"], "priority position 2: scheduled after D-2 with shorter shelf life")
        self.assertTrue(starved["decision_reason"])

    # Sanity check on the real project data: nothing created or lost
    def test_project_data_quantities_reconcile(self):
        for path, choice in [("donations.csv", 1), ("recipients.csv", 2), ("volunteers.csv", 3)]:
            self.assertTrue(rr.clean_uploaded_data(os.path.join(HERE, path), choice))
        total = sum(d["quantity"] for d in rr.Donations.values())

        for sort in (rr.FIFO_sort, rr.greedy_sort):
            assignments, unmatched = sort()
            delivered = sum(a["delivery_quantity"] for a in assignments)
            left = sum(d["quantity"] for d in unmatched)
            self.assertEqual(delivered + left, total, sort.__name__)
        # Sorting works on copies, so the loaded data is untouched.
        self.assertEqual(sum(d["quantity"] for d in rr.Donations.values()), total)


if __name__ == "__main__":
    unittest.main()
