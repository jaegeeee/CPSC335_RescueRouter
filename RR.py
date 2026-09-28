import csv
import json
from datetime import datetime

CHOICE = ["Donation", "Recipient", "Volunteer"]

Donation = [] 
Recipient = []
Volunteer = []
Assignment = []
Unassigned_Donations = []

def upload_file(file_path):
    try:
        if file_path.endswith(".csv"):
            return csv_to_dict(file_path)
        elif file_path.endswith(".json"):
            return json_to_dict(file_path)
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
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
    global Donation, Recipient, Volunteer
    uploaded_file = upload_file(file_path)
    try:
        if choice == 1: #clean up donations
            for row in uploaded_file: #clean up data
                row["quantity"] = int(row["quantity"]) if row["quantity"] is not None else None
                row["ready_time"] = datetime.strptime(row["ready_time"], "%H:%M") if row["ready_time"] is not None else None
                row["shelf_life_minutes"] = int(row["shelf_life_minutes"]) if row["shelf_life_minutes"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None

            Donation.extend(uploaded_file)

        elif choice == 2: #clean up recipients

            for row in uploaded_file: #clean up data
                row["accepted_food_types"] = set(row["accepted_food_types"]) if isinstance(row["accepted_food_types"], list) else set(row["accepted_food_types"].split(";"))
                row["capacity"] = int(row["capacity"]) if row["capacity"] is not None else None
                row["closing_time"] = datetime.strptime(row["closing_time"], "%H:%M") if row["closing_time"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None

            Recipient.extend(uploaded_file)

        elif choice == 3: #clean up volunteers

            for row in uploaded_file: #clean up data
                row["vehicle_capacity"] = int(row["vehicle_capacity"]) if row["vehicle_capacity"] is not None else None
                row["available_from"] = datetime.strptime(row["available_from"], "%H:%M") if row["available_from"] is not None else None
                row["available_until"] = datetime.strptime(row["available_until"], "%H:%M") if row["available_until"] is not None else None
                row["max_pickups"] = int(row["max_pickups"]) if row["max_pickups"] is not None else None
                row["pickup_area"] = row["pickup_area"].strip() if row["pickup_area"] is not None else None

            Volunteer.extend(uploaded_file)
        else:
            return
    except (ValueError, TypeError) as e:
            print(f"Error cleaning file: {e}")
            return




#FIFO sorting and assignment function: "Process donations in arrival order/'ready_time'. For each donation, assign the first feasible recipient and volunteer. Record unmatched donations"
# sorted by ready_time for donations, pickup_area for recipients, and available_from for volunteers. gets first feasible recipient and volunteer for each donation.
#the greedy assignment: "Sort donations by "Shelf_life_minutes". For each donation, assign the first feasible recipient and volunteer. Record unmatched donations"

def assign(sort_type, sorted_Donations, sorted_Recipients, sorted_Volunteers):
    assignment = []
    unmatched_donations = []
    
    for donation in sorted_Donations:
        while donation["quantity"] > 0:
            assigned = False
            for recipient in sorted_Recipients:
                for volunteer in sorted_Volunteers:
                    if donation["pickup_area"] == recipient["pickup_area"] == volunteer["pickup_area"] \
                        and donation["food_type"] in recipient["accepted_food_types"] \
                        and donation["ready_time"] <= recipient["closing_time"] \
                        and volunteer["available_until"] >= donation["ready_time"] >= volunteer["available_from"] \
                        and volunteer["vehicle_capacity"] > 0 and volunteer["max_pickups"] > 0 and recipient["capacity"] > 0:
                        assignment.append({
                            "donationID": donation["donation_ID"],
                            "recipientID": recipient["recipient_ID"],
                            "volunteerID": volunteer["volunteer_ID"],
                            "delivery_quantity": min(donation["quantity"], volunteer["vehicle_capacity"], recipient["capacity"]),
                            "sort_format": sort_type
                        })

                        assigned = True
                        
                        #update donation/recipient/volunteer status after assignment. this leaves the possibility of partially fulfilled donations, recipients, or volunteers.
                        volunteer["vehicle_capacity"] -= assignment[-1]["delivery_quantity"]
                        volunteer["max_pickups"] -= 1
                        if volunteer["max_pickups"] == 0 or volunteer["vehicle_capacity"] == 0:
                            sorted_Volunteers.remove(volunteer)

                        recipient["capacity"] -= assignment[-1]["delivery_quantity"]
                        if recipient["capacity"] == 0:
                            sorted_Recipients.remove(recipient)

                        donation["quantity"] -= assignment[-1]["delivery_quantity"]
                        break
                if assigned:
                    break
            if not assigned:
                break
        if donation["quantity"] > 0:
            unmatched_donations.append(donation)
    return assignment, unmatched_donations




def FIFO_sort():
    sorted_Donations = sorted((dict(d) for d in Donation), key=lambda x: x["ready_time"])
    sorted_Recipients = sorted((dict(r) for r in Recipient), key=lambda x: x["closing_time"])
    sorted_Volunteers = sorted((dict(v) for v in Volunteer), key=lambda x: x["available_from"])
    return assign("FIFO",sorted_Donations, sorted_Recipients, sorted_Volunteers)


def greedy_sort():
    sorted_Donations = sorted((dict(d) for d in Donation), key=lambda x: x["shelf_life_minutes"])
    sorted_Recipients = sorted((dict(r) for r in Recipient), key=lambda x: x["closing_time"])
    sorted_Volunteers = sorted((dict(v) for v in Volunteer), key=lambda x: x["available_from"])
    return assign("greedy", sorted_Donations, sorted_Recipients, sorted_Volunteers)

    

def create_assignment():
    if not Donation or not Recipient or not Volunteer:
        print("\n Missing files! Please upload all three files before creating an assignment.\n")
        return
    FIFO_assignment, FIFO_unmatched_donations = FIFO_sort()
    FIFO_delivered = sum(a["delivery_quantity"] for a in FIFO_assignment)
    print("\n---FIFO Assignment Results:---\n")
    print(f"Total assignments created: {len(FIFO_assignment)}")
    print(f"Total quantity delivered: {FIFO_delivered}")
    print(f"Total unassigned donations: {len(FIFO_unmatched_donations)}")
    Assignment.append(FIFO_assignment)
    Unassigned_Donations.append(FIFO_unmatched_donations)


    print("\n---Greedy Assignment Results:---\n")
    Greedy_assignment, Greedy_unmatched_donations = greedy_sort()
    Greedy_delivered = sum(a["delivery_quantity"] for a in Greedy_assignment)
    print(f"Total assignments created: {len(Greedy_assignment)}")
    print(f"Total quantity delivered: {Greedy_delivered}")
    print(f"Total unassigned donations: {len(Greedy_unmatched_donations)}")
    Assignment.append(Greedy_assignment)
    Unassigned_Donations.append(Greedy_unmatched_donations)
    
    if FIFO_delivered > Greedy_delivered:
        print("\n___FIFO performed better than Greedy.___\n")
    elif FIFO_delivered < Greedy_delivered:
        print("\n___Greedy performed better than FIFO.___\n")
    else:
        print("\n___FIFO and Greedy performed equally.___\n")



def main():
    data_lists = {1: Donation, 2: Recipient, 3: Volunteer}

    while True:
        print("1. Upload Donation File")
        print("2. Upload Recipient File")
        print("3. Upload Volunteer File")
        print("4. Create FIFO/Greedy Assignments")
        print("5. View Assignment History")
        print("6. Exit")
        try:
            choice = int(input("Enter your choice (numeric value): "))
        except ValueError:
            print("Invalid choice. Please try again.")
            continue


        if choice in [1, 2, 3]:
            file_path = input(f"\nEnter {CHOICE[choice-1]} file path: ").strip().strip('"')
            clean_uploaded_data(file_path,choice)
            print(f"\n{CHOICE[choice-1]} uploaded and processed.")
            print(f"\n{CHOICE[choice-1]} contains {len(data_lists[choice])} records.\n")
        elif choice == 4:
                create_assignment()
        elif choice == 5:
            if not Assignment:
                print("\nNo assignments created yet.\n")
            for assigned_donations, unassigned_donations in zip(Assignment, Unassigned_Donations):
                print(f"\n{assigned_donations[0]['sort_format'] if assigned_donations else 'Run'} assignments:")
                for assigned in assigned_donations:
                    print(assigned)
                print("Unassigned donations:")
                for unassigned in unassigned_donations:
                    print(f"{unassigned['donation_ID']} (remaining quantity: {unassigned['quantity']})")
            print("\n---\n")
        elif choice == 6:
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()