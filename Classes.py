import csv
import json

Donation = [{"donation_ID": None,
     "donor_name": None,
     "food_type": None,
     "quantity": None,
     "expires_on": None,
     "pickup_area": None,
     "ready_time": None
     }] 

Recipient = [{"recipient_ID": None,
     "organization_name": None,
     "accepted_food_types": set(),
     "capacity": None,
     "pickup_area": None,
     "closing_time": None,
     "ready_time": None
     }]

Volunteer = [{
    "volunteer_id": None,
    "vehicle_capacity": None,
    "area_location": None,
    "availability": None,
    "maximum_pickups": None
}]

Assignment = [{"donation_id": None,
     "recipient_id": None,
     "volunteer_id": None,
     "scheduled_time": None,
     "decision_reason": None,
     "status": None
}]


Assignment_History = []


def create_assignment(donation, recipients, volunteers):
    pass

def upload_file(file_path):
     if file_path.endswith(".csv"):
         return csv_to_dict(file_path)
     elif file_path.endswith(".json"):
          return json_to_dict(file_path)
     else:
          raise ValueError("Unsupported file format")


def csv_to_dict(file_path):
    result = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            result.append(row)
    return result

def json_to_dict(file_path):
    result = []
    with open(file_path) as jsonfile:
        data = json.load(jsonfile)
        for row in data:
            result.append(row)
    return result


def main():
    while True:
        print("1. Upload Donation File")
        print("2. Upload Recipient File")
        print("3. Upload Volunteer File")
        print("4. Create Assignment")
        print("5. View Assignment History")
        print("6. Exit")
        choice = input("Enter your choice (numeric value): ")
        if choice == "1":
            file_path = input("Enter the donation file path: ")
            global Donation 
            Donation = upload_file(file_path)
        elif choice == "2":
            file_path = input("Enter the recipient file path: ")
            global Recipient
            Recipient = upload_file(file_path)
        elif choice == "3":
            file_path = input("Enter the volunteer file path: ")
            global Volunteer
            Volunteer = upload_file(file_path)
        elif choice == "4":
            for donation in Donation:
                create_assignment(donation, Recipient, Volunteer)
        elif choice == "5":
            for assignment in Assignment_History:
                print(assignment)
        elif choice == "6":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()