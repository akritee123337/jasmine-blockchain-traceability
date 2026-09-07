"use strict";

const { Contract } = require("fabric-contract-api");
const crypto = require("crypto");

class TraceabilityContract extends Contract {
  static eventKey(batchId, index) {
    return `event:${batchId}:${String(index).padStart(10, "0")}`;
  }

  static batchKey(batchId) {
    return `batch:${batchId}`;
  }

  static hash(fields) {
    return crypto.createHash("sha256").update(JSON.stringify(fields)).digest("hex");
  }

  async RecordEvent(ctx, batchId, eventType, role, actorId, actorName, offChainRef, dataHash, timestamp) {
    const batchState = await ctx.stub.getState(TraceabilityContract.batchKey(batchId));
    const index = batchState.length ? JSON.parse(batchState.toString()).nextIndex : 0;
    const previousHash = index === 0
      ? "0".repeat(64)
      : JSON.parse((await ctx.stub.getState(TraceabilityContract.eventKey(batchId, index - 1))).toString()).blockHash;

    const block = {
      index,
      batchId,
      eventType,
      role,
      actorId,
      actorName,
      timestamp,
      offChainRef,
      dataHash,
      previousHash,
    };
    block.blockHash = TraceabilityContract.hash([
      block.index, block.batchId, block.eventType, block.role, block.actorId,
      block.actorName, block.timestamp, block.offChainRef, block.dataHash,
      block.previousHash,
    ]);

    await ctx.stub.putState(TraceabilityContract.eventKey(batchId, index), Buffer.from(JSON.stringify(block)));
    await ctx.stub.putState(TraceabilityContract.batchKey(batchId), Buffer.from(JSON.stringify({ nextIndex: index + 1 })));
    return JSON.stringify(block);
  }

  async GetBatchEvents(ctx, batchId) {
    const iterator = await ctx.stub.getStateByRange(`event:${batchId}:`, `event:${batchId};`);
    const events = [];
    for (;;) {
      const result = await iterator.next();
      if (result.value && result.value.value) events.push(JSON.parse(result.value.value.toString()));
      if (result.done) break;
    }
    await iterator.close();
    return JSON.stringify(events);
  }

  async VerifyBatch(ctx, batchId) {
    const events = JSON.parse(await this.GetBatchEvents(ctx, batchId));
    const blocks = events.map((block, index) => {
      const expectedPrevious = index === 0 ? "0".repeat(64) : events[index - 1].blockHash;
      const recomputed = TraceabilityContract.hash([
        block.index, block.batchId, block.eventType, block.role, block.actorId,
        block.actorName, block.timestamp, block.offChainRef, block.dataHash,
        block.previousHash,
      ]);
      const blockHashValid = recomputed === block.blockHash;
      const chainLinkValid = block.previousHash === expectedPrevious;
      return {
        index: block.index,
        event_type: block.eventType,
        off_chain_ref: block.offChainRef,
        data_hash: block.dataHash,
        block_hash_valid: blockHashValid,
        chain_link_valid: chainLinkValid,
        status: blockHashValid && chainLinkValid ? "OK" : "TAMPERED",
      };
    });
    return JSON.stringify({ batch_id: batchId, valid: blocks.every((block) => block.status === "OK"), blocks });
  }
}

module.exports = TraceabilityContract;
