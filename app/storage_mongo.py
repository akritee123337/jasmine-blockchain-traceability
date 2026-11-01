"""MongoDB off-chain storage combined with a Hyperledger Fabric ledger."""

from pymongo import MongoClient
from pymongo.collection import Collection
import time
from typing import Dict, Any, List
from app.blockchain import compute_hash
from app.fabric_gateway import FabricGatewayClient

class TraceabilityStore:
    def __init__(self, mongo_uri: str = "mongodb://[::1]:27017", db_name: str = "jasmine_db"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.off_chain: Collection = self.db["off_chain_records"]
        self.fabric = FabricGatewayClient()

    # -------------------- writing --------------------
    def save_off_chain_record(self, record: Dict[str, Any]) -> str:
        """Insert the FULL detailed record into MongoDB.
        
        Note: a copy is used so PyMongo's in-place _id injection does not
        mutate the caller's dict (which would silently corrupt hash checks).
        """
        result = self.off_chain.insert_one(dict(record))
        return str(result.inserted_id)

    def append_block(self, batch_id: str, event_type: str, role: str,
                      actor_id: str, actor_name: str,
                      off_chain_record: Dict[str, Any]) -> Dict[str, Any]:
        data_hash = compute_hash(off_chain_record)
        off_chain_ref = self.save_off_chain_record(off_chain_record)
        return self.fabric.record_event({
            "batch_id": batch_id,
            "event_type": event_type,
            "role": role,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "off_chain_ref": off_chain_ref,
            "data_hash": data_hash,
            "timestamp": time.time(),
        })
    

    # -------------------- reading (customers get read-only access here) --------------------
    def get_batch_history(self, batch_id: str) -> List[Dict[str, Any]]:
        return self.fabric.get_batch_events(batch_id)

    # -------------------- customer-facing full detail view --------------------
    def get_full_batch_details(self, batch_id: str) -> List[Dict[str, Any]]:
        blocks = self.get_batch_history(batch_id)
        full_details = []
        for block in blocks:
            record = self.off_chain.find_one({"_id": self._to_object_id(block["offChainRef"])})
            if record is not None:
                record = dict(record)
                record.pop("_id", None)
            full_details.append({
                "event_type": block.get("event_type") or block["eventType"],
                "role": block["role"],
                "actor_id": block.get("actor_id") or block["actorId"],
                "actor_name": block.get("actorName", "Unknown"),
                "timestamp": float(block["timestamp"]),
                "block_hash": block.get("block_hash") or block["blockHash"],
                "details": record or {},
            })
        return full_details
    

    # -------------------- verification --------------------
    def verify_batch(self, batch_id: str) -> Dict[str, Any]:
        report = self.fabric.verify_batch(batch_id)
        for block, result in zip(self.get_batch_history(batch_id), report["blocks"]):
            record = self.off_chain.find_one({"_id": self._to_object_id(block["offChainRef"])})
            if record is not None:
                record_with_id = dict(record)
                record_without_id = dict(record)
                record_without_id.pop("_id", None)
                data_ok = (
                    compute_hash(record_without_id) == block["dataHash"]
                    or compute_hash(record_with_id) == block["dataHash"]
                )
            else:
                data_ok = False

            # Re-read block_hash and chain_link validity from Fabric's report
            block_hash_ok = result.get("block_hash_valid", True)
            chain_link_ok = result.get("chain_link_valid", True)

            result["off_chain_data_valid"] = data_ok
            # Always recompute status from ALL three checks; the Fabric chaincode
            # cannot reach MongoDB so its off-chain verdict must be overridden here.
            result["status"] = "OK" if (block_hash_ok and chain_link_ok and data_ok) else "TAMPERED"

        report["valid"] = all(
            b["status"] == "OK" and b["off_chain_data_valid"]
            for b in report["blocks"]
        )
        return report

    @staticmethod
    def _to_object_id(id_str: str):
        from bson import ObjectId
        try:
            return ObjectId(id_str)
        except Exception:
            return id_str