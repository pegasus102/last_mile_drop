# Last-Mile Whisper

**Zero-friction, geo-fenced voice landmarks for hyper-local Indian logistics.**

---

## 🧩 Problem Statement

Millions of addresses across Indian tier-1/2/3 cities lack structured grid references (e.g., *"Opposite Sharma Sweets, behind Peepal tree, red gate"*). This forces delivery associates to stop, call masked customer numbers, and wait for verbal directions — adding 2–3 minutes per delivery, burning fuel, increasing telecom costs, and interrupting customers during work or meetings.

**Last-Mile Whisper** eliminates this friction by converting a short customer voice note into structured, privacy-shielded visual landmark tags, and replaces unnecessary phone calls with a smart digital doorbell — unlocked only when the driver is physically near the delivery location.

---

## 🏗️ Architecture Overview

```
[ Customer Voice Note ]
        │
        ▼
Amazon S3 Bucket ──► AWS Lambda Orchestrator
        │
        ├──────────────┬───────────────┐
        ▼              ▼               
Amazon Bedrock    Cedar Policy Engine
(Claude 3 Haiku)  (Checks Driver Distance)
(JSON Landmark          │
 Extraction)             │
        └──────────────┴───────────────┘
                │
                ▼
      Amazon DynamoDB
      (Deliveries State Table)
                │
                ▼
      Driver HUD (Web)
      (3 Visual Tags + Digital Doorbell State)
```

**Flow Summary:**
1. Customer records a 10-second voice note at checkout, uploaded to **Amazon S3**.
2. An **AWS Lambda Orchestrator** (triggered via EventBridge/S3 event) coordinates processing.
3. **Amazon Bedrock (Claude 3 Haiku)** extracts a clean JSON payload (`landmark`, `turn_instruction`, `door_color`) from the raw transcript.
4. The **Cedar Policy Engine** enforces geo-fenced access control — landmark tags unlock at 500m, and the Digital Doorbell unlocks at 20m from the delivery pin.
5. Processed state is persisted in **Amazon DynamoDB** (`Deliveries` table).
6. The **Driver HUD** renders high-contrast visual tags and manages the Digital Doorbell state machine (chime alerts, ping retries, fallback masked calling).

---

## 🔐 Core Features

- **Geo-Fenced Cedar Shield** — Dual-stage authorization (500m for landmark tags, 20m for doorbell activation).
- **AI Landmark Extraction** — Converts messy regional speech into structured JSON via Claude 3 Haiku.
- **Driver-First HUD** — Dark-mode, glanceable interface built for two-wheeler delivery riders.
- **Status-Aware Digital Doorbell** — State machine handling 30-second chime alerts, notification opt-out detection, 2-ping retry caps, and fallback masked calling.

---

## 🛠️ Local Tech Stack

| Layer | Technology |
|---|---|
| Cloud Emulation | **LocalStack** (S3, DynamoDB, EventBridge) |
| Infrastructure | **AWS SAM CLI** |
| AI / ML | **Amazon Bedrock** — `anthropic.claude-3-haiku-20240307-v1:0` via `boto3` |
| Authorization | **Cedar Policy Engine** (`cedar-policy-cli`) |
| Backend | **Python 3.11**, `boto3` |
| Database | **Amazon DynamoDB** (`Deliveries` table) |
| Frontend | **HTML5**, **CSS3** (Dark Slate Theme), Vanilla JavaScript |

---

## 🚦 Digital Doorbell State Machine

| Condition | Behavior |
|---|---|
| Distance > 20m | Doorbell `DISABLED` — "Locked by Cedar Policy" |
| Notifications Disabled | HUD skips doorbell → `[ 📞 Direct Call Required ]` |
| Distance ≤ 20m & First Tap | Sends 30s chime → state `RINGING_30S` |
| Timeout / 2nd Tap | Button → `[ 🔄 Ping Once More ]` |
| Max Pings Exceeded (2) | State `MAX_PINGS_EXCEEDED` → unlocks `[ 📞 Masked Direct Call ]` |

---

## 🚀 Getting Started

```bash
# Start LocalStack
localstack start -d

# Deploy with SAM
sam build
sam local start-api

# Validate Cedar policies
cedar validate --policies policies/ --schema schema.cedarschema
```

---

*Built for the AWS / WeMakeDevs "First Commit" Hackathon.*