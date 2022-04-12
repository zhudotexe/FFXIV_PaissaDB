"""
Load testing spec file using Locust. Note that certain things should be set in the test environment:

- should have a world in worlds with ID 31415
- JWT secret should be set to "secret"
"""
import json
import os
import time

import jwt
from locust import HttpUser, constant, task

TEST_WORLD_ID = 31415
TEST_USER_ID = 3141529265359
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static/dummy_ward_info.json")) as f:
    DUMMY_WARD_INFO = json.load(f)


# a sweeper usually HELLOs once, then POSTs 1/sec
class Sweeper(HttpUser):
    wait_time = constant(1)
    weight = 8

    def on_start(self):
        hello = {
            "cid": TEST_USER_ID,
            "name": "Locust Test User",
            "world": "Locust Test World",
            "worldId": TEST_WORLD_ID,
        }
        self.client.post("/hello", json=hello, headers={"Authorization": f"Bearer {generate_jwt()}"})

    @task
    def post_sweep(self):
        data = DUMMY_WARD_INFO.copy()
        data["server_timestamp"] = time.time()
        self.client.post("/wardInfo", json=data, headers={"Authorization": f"Bearer {generate_jwt()}"})


# # a consumer is likely to request /worlds once, and may request world or district detail at random
# class Consumer(HttpUser):
#     wait_time = between(1, 2.5)
#     weight = 1
#
#     @task
#     def get_world_summary(self):
#         self.client.get("/worlds")
#
#     @task(10)
#     def get_world_detail(self):
#         self.client.get(f"/worlds/{TEST_WORLD_ID}")
#
#     @task(10)
#     def get_district_detail(self):
#         self.client.get(f"/worlds/{TEST_WORLD_ID}/339")  # dummy data is all in ward 339


# helpers
def generate_jwt():
    return jwt.encode(
        {"cid": TEST_USER_ID, "iss": "PaissaDB", "aud": "PaissaHouse", "iat": time.time()}, "secret", algorithm="HS256"
    )
