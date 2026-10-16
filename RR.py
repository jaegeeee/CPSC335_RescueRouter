import csv
import json
from datetime import datetime, timedelta

CHOICE = ["Donation", "Recipient", "Volunteer"]

#changed to dict per the documentation. made volunteer a dict as well
Donations = {} 
Recipients = {}
Volunteers = {}

#FilePaths
CSV_Files = ["donation.csv", "recipient.csv", "volunteer.csv"]
JSON_Files = ["donation.json", "recipient.json", "volunteer.json"] 


def upload_file(file_path):
    try:
        if file_path.endswith(".csv"):
            return csv_to_dict(file_path)
        elif file_path.endswith(".json"):
            return json_to_dict(file_path)
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
        display_header("ERROR")
        print(f"Error uploading file: {e}")
        return []

def csv_to_dict(file_path):
    try:
        result = []
        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                result.append(row)
        return result
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

def json_to_dict(file_path): 
    try:
        result = []
        with open(file_path) as jsonfile:
            data = json.load(jsonfile)
            for row in data:
                result.append(row)
        return result
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return []

#helper functions for uploading and cleaning data
def clean_uploaded_data(file_path,choice):
    global Donations, Recipients, Volunteers
    uploaded_file = upload_file(file_path)
    try:
        if choice == 1:
            uploaded_file = remove_duplicate_donations(uploaded_file)
            for row in uploaded_file:
                row["quantity"] = int(row["quantity"]) if row["quantity"] is not None else None
                row["ready_time"] = datetime.strptime(row["ready_time"], "%H:%M") if row["ready_time"] is not None else None
                row["shelf_life_minutes"] = int(row["shelf_life_minutes"]) if row["shelf_life_minutes"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None
            for row in uploaded_file:
                Donations[row["donation_ID"]] = row
            return True
        elif choice == 2:
            for row in uploaded_file:
                row["accepted_food_types"] = set(row["accepted_food_types"]) if isinstance(row["accepted_food_types"], list) else set(row["accepted_food_types"].split(";"))
                row["capacity"] = int(row["capacity"]) if row["capacity"] is not None else None
                row["closing_time"] = datetime.strptime(row["closing_time"], "%H:%M") if row["closing_time"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None
            for row in uploaded_file:
                Recipients[row["recipient_ID"]] = row
            return True
        elif choice == 3:
            for row in uploaded_file:
                row["vehicle_capacity"] = int(row["vehicle_capacity"]) if row["vehicle_capacity"] is not None else None
                row["available_from"] = datetime.strptime(row["available_from"], "%H:%M") if row["available_from"] is not None else None
                row["available_until"] = datetime.strptime(row["available_until"], "%H:%M") if row["available_until"] is not None else None
                row["max_pickups"] = int(row["max_pickups"]) if row["max_pickups"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None
            for row in uploaded_file:
                Volunteers[row["volunteer_ID"]] = row
            return True
        else:
            return False
    except (ValueError, TypeError) as error:
        print(f"Error cleaning file: {error}")
        return False

def display_options():
    print("\n")
    print(f"\t1. Upload Donation File")
    print(f"\t2. Upload Recipient File")
    print(f"\t3. Upload Volunteer File")
    print(f"\t4. Create & View FIFO/Greedy Assignments")
    print(f"\t5. Exit")
    print(f'\n')

def display_header(title):
    print("\n" + "=" * 50)
    print(f"{title}")
    print("=" * 50)


def display_history(temp_assignment, temp_unassigned_donations, label):
    if not temp_assignment:
        print(f"\nNo assignments created yet for {label}.\n")
    else:
        print("Assigned Donations:")
        for assigned in temp_assignment:
            print(f"\nAssigned: {assigned['decision_reason']}")
            print(f"  Order: {assigned['priority_reason']}")
    if temp_unassigned_donations:
        print("\nUnassigned Donations:")
        for unassigned in temp_unassigned_donations:
            print(f"\n{unassigned['status'].capitalize()}: {unassigned['decision_reason']}")
            print(f"  Order: {unassigned['priority_reason']}")


def candidate_reasons(donation, recipient, volunteer): #this function calculates the scheduled time for a donation and explains why a match with a recipient and volunteer might be infeasible
    """Calculate scheduled time and explain why a donation match is infeasible."""
    scheduled_time = max(donation["ready_time"], volunteer["available_from"])
    expires_at = donation["ready_time"] + timedelta(minutes=donation["shelf_life_minutes"])
    reasons = []

    if donation["pickup_area"] != recipient["pickup_area"]:
        reasons.append("recipient is outside the donation pickup area")
    if donation["pickup_area"] != volunteer["pickup_area"]:
        reasons.append("volunteer is outside the donation pickup area")
    if donation["food_type"] not in recipient["accepted_food_types"]:
        reasons.append(f"recipient does not accept {donation['food_type']}")
    if recipient["capacity"] <= 0:
        reasons.append("recipient has no remaining capacity")
    if volunteer["vehicle_capacity"] <= 0 or volunteer["max_pickups"] <= 0:
        reasons.append("volunteer has no vehicle capacity or pickups remaining")
    if scheduled_time > volunteer["available_until"]:
        reasons.append("scheduled time is outside volunteer availability")
    if scheduled_time > recipient["closing_time"]:
        reasons.append("scheduled time is after recipient closing time")
    if scheduled_time >= expires_at:
        reasons.append("donation expires at or before the scheduled time")

    return scheduled_time, reasons, expires_at


#FIFO sorting and assignment function: "Process donations in arrival order/'ready_time'. For each donation, assign the first feasible recipient and volunteer. Record unmatched donations"
#sorted by ready_time for donations, pickup_area for recipients, and available_from for volunteers. gets first feasible recipient and volunteer for each donation.
#the greedy assignment: "Sort donations by "Shelf_life_minutes". For each donation, assign the first feasible recipient and volunteer. Record unmatched donations"


def priority_reasons(donations, strategy): #this function describes each donation's position in the selected strategy's queue relative to other donations
    """Describe each donation's position in the selected strategy's queue."""
    reasons = {}
    for index, donation in enumerate(donations):
        donation_id = donation["donation_ID"]
        position = f"Donation {donation_id} was considered {index + 1} of {len(donations)}"
        if strategy == "FIFO":
            rule = "under the first-in-first-out rule"
            if index == 0:
                reasons[donation_id] = f"{position} because it was ready earliest ({donation['ready_time']:%H:%M}) {rule}."
            else:
                previous = donations[index - 1]
                if donation["ready_time"] == previous["ready_time"]:
                    detail = f"it was ready at the same time as {previous['donation_ID']} ({donation['ready_time']:%H:%M}), so file order was kept"
                else:
                    detail = f"{previous['donation_ID']} was ready earlier ({previous['ready_time']:%H:%M} vs {donation['ready_time']:%H:%M})"
                reasons[donation_id] = f"{position}, after {previous['donation_ID']}, because {detail} {rule}."
        else:
            rule = "under the urgency-first greedy rule"
            if index == 0:
                reasons[donation_id] = f"{position} because it had the least shelf life ({donation['shelf_life_minutes']} minutes) {rule}."
            else:
                previous = donations[index - 1]
                if donation["shelf_life_minutes"] == previous["shelf_life_minutes"]:
                    detail = f"it had the same shelf life as {previous['donation_ID']} ({donation['shelf_life_minutes']} minutes), so file order was kept"
                else:
                    detail = (f"{previous['donation_ID']} had less remaining shelf life "
                              f"({previous['shelf_life_minutes']} vs {donation['shelf_life_minutes']} minutes)")
                reasons[donation_id] = f"{position}, after {previous['donation_ID']}, because {detail} {rule}."
    return reasons #at the end it returns a dictionary mapping each donation's ID to its priority explanation

def assign(sort_type, sorted_Donations, sorted_Recipients, sorted_Volunteers):
    assignments = []
    unmatched_donations = []
    priorities = priority_reasons(sorted_Donations, sort_type)

    for donation in sorted_Donations:
        original_quantity = donation["quantity"] #this stores the initial quantity of the donation before any assignments are made
        rejection_reasons = set() #this will store the reasons why a donation could not be assigned
        if not sorted_Recipients: #this checks if there are no recipients loaded
            rejection_reasons.add("no recipients were loaded") #this adds a rejection reason if no recipients are loaded
        if not sorted_Volunteers: #this checks if there are no volunteers loaded
            rejection_reasons.add("no volunteers were loaded") #this adds a rejection reason if no volunteers are loaded

        while donation["quantity"] > 0:
            assigned = False
            for recipient in sorted_Recipients:
                for volunteer in sorted_Volunteers:
                    scheduled_time, reasons, expires_at = candidate_reasons(donation, recipient, volunteer)
                    if reasons:
                        if donation["pickup_area"] == recipient["pickup_area"] == volunteer["pickup_area"]: #reasons from other areas would add noise to the explanation, simplifying for readability
                            rejection_reasons.update(reasons)
                        continue
                    quantity = min(donation["quantity"], volunteer["vehicle_capacity"], recipient["capacity"])
                    minutes_left = int((expires_at - scheduled_time).total_seconds() // 60)
                    organization = recipient["organization_name"]
                    explanation = (
                        f"Donation {donation['donation_ID']} was assigned to {organization} with volunteer "
                        f"{volunteer['volunteer_name']} ({volunteer['volunteer_ID']}) at {scheduled_time:%H:%M} for {quantity} items "
                        f"because it expires in {minutes_left} minutes (at {expires_at:%H:%M}), "
                        f"{organization} accepts {donation['food_type']} and has room for {recipient['capacity']} more items "
                        f"before closing at {recipient['closing_time']:%H:%M}, and the volunteer is available until "
                        f"{volunteer['available_until']:%H:%M} and can carry {volunteer['vehicle_capacity']} items per pickup."
                    )
                    if quantity < donation["quantity"]:
                        limit = "the vehicle capacity" if quantity == volunteer["vehicle_capacity"] else "the recipient's remaining capacity"
                        explanation += f" This pickup carries {quantity} of the {donation['quantity']} remaining items, limited by {limit}."
                    assignments.append({
                        "donation_ID": donation["donation_ID"],
                        "recipient_ID": recipient["recipient_ID"],
                        "volunteer_ID": volunteer["volunteer_ID"],
                        "scheduled_time": scheduled_time,
                        "delivery_quantity": quantity,
                        "decision_reason": explanation,
                        "priority_reason": priorities[donation["donation_ID"]],
                        "status": "assigned",
                    })

                    #used up recipients and volunteers sray in the lists so later donations get "no remaining capactiy" for reason
                    recipient["capacity"] -= quantity #decrease the recipient's capacity by the assigned quantity
                    volunteer["max_pickups"] -= 1 #decrease the volunteer's remaining pickups by 1
                    donation["quantity"] -= quantity #decrease the donation's remaining quantity by the assigned quantity
                    assigned = True

                    break
                if assigned:
                    break
            if not assigned:
                break
        if donation["quantity"] > 0:
            if not rejection_reasons:
                rejection_reasons.add(f"no recipient and volunteer pair both serve the {donation['pickup_area']} pickup area")
            because = "; ".join(sorted(rejection_reasons))
            remaining = donation["quantity"]
            if remaining < original_quantity:
                donation["status"] = "partially assigned"
                donation["decision_reason"] = (
                    f"Donation {donation['donation_ID']} was only partially assigned: {original_quantity - remaining} of "
                    f"{original_quantity} items were delivered, but the remaining {remaining} could not be assigned because {because}."
                )
            else:
                donation["status"] = "unassigned"
                donation["decision_reason"] = (
                    f"Donation {donation['donation_ID']} ({original_quantity} items) could not be assigned because {because}."
                )
            donation["priority_reason"] = priorities[donation["donation_ID"]]
            unmatched_donations.append(donation)


    return assignments, unmatched_donations

def FIFO_sort():
    sorted_Donations = sorted((dict(d) for d in Donations.values()), key=lambda x: x["ready_time"])
    sorted_Recipients = sorted((dict(r) for r in Recipients.values()), key=lambda x: x["closing_time"])
    sorted_Volunteers = sorted((dict(v) for v in Volunteers.values()), key=lambda x: x["available_from"])
    return assign("FIFO",sorted_Donations, sorted_Recipients, sorted_Volunteers)

def greedy_sort():
    sorted_Donations = sorted((dict(d) for d in Donations.values()), key=lambda x: x["shelf_life_minutes"])
    sorted_Recipients = sorted((dict(r) for r in Recipients.values()), key=lambda x: x["closing_time"]) 
    sorted_Volunteers = sorted((dict(v) for v in Volunteers.values()), key=lambda x: x["available_from"])
    return assign("greedy", sorted_Donations, sorted_Recipients, sorted_Volunteers)


def calculate_and_display_results(assignments, unmatched_donations, label):
    donations_delivered = sum(a["delivery_quantity"] for a in assignments)
    donations_undelivered = sum(d["quantity"] for d in unmatched_donations)

    display_header(label + " Assignment Results")
    if label == "FIFO":
        print("Priority rule: donations are handled in order of ready time (first in, first out).")
    else:
        print("Priority rule: donations with the least shelf life are handled first (urgency-first greedy).")
    print(
        "Each donation goes to the first recipient (earliest closing) and volunteer (earliest available) that pass every check:\n"
        "same pickup area, food type accepted, recipient capacity left, volunteer capacity and pickups left,\n"
        "pickup within volunteer hours and before the recipient closes, and pickup before the food expires.\n"
        "Pickup time is the later of the donation's ready time and the volunteer's start time.\n"
    )
    print(
        f"Assigned {len(assignments)} donations for delivery with total quantity delivered: {donations_delivered}\n"
        f"{len(unmatched_donations)} donations were not assigned for delivery with {donations_undelivered} total quantity.\n"
    )
    display_history(assignments, unmatched_donations, label)





def create_assignment():
    if not Donations or not Recipients or not Volunteers:
        print("\n Missing files! Please upload all three files before creating an assignment.\n")
        return
    else:
        FIFO_delivered = 0
        Greedy_delivered = 0
        for label, selected_sort in [("FIFO", FIFO_sort), ("GREEDY", greedy_sort)]:

            temp_assignment, temp_unassigned_donations = selected_sort()
            
            calculate_and_display_results(temp_assignment, temp_unassigned_donations, label)
            
            FIFO_delivered = sum(a["delivery_quantity"] for a in temp_assignment) if label == "FIFO" else FIFO_delivered
            Greedy_delivered = sum(a["delivery_quantity"] for a in temp_assignment) if label == "GREEDY" else Greedy_delivered

        if FIFO_delivered > Greedy_delivered:
            print("\n___FIFO performed better than Greedy.___\n")
        elif FIFO_delivered < Greedy_delivered:
            print("\n___Greedy performed better than FIFO.___\n")
        else:
            print("\n___FIFO and Greedy performed equally.___\n")


def remove_duplicate_donations(rows): #keeps the first record for each donation ID, including IDs already loaded, and reports the rest
    seen = set(Donations.keys())
    unique_rows = []
    duplicates = []
    for row in rows:
        if row["donation_ID"] in seen:
            duplicates.append(row["donation_ID"])
        else:
            seen.add(row["donation_ID"])
            unique_rows.append(row)
    if duplicates:
        print(f"Removed duplicate donations (first record kept): {duplicates}")
    return unique_rows

def main():
    data_lists = {1: Donations, 2: Recipients, 3: Volunteers}
    display_header("Rescue Router Main Menu")
    while True:
        display_options()
        try:
            choice = int(input("Enter your choice (numeric value): "))
        except ValueError:
            print("Invalid choice. Please try again.")
            continue
        if choice in [1, 2, 3]:
            file_path = input(f"\nEnter {CHOICE[choice-1]} file path: ").strip().strip('"')
            if clean_uploaded_data(file_path,choice):
                print(f"\n{CHOICE[choice-1]} uploaded and processed.")
                print(f"\n{CHOICE[choice-1]} contains {len(data_lists[choice])} records.\n")
        elif choice == 4:
            create_assignment()
        elif choice == 5:
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()