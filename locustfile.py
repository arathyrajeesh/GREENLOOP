import json
import time
import random
from locust import HttpUser, task, between, events
from websocket import create_connection

class WebSocketClient:
    def __init__(self, host):
        self.host = host
        self.ws = None

    def connect(self, token):
        url = f"{self.host}/ws/tracking/?token={token}"
        self.ws = create_connection(url, timeout=5)

    def send(self, data):
        if self.ws:
            self.ws.send(json.dumps(data))

    def recv(self):
        if self.ws:
            return self.ws.recv()
        return None

    def close(self):
        if self.ws:
            self.ws.close()

class GreenLoopUser(HttpUser):
    abstract = True
    wait_time = between(1, 5)
    token = None
    user_id = None
    host = "http://django:8000" # Use Gunicorn for API
    ws_host = "ws://daphne:8001" # Use Daphne for WS

class ResidentUser(GreenLoopUser):
    weight = 1
    username = ""

    def on_start(self):
        self.username = f"resident_{random.randint(0, 249)}"
        email = f"{self.username}@loadtest.com"
        
        # 1. Request OTP
        resp = self.client.post("/api/v1/auth/otp/request/", json={"email": email})
        if resp.status_code == 200:
            otp = resp.json().get("test_mode_otp")
            # 2. Verify OTP
            verify_resp = self.client.post("/api/v1/auth/otp/verify/", json={
                "email": email,
                "code": otp
            })
            if verify_resp.status_code == 200:
                self.token = verify_resp.json().get("access")
                self.user_id = verify_resp.json().get("user", {}).get("id")
            else:
                print(f"OTP Verify failed for {email}: {verify_resp.text}")
        else:
            print(f"OTP Request failed for {email}: {resp.text}")

    @task(3)
    def list_pickups(self):
        if self.token:
            self.client.get("/api/v1/pickups/", headers={"Authorization": f"Bearer {self.token}"})

    @task(2)
    def list_complaints(self):
        if self.token:
            self.client.get("/api/v1/complaints/", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def request_pickup(self):
        if self.token:
            self.client.post("/api/v1/pickups/", json={
                "waste_type": random.choice(["dry", "wet", "hazardous"]),
                "location": {"type": "Point", "coordinates": [76.9467 + random.uniform(-0.01, 0.01), 8.4875 + random.uniform(-0.01, 0.01)]},
                "scheduled_date": time.strftime("%Y-%m-%d")
            }, headers={"Authorization": f"Bearer {self.token}"})

class WorkerUser(GreenLoopUser):
    weight = 1
    username = ""
    ws_client = None

    def on_start(self):
        self.username = f"worker_{random.randint(0, 249)}"
        # 1. Login via password
        response = self.client.post("/api/v1/auth/worker-login/", json={
            "username": self.username,
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access")
            self.user_id = response.json().get("user", {}).get("id")
        else:
            print(f"Worker Login failed for {self.username}: {response.text}")
            return

        # 2. Connect WebSocket
        self.ws_client = WebSocketClient(self.ws_host)
        try:
            self.ws_client.connect(self.token)
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=0,
                response_length=0,
            )
        except Exception as e:
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=0,
                response_length=0,
                exception=e,
            )

    def on_stop(self):
        if self.ws_client:
            self.ws_client.close()

    @task(5)
    def update_location(self):
        if self.ws_client and self.ws_client.ws:
            start_time = time.time()
            try:
                self.ws_client.send({
                    "latitude": 8.4875 + random.uniform(-0.01, 0.01),
                    "longitude": 76.9467 + random.uniform(-0.01, 0.01)
                })
                events.request.fire(
                    request_type="WebSocket",
                    name="LocationUpdate",
                    response_time=(time.time() - start_time) * 1000,
                    response_length=0,
                )
            except Exception as e:
                events.request.fire(
                    request_type="WebSocket",
                    name="LocationUpdate",
                    response_time=(time.time() - start_time) * 1000,
                    response_length=0,
                    exception=e,
                )

    @task(2)
    def list_assigned_pickups(self):
        if self.token:
            self.client.get("/api/v1/pickups/", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def check_attendance(self):
        if self.token:
            self.client.get("/api/v1/attendance/", headers={"Authorization": f"Bearer {self.token}"})
