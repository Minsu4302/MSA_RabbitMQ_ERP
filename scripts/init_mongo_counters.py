# Initialize MongoDB counters for approval_request_id to current max requestId
# Usage: set env MONGO_URI and DB_NAME, then run inside cluster/pod or from machine with access
# Example: python scripts/init_mongo_counters.py

import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "erp")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

approvals = db["approvals"]
counters = db["counters"]

max_doc = approvals.find_one(sort=[("requestId", -1)])
max_id = int(max_doc["requestId"]) if max_doc and "requestId" in max_doc else 0

counters.update_one({"_id": "approval_request_id"}, {"$set": {"seq": max_id}}, upsert=True)

print(f"Initialized counters.approval_request_id.seq to {max_id}")
