"""
test_customer_view.py
Tests customer_view.py rendering logic standalone (no MongoDB, no
FastAPI needed). Confirms the HTML page builds correctly from sample
timeline data before you wire it into the live API.

Run: python3 test_customer_view.py
Then open the generated preview_batch_page.html in your browser.
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.customer_view import render_batch_page
import time

sample_timeline = [
    {
        "event_type": "CULTIVATION", "role": "farmer", "actor_id": "farmer_102",
        "timestamp": time.time() - 6000000, "block_hash": "367fcb1781e0abcd1234",
        "details": {"farm_id": "FARM-12", "plot": "A3", "practice": "organic"},
    },
    {
        "event_type": "DISEASE_DETECTION", "role": "ai_system", "actor_id": "ai_engine",
        "timestamp": time.time() - 5000000, "block_hash": "3d7cc9fee638ef561234",
        "details": {"disease": "Leaf Spot", "confidence": 0.94, "severity": "Medium"},
    },
    {
        "event_type": "TREATMENT", "role": "expert", "actor_id": "expert_09",
        "timestamp": time.time() - 4000000, "block_hash": "471ad1d30a4c99881234",
        "details": {"treatment": "Neem oil spray", "notes": "2 rounds, 5 days apart"},
    },
    {
        "event_type": "HARVEST", "role": "farmer", "actor_id": "farmer_102",
        "timestamp": time.time() - 3000000, "block_hash": "68274e2428ab77661234",
        "details": {"quantity_kg": 42.5, "grade": "A"},
    },
    {
        "event_type": "COLLECTION", "role": "distributor", "actor_id": "dist_44",
        "timestamp": time.time() - 2000000, "block_hash": "c5c29231116399221234",
        "details": {"vehicle": "TN-09-AZ-1234"},
    },
    {
        "event_type": "TRANSPORTATION", "role": "distributor", "actor_id": "dist_44",
        "timestamp": time.time() - 1000000, "block_hash": "9953c22a2d5988771234",
        "details": {"route": "Farm -> Warehouse -> Retail", "temp_c": 18.2},
    },
    {
        "event_type": "SALE", "role": "seller", "actor_id": "seller_08",
        "timestamp": time.time() - 100000, "block_hash": "77a0d6ef36e9aabb1234",
        "details": {"price_per_kg": 320, "buyer": "retail_shop_19"},
    },
]

html = render_batch_page("JAS-2026-001", sample_timeline, is_valid=True)

with open("preview_batch_page.html", "w") as f:
    f.write(html)

print("Preview generated: preview_batch_page.html")
print("Open this file in your browser to see exactly what a customer")
print("sees after scanning the QR code.")