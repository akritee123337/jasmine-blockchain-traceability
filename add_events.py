"""
add_events.py
Adds real events to MongoDB via the blockchain logic -- no Swagger UI.
Run: py add_events.py
"""

import os

from app.storage_mongo import TraceabilityStore
from app.qr_generator import generate_qr_for_batch

store = TraceabilityStore(mongo_uri="mongodb://localhost:27017", db_name="jasmine_db")

batch_id = os.getenv("BATCH_ID", "JAS-2026-003")

# (event_type, role, actor_id, actor_name, data)
events = [
    ("CULTIVATION", "farmer", "farmer_102", "Ramesh Kumar",
     {"farm_id": "FARM-12", "plot": "A3", "practice": "organic"}),

    ("DISEASE_DETECTION", "ai_system", "ai_engine", "AI Diagnosis System",
     {"disease": "Leaf Spot", "confidence": 0.94, "severity": "Medium"}),

    ("TREATMENT", "expert", "expert_09", "Dr. Anjali Sharma",
     {"treatment": "Neem oil spray", "notes": "2 rounds, 5 days apart"}),

    ("HARVEST", "farmer", "farmer_102", "Ramesh Kumar",
     {"quantity_kg": 42.5, "grade": "A"}),

    ("COLLECTION", "distributor", "dist_44", "Suresh Logistics Pvt Ltd",
     {"vehicle": "TN-09-AZ-1234"}),

    ("TRANSPORTATION", "distributor", "dist_44", "Suresh Logistics Pvt Ltd",
     {"route": "Farm -> Warehouse -> Retail", "temp_c": 18.2}),

    ("SALE", "seller", "seller_08", "Green Leaf Retail Store",
     {"price_per_kg": 320, "buyer": "retail_shop_19"}),
]

existing_events = store.get_batch_history(batch_id)
start_index = len(existing_events)
if existing_events:
    if start_index >= len(events):
        print(f"Batch '{batch_id}' already contains {len(existing_events)} events.")
        print("No duplicate events were added.")
    else:
        print(f"Batch '{batch_id}' already contains {start_index} events.")
        print(f"Resuming with {len(events) - start_index} remaining events...\n")
else:
    print(f"Adding {len(events)} events to batch '{batch_id}'...\n")

for event_type, role, actor_id, actor_name, data in events[start_index:]:
    block = store.append_block(
        batch_id=batch_id,
        event_type=event_type,
        role=role,
        actor_id=actor_id,
        actor_name=actor_name,
        off_chain_record=data,
    )
    block_hash = block.get("block_hash", block.get("blockHash", ""))
    print(f"  Added: {event_type:<18} by {actor_name:<25} "
          f"(block #{block['index']}, hash={block_hash[:12]}...)")

print("\nDone. View the live customer page at:")
base_url = os.getenv("TRACEABILITY_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
qr_path = generate_qr_for_batch(
    batch_id,
    base_url=base_url,
    output_path=f"qr_{batch_id}.png",
)
print(f"Customer page: {base_url}/track/{batch_id}")
print(f"Scan this QR image: {qr_path}")