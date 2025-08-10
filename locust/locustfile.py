from locust import HttpUser, TaskSet, task, between
import random

class PassengerBehavior(TaskSet):
    @task(5)
    def request_ride(self):
        passenger_id = random.randint(1, 10)
        self.client.post("/request_ride", json={"passenger_id": passenger_id})

    @task(2)
    def check_ride_status(self):
        ride_id = random.randint(1, 50)
        self.client.get(f"/ride_status/{ride_id}")

class DriverBehavior(TaskSet):
    @task(5)
    def get_available_rides(self):
        self.client.get("/available_rides")

    @task(3)
    def accept_ride(self):
        ride_id = random.randint(1, 50)
        driver_id = random.randint(1, 5)
        self.client.post(f"/accept_ride/{ride_id}?driver_id={driver_id}")

    @task(2)
    def complete_ride(self):
        ride_id = random.randint(1, 50)
        driver_id = random.randint(1, 5)
        self.client.post(f"/complete_ride/{ride_id}?driver_id={driver_id}")

class PassengerUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [PassengerBehavior]
    host = "http://localhost:8001"  # passenger-service

class DriverUser(HttpUser):
    wait_time = between
