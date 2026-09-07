"""
blockchain.py
Core blockchain logic for the Jasmine Traceability System.

Design:
- Each Batch (e.g. JAS-2026-001) has its own hash-chained ledger.
- Each Block represents ONE supply-chain event (cultivation, disease
  detection, treatment, harvest, collection, transport, sale).
- A block stores only compact metadata + a SHA-256 hash of the full
  off-chain record (which lives in MongoDB). The heavy data (images,
  AI report text, etc.) is NEVER stored on-chain.
- Blocks are linked via previous_hash, exactly like a real blockchain.
  Changing ANY field in a past block (or its referenced off-chain
  record) breaks the chain -> detectable via verify_chain().

This module has ZERO external dependencies (only Python stdlib), so it
can be unit-tested / demoed instantly without MongoDB, then plugged
into the FastAPI + MongoDB backend via storage_mongo.py.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------
# Roles allowed to write each event type (Role-Based Access Control)
# ---------------------------------------------------------------------
EVENT_ROLE_MAP = {
    "CULTIVATION":        ["farmer"],
    "DISEASE_DETECTION":  ["farmer", "ai_system"],
    "TREATMENT":          ["farmer", "expert"],
    "HARVEST":            ["farmer"],
    "COLLECTION":         ["distributor"],
    "TRANSPORTATION":     ["distributor"],
    "SALE":                ["seller"],
}

READ_ONLY_ROLES = ["customer"]


class RoleAccessError(Exception):
    """Raised when a role tries to record an event it is not permitted to."""
    pass


def compute_hash(*parts: Any) -> str:
    """SHA-256 hash of the concatenated, JSON-serialized parts."""
    payload = json.dumps(parts, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

@dataclass
class Block:
    index: int
    batch_id: str
    event_type: str
    role: str
    actor_id: str
    actor_name: str            # NEW — human-readable name
    timestamp: float
    off_chain_ref: str
    data_hash: str
    previous_hash: str
    block_hash: str = field(default="")

    def compute_block_hash(self) -> str:
        return compute_hash(
            self.index,
            self.batch_id,
            self.event_type,
            self.role,
            self.actor_id,
            self.actor_name,        # NEW — included in hash too
            self.timestamp,
            self.off_chain_ref,
            self.data_hash,
            self.previous_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BatchBlockchain:
    """
    A hash-chained ledger for a single jasmine harvest batch.
    In production each batch's chain is persisted in a MongoDB
    collection (see storage_mongo.py); here it's kept as a Python
    list so the core logic can be demoed/tested with zero setup.
    """

    GENESIS_PREV_HASH = "0" * 64

    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.chain: List[Block] = []

    # -------------------- writing new events --------------------
    def add_event(
        self,
        event_type: str,
        role: str,
        actor_id: str,
        off_chain_record: Dict[str, Any],
        off_chain_ref: str,
        actor_name: str = "Unknown",
    ) -> Block:
        allowed_roles = EVENT_ROLE_MAP.get(event_type)
        if allowed_roles is None:
            raise ValueError(f"Unknown event type: {event_type}")
        if role not in allowed_roles:
            raise RoleAccessError(
                f"Role '{role}' is not permitted to record '{event_type}' "
                f"events. Allowed roles: {allowed_roles}"
            )

        previous_hash = self.chain[-1].block_hash if self.chain else self.GENESIS_PREV_HASH
        data_hash = compute_hash(off_chain_record)

        block = Block(
            index=len(self.chain),
            batch_id=self.batch_id,
            event_type=event_type,
            role=role,
            actor_id=actor_id,
            actor_name=actor_name,
            timestamp=time.time(),
            off_chain_ref=off_chain_ref,
            data_hash=data_hash,
            previous_hash=previous_hash,
        )
        block.block_hash = block.compute_block_hash()
        self.chain.append(block)
        return block
    

    # -------------------- reading (any role, incl. customer) --------------------
    def get_history(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]

    # -------------------- integrity verification --------------------
    def verify_chain(self, current_off_chain_records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Re-computes hashes from CURRENT off-chain data (as it exists
        right now in MongoDB) and checks them against what's stored
        on-chain. This is how tampering is detected.

        `current_off_chain_records` maps off_chain_ref -> the record
        AS IT CURRENTLY EXISTS in MongoDB (which may have been altered
        after the block was written).

        Returns a report: overall validity + per-block detail.
        """
        report = {"batch_id": self.batch_id, "valid": True, "blocks": []}

        for i, block in enumerate(self.chain):
            block_result = {"index": block.index, "event_type": block.event_type}

            # 1) Check this block's own hash is internally consistent
            recomputed_block_hash = block.compute_block_hash()
            block_hash_ok = (recomputed_block_hash == block.block_hash)

            # 2) Check the link to the previous block
            expected_prev = self.chain[i - 1].block_hash if i > 0 else self.GENESIS_PREV_HASH
            link_ok = (block.previous_hash == expected_prev)

            # 3) Check the off-chain data hasn't been silently altered
            current_record = current_off_chain_records.get(block.off_chain_ref)
            current_data_hash = compute_hash(current_record) if current_record is not None else None
            data_ok = (current_data_hash == block.data_hash)

            block_result.update({
                "block_hash_valid": block_hash_ok,
                "chain_link_valid": link_ok,
                "off_chain_data_valid": data_ok,
                "status": "OK" if (block_hash_ok and link_ok and data_ok) else "TAMPERED",
            })
            report["blocks"].append(block_result)

            if not (block_hash_ok and link_ok and data_ok):
                report["valid"] = False

        return report