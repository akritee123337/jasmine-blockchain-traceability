"use strict";

const http = require("http");
const fs = require("fs");
const crypto = require("crypto");
const grpc = require("@grpc/grpc-js");
const { connect, signers } = require("@hyperledger/fabric-gateway");

const port = Number(process.env.FABRIC_GATEWAY_PORT || 8081);
const channelName = process.env.FABRIC_CHANNEL || "mychannel";
const chaincodeName = process.env.FABRIC_CHAINCODE || "traceability";
const contractPath = process.env.FABRIC_CONTRACT_PATH || "/app/crypto/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/signcerts/cert.pem";
const keyPath = process.env.FABRIC_KEY_PATH || "/app/crypto/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/keystore";
const tlsCertPath = process.env.FABRIC_TLS_CERT_PATH || "/app/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt";
const peerEndpoint = process.env.FABRIC_PEER_ENDPOINT || "localhost:7051";
const peerHostAlias = process.env.FABRIC_PEER_HOST_ALIAS || "peer0.org1.example.com";

function readPrivateKey() {
  const file = fs.readdirSync(keyPath).find((name) => name.endsWith("_sk"));
  if (!file) throw new Error(`No private key found in ${keyPath}`);
  return fs.readFileSync(`${keyPath}/${file}`);
}

const identity = { mspId: process.env.FABRIC_MSP_ID || "Org1MSP", credentials: fs.readFileSync(contractPath) };
const signer = signers.newPrivateKeySigner(crypto.createPrivateKey(readPrivateKey()));
const client = new grpc.Client(peerEndpoint, grpc.credentials.createSsl(fs.readFileSync(tlsCertPath)), {
  "grpc.ssl_target_name_override": peerHostAlias,
});
const gateway = connect({ identity, signer, client });
const contract = gateway.getNetwork(channelName).getContract(chaincodeName);

function body(request) {
  return new Promise((resolve, reject) => {
    let data = "";
    request.on("data", (chunk) => { data += chunk; });
    request.on("end", () => resolve(JSON.parse(data || "{}")));
    request.on("error", reject);
  });
}

function send(response, status, value) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(value));
}

function parseFabricJson(result) {
  const text = Buffer.from(result).toString("utf8");
  return JSON.parse(text.replace(/\0/g, "").trim());
}

const server = http.createServer(async (request, response) => {
  try {
    const parts = request.url.split("/").filter(Boolean);
    if (request.method === "POST" && parts[0] === "events") {
      const input = await body(request);
      const result = await contract.submitTransaction("RecordEvent", input.batch_id, input.event_type, input.role, input.actor_id, input.actor_name, input.off_chain_ref, input.data_hash, String(input.timestamp));
      return send(response, 200, parseFabricJson(result));
    }
    if (request.method === "GET" && parts[0] === "batches" && parts[2] === "events") {
      const result = await contract.evaluateTransaction("GetBatchEvents", parts[1]);
      return send(response, 200, parseFabricJson(result));
    }
    if (request.method === "GET" && parts[0] === "batches" && parts[2] === "verify") {
      const result = await contract.evaluateTransaction("VerifyBatch", parts[1]);
      return send(response, 200, parseFabricJson(result));
    }
    send(response, 404, { error: "Not found" });
  } catch (error) {
    send(response, 500, { error: error.message });
  }
});

server.listen(port, () => console.log(`Fabric Gateway listening on http://127.0.0.1:${port}`));
