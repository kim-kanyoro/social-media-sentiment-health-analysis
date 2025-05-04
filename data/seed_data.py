from faker import Faker
import random
import json

fake = Faker()

# Function to generate a single fake user
def generate_fake_user():
    return {
        "userid": fake.uuid4(),
        "name": fake.name(),
        "email": fake.email(),
        "password": fake.password(),
        "role": random.choice(["user", "admin"]),  # Randomly assign user or admin role
    }

# Function to generate a list of fake users
def generate_fake_users(n=1000):
    return [generate_fake_user() for _ in range(n)]

# Function to save the generated fake users to a JSON file
def save_fake_users_to_file(file_name="data/fake_users.json"):
    users = generate_fake_users()
    with open(file_name, "w") as file:
        json.dump(users, file)

# Run this file to seed data
if __name__ == "__main__":
    save_fake_users_to_file()  # Generates and saves 1000 fake users by default
    print("Fake users generated.")
