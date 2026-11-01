
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const grpc = require("@grpc/grpc-js");
const { connect, signers } = require("@hyperledger/fabric-gateway");

const port = Number(process.env.FABRIC_GATEWAY_PORT || 8081);
const channelName = process.env.FABRIC_CHANNEL || "mychannel";
const chaincodeName = process.env.FABRIC_CHAINCODE || "traceability";

// Fabric network certificate directory
const cryptoPath = path.resolve(
  __dirname,
  "../fabric-samples/test-network/organizations/peerOrganizations/org1.example.com"
);

// User identity certificate
const contractPath =
  process.env.FABRIC_CONTRACT_PATH ||
  path.join(
    cryptoPath,
    "users",
    "User1@org1.example.com",
    "msp",
    "signcerts",
    "User1@org1.example.com-cert.pem"
  );

// User's private key directory
const keyPath =
  process.env.FABRIC_KEY_PATH ||
  path.join(
    cryptoPath,
    "users",
    "User1@org1.example.com",
    "msp",
    "keystore"
  );

// Peer TLS certificate
const tlsCertPath =
  process.env.FABRIC_TLS_CERT_PATH ||
  path.join(
    cryptoPath,
    "peers",
    "peer0.org1.example.com",
    "tls",
    "ca.crt"
  );

const peerEndpoint =
  process.env.FABRIC_PEER_ENDPOINT || "localhost:7051";

const peerHostAlias =
  process.env.FABRIC_PEER_HOST_ALIAS || "peer0.org1.example.com";

// Read the user's private key
function readPrivateKey() {
  if (!fs.existsSync(keyPath)) {
    throw new Error(`Private key directory not found: ${keyPath}`);
  }

  const file = fs
    .readdirSync(keyPath)
    .find((name) => name.endsWith("_sk"));

  if (!file) {
    throw new Error(`No private key found in ${keyPath}`);
  }

  return fs.readFileSync(path.join(keyPath, file));
}

// Validate required certificate files
for (const [name, filePath] of [
  ["Identity certificate", contractPath],
  ["TLS certificate", tlsCertPath],
]) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`${name} not found: ${filePath}`);
  }
}

// Create Fabric identity and signer
const identity = {
  mspId: process.env.FABRIC_MSP_ID || "Org1MSP",
  credentials: fs.readFileSync(contractPath),
};

const signer = signers.newPrivateKeySigner(
  crypto.createPrivateKey(readPrivateKey())
);

// Connect to the Fabric peer
const client = new grpc.Client(
  peerEndpoint,
  grpc.credentials.createSsl(fs.readFileSync(tlsCertPath)),
  {
    "grpc.ssl_target_name_override": peerHostAlias,
  }
);

const gateway = connect({
  identity,
  signer,
  client,
});

const contract = gateway
  .getNetwork(channelName)
  .getContract(chaincodeName);

// Read JSON request bodies
function body(request) {
  return new Promise((resolve, reject) => {
    let data = "";

    request.on("data", (chunk) => {
      data += chunk;
    });

    request.on("end", () => {
      try {
        resolve(JSON.parse(data || "{}"));
      } catch (error) {
        reject(error);
      }
    });

    request.on("error", reject);
  });
}

// Send JSON responses
function send(response, status, value) {
  response.writeHead(status, {
    "Content-Type": "application/json",
  });

  response.end(JSON.stringify(value));
}

// Parse JSON returned by chaincode
function parseFabricJson(result) {
  const text = Buffer.from(result)
    .toString("utf8")
    .replace(/\0/g, "")
    .trim();

  return JSON.parse(text);
}

// HTTP API routes
const server = http.createServer(async (request, response) => {
  try {
    const parts = request.url.split("?")[0].split("/").filter(Boolean);

    // Record a traceability event
    if (request.method === "POST" && parts[0] === "events") {
      const input = await body(request);

      const result = await contract.submitTransaction(
        "RecordEvent",
        input.batch_id,
        input.event_type,
        input.role,
        input.actor_id,
        input.actor_name,
        input.off_chain_ref,
        input.data_hash,
        String(input.timestamp)
      );

      return send(response, 200, parseFabricJson(result));
    }

    // Retrieve events for a batch
    if (
      request.method === "GET" &&
      parts[0] === "batches" &&
      parts[2] === "events"
    ) {
      const result = await contract.evaluateTransaction(
        "GetBatchEvents",
        parts[1]
      );

      return send(response, 200, parseFabricJson(result));
    }

    // Verify a batch
    if (
      request.method === "GET" &&
      parts[0] === "batches" &&
      parts[2] === "verify"
    ) {
      const result = await contract.evaluateTransaction(
        "VerifyBatch",
        parts[1]
      );

      return send(response, 200, parseFabricJson(result));
    }

    return send(response, 404, { error: "Not found" });
  } catch (error) {
    console.error("Fabric Gateway request error:", error.message);

    return send(response, 500, {
      error: error.message,
    });
  }
});

server.listen(port, () => {
  console.log(`Fabric Gateway listening on http://127.0.0.1:${port}`);
});