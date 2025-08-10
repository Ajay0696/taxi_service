from locust import HttpUser, task, between
import random

class PassengerUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://passenger-service:8001"

    @task(5)
    def request_ride(self):
        passenger_id = random.randint(1, 10)
        self.client.post("/request_ride", json={"passenger_id": passenger_id})

    @task(2)
    def check_status(self):
        ride_id = random.randint(1, 50)
        self.client.get(f"/ride_status/{ride_id}")

class DriverUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://driver-service:8002"

    @task(3)
    def list_and_accept(self):
        # fetch available rides and attempt to accept a random one
        res = self.client.get("/available_rides")
        if res.status_code == 200 and res.json():
            rides = res.json()
            if rides:
                ride = random.choice(rides)
                ride_id = ride.get("id")
                driver_id = random.randint(1, 5)
                self.client.post(f"/accept_ride/{ride_id}", params={"driver_id": driver_id})

    @task(1)
    def complete_random(self):
        ride_id = random.randint(1, 50)
        driver_id = random.randint(1, 5)
        self.client.post(f"/complete_ride/{ride_id}", params={"driver_id": driver_id})
