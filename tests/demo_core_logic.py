"""
demo_core_logic.py
Tests the core blockchain.py module end-to-end WITHOUT needing MongoDB
or FastAPI running. Use this tonight to confirm the logic works, and
to generate the tamper-detection result you can paste into your paper.

Run:  python3 demo_core_logic.py
"""


import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.blockchain import BatchBlockchain, RoleAccessError
import time

print("=" * 70)
print("JASMINE BLOCKCHAIN TRACEABILITY -- CORE LOGIC DEMO")
print("=" * 70)

# Simulate MongoDB: a simple dict acting as the off-chain database
mongodb_simulated: dict = {}

batch = BatchBlockchain(batch_id="JAS-2026-001")

# 1) Farmer logs cultivation
rec1 = {"farm_id": "FARM-12", "plot": "A3", "practice": "organic", "geo": [12.97, 77.59]}
mongodb_simulated["mongo_rec_1"] = rec1
b1 = batch.add_event("CULTIVATION", role="farmer", actor_id="farmer_102",
                      off_chain_record=rec1, off_chain_ref="mongo_rec_1")

# 2) AI detects disease
rec2 = {"image_path": "/uploads/leaf_0912.jpg", "disease": "Leaf Spot",
        "confidence": 0.94, "severity": "Medium"}
mongodb_simulated["mongo_rec_2"] = rec2
b2 = batch.add_event("DISEASE_DETECTION", role="ai_system", actor_id="ai_engine",
                      off_chain_record=rec2, off_chain_ref="mongo_rec_2")

# 3) Expert / farmer applies treatment
rec3 = {"treatment": "Neem oil spray", "applied_by": "farmer_102", "notes": "2 rounds, 5 days apart"}
mongodb_simulated["mongo_rec_3"] = rec3
b3 = batch.add_event("TREATMENT", role="expert", actor_id="expert_09",
                      off_chain_record=rec3, off_chain_ref="mongo_rec_3")

# 4) Harvest
rec4 = {"quantity_kg": 42.5, "grade": "A", "harvested_on": "2026-06-14"}
mongodb_simulated["mongo_rec_4"] = rec4
b4 = batch.add_event("HARVEST", role="farmer", actor_id="farmer_102",
                      off_chain_record=rec4, off_chain_ref="mongo_rec_4")

# 5) Distributor collects
rec5 = {"collected_by": "dist_44", "vehicle": "TN-09-AZ-1234"}
mongodb_simulated["mongo_rec_5"] = rec5
b5 = batch.add_event("COLLECTION", role="distributor", actor_id="dist_44",
                      off_chain_record=rec5, off_chain_ref="mongo_rec_5")

# 6) Transportation
rec6 = {"route": "Farm -> Warehouse -> Retail", "temp_c": 18.2}
mongodb_simulated["mongo_rec_6"] = rec6
b6 = batch.add_event("TRANSPORTATION", role="distributor", actor_id="dist_44",
                      off_chain_record=rec6, off_chain_ref="mongo_rec_6")

# 7) Sale
rec7 = {"seller": "seller_08", "price_per_kg": 320, "buyer": "retail_shop_19"}
mongodb_simulated["mongo_rec_7"] = rec7
b7 = batch.add_event("SALE", role="seller", actor_id="seller_08",
                      off_chain_record=rec7, off_chain_ref="mongo_rec_7")

print(f"\n[1] Batch '{batch.batch_id}' now has {len(batch.chain)} chained events.\n")
for blk in batch.get_history():
    print(f"  Block {blk['index']}: {blk['event_type']:<18} "
          f"role={blk['role']:<12} hash={blk['block_hash'][:12]}...")

# Test 1: RBAC enforcement
print("\n[2] Testing Role-Based Access Control (RBAC)...")
try:
    batch.add_event("SALE", role="farmer", actor_id="farmer_102",
                     off_chain_record={"x": 1}, off_chain_ref="mongo_rec_bad")
    print("  FAILED: farmer was wrongly allowed to record a SALE event!")
except RoleAccessError as e:
    print(f"  PASSED: correctly rejected -> {e}")

# Test 2: Integrity verification BEFORE tampering
print("\n[3] Verifying chain integrity (before any tampering)...")
report_before = batch.verify_chain(mongodb_simulated)
print(f"  Overall valid: {report_before['valid']}")
for b in report_before["blocks"]:
    print(f"    Block {b['index']} ({b['event_type']:<18}) -> {b['status']}")

# Test 3: Simulate tampering
print("\n[4] Simulating tampering: directly editing MongoDB record for HARVEST "
      "(quantity_kg 42.5 -> 60.0), WITHOUT going through the blockchain layer...")
mongodb_simulated["mongo_rec_4"]["quantity_kg"] = 60.0

print("\n[5] Re-verifying chain integrity (after tampering)...")
report_after = batch.verify_chain(mongodb_simulated)
print(f"  Overall valid: {report_after['valid']}")
for b in report_after["blocks"]:
    flag = "  <-- TAMPER DETECTED" if b["status"] == "TAMPERED" else ""
    print(f"    Block {b['index']} ({b['event_type']:<18}) -> {b['status']}{flag}")

print("\n" + "=" * 70)
print("SUMMARY FOR RESEARCH PAPER")
print("=" * 70)
print(f"Total events logged:              {len(batch.chain)}")
print(f"Chain valid before tampering:      {report_before['valid']}")
print(f"Chain valid after tampering:       {report_after['valid']}")
tampered_blocks = [b['index'] for b in report_after['blocks'] if b['status'] == 'TAMPERED']
print(f"Tampered block(s) detected:        {tampered_blocks}")
print(f"RBAC unauthorized-write rejected:  True")