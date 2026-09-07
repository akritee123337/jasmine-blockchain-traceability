"""
benchmark.py
Measures real latency of the core blockchain operations, with ZERO
external dependencies. Use these numbers directly in your paper's
results/evaluation section.

Run: python3 benchmark.py
"""


import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.blockchain import BatchBlockchain
import time
import statistics
N_RUNS = 200

batch = BatchBlockchain(batch_id="JAS-2026-BENCH")
mongodb_simulated = {}

event_sequence = [
    ("CULTIVATION", "farmer", "farmer_1"),
    ("DISEASE_DETECTION", "ai_system", "ai_engine"),
    ("TREATMENT", "expert", "expert_1"),
    ("HARVEST", "farmer", "farmer_1"),
    ("COLLECTION", "distributor", "dist_1"),
    ("TRANSPORTATION", "distributor", "dist_1"),
    ("SALE", "seller", "seller_1"),
]

# Benchmark 1: block write latency
write_times = []
for i in range(N_RUNS):
    event_type, role, actor = event_sequence[i % len(event_sequence)]
    record = {"sample_field": i, "note": "benchmark record"}
    ref = f"rec_{i}"
    mongodb_simulated[ref] = record

    start = time.perf_counter()
    batch.add_event(event_type, role=role, actor_id=actor,
                     off_chain_record=record, off_chain_ref=ref)
    end = time.perf_counter()
    write_times.append((end - start) * 1000)

# Benchmark 2: full chain verification latency
verify_times = []
for _ in range(30):
    start = time.perf_counter()
    batch.verify_chain(mongodb_simulated)
    end = time.perf_counter()
    verify_times.append((end - start) * 1000)

print("=" * 60)
print("PERFORMANCE BENCHMARK — Jasmine Blockchain Traceability")
print("=" * 60)
print(f"Chain length at time of verification: {len(batch.chain)} blocks\n")

print(f"Block write (append_event) latency over {N_RUNS} runs:")
print(f"  Mean:   {statistics.mean(write_times):.4f} ms")
print(f"  Median: {statistics.median(write_times):.4f} ms")
print(f"  Min:    {min(write_times):.4f} ms")
print(f"  Max:    {max(write_times):.4f} ms")

print(f"\nFull chain verification latency over 30 runs ({len(batch.chain)}-block chain):")
print(f"  Mean:   {statistics.mean(verify_times):.4f} ms")
print(f"  Median: {statistics.median(verify_times):.4f} ms")
print(f"  Min:    {min(verify_times):.4f} ms")
print(f"  Max:    {max(verify_times):.4f} ms")

print("\n" + "=" * 60)
print("TABLE FOR RESEARCH PAPER")
print("=" * 60)
print(f"{'Operation':<30}{'Mean (ms)':<15}{'Min (ms)':<15}{'Max (ms)'}")
print(f"{'Block write (per event)':<30}{statistics.mean(write_times):<15.4f}"
      f"{min(write_times):<15.4f}{max(write_times):.4f}")
print(f"{'Chain verification (' + str(len(batch.chain)) + ' blocks)':<30}"
      f"{statistics.mean(verify_times):<15.4f}{min(verify_times):<15.4f}{max(verify_times):.4f}")