# Hyperledger Fabric deployment

The application now uses MongoDB only for `off_chain_records`. Event metadata and hashes are written to Hyperledger Fabric through `fabric-gateway-service`.

## Prerequisites

- Docker Desktop with Linux containers enabled
- Node.js 18+
- The Hyperledger Fabric test network from the official `fabric-samples` repository

Docker is required for the Fabric peers, orderer, certificate authority, and CouchDB. The current Windows machine did not have Docker installed, so the network cannot be started until Docker Desktop is installed.

## Deploy the chaincode

From a Fabric `test-network` checkout, start the network and create a channel:

```text
network.bat up createChannel -ca
```

Copy this directory into the test network's chaincode directory, or use its absolute path, then deploy:

```text
network.bat deployCC -ccn traceability -ccp D:\jasmine-blockchain-traceability\fabric\chaincode-javascript -ccl javascript
```

Install the Gateway bridge dependencies:

```text
cd D:\jasmine-blockchain-traceability\fabric-gateway-service
npm install
```

Start the Gateway bridge with certificate paths from the Fabric test network:

```text
set FABRIC_GATEWAY_PORT=8081
set FABRIC_CHANNEL=mychannel
set FABRIC_CHAINCODE=traceability
set FABRIC_CONTRACT_PATH=C:\path\to\fabric-samples\test-network\organizations\peerOrganizations\org1.example.com\users\User1@org1.example.com\msp\signcerts\cert.pem
set FABRIC_KEY_PATH=C:\path\to\fabric-samples\test-network\organizations\peerOrganizations\org1.example.com\users\User1@org1.example.com\msp\keystore
set FABRIC_TLS_CERT_PATH=C:\path\to\fabric-samples\test-network\organizations\peerOrganizations\org1.example.com\peers\peer0.org1.example.com\tls\ca.crt
set FABRIC_PEER_ENDPOINT=localhost:7051
set FABRIC_PEER_HOST_ALIAS=peer0.org1.example.com
node server.js
```

Start the FastAPI application in another terminal:

```text
cd D:\jasmine-blockchain-traceability
set FABRIC_GATEWAY_URL=http://127.0.0.1:8081
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

After this, `python add_events.py` writes the detailed record to MongoDB and submits the event log and its hash to Fabric. The QR page reads the event log from Fabric and joins it with MongoDB details using `off_chain_ref`.

## What is on Fabric

Each Fabric event contains:

- batch ID and event type
- actor ID, actor name, and role
- timestamp
- MongoDB off-chain reference
- SHA-256 hash of the detailed record
- previous event hash
- current block hash

No `blockchain_ledger` MongoDB collection is used by the new application path.
