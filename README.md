# Last-Mile Whisper

**Zero-Friction, Geo-Fenced Voice Landmarks & Multimodal TTS Delivery Infrastructure for Hyper-Local Logistics in India.**

---

## 🧩 Problem Statement

Millions of addresses across Indian tier-1/2/3 cities lack structured grid references — *"Opposite Sharma Sweets, behind Peepal tree, red gate"* is often the most precise directions a customer can give. This forces delivery associates to stop mid-route, call masked customer numbers, and wait for verbal directions, adding **2–3 minutes per delivery**, burning fuel across thousands of daily stops, and interrupting customers during work, meetings, or family time.

**Last-Mile Whisper** eliminates this friction end-to-end: a short customer voice note is converted into structured, privacy-shielded visual landmark tags *and* a natural-language spoken route summary, while unnecessary phone calls are replaced by a smart digital doorbell that only unlocks when the driver is physically near the delivery location.

---

## 🏗️ Complete End-to-End Architecture

The system evolved from a Bedrock-only local prototype into a hybrid pipeline that pairs Google's multimodal Gemini models with AWS's delivery, authorization, and voice infrastructure.

```
[ Customer Voice Note (.m4a) ]
            │
            ▼
    Amazon S3 Bucket  ──────────────► AWS Lambda Orchestrator
                                              │
              ┌───────────────────────────────┼────────────────────────────┐
              ▼                                ▼                            ▼
   Google Gemini Multimodal          Cedar Policy Engine            Amazon Polly
   (gemini-3.1-flash-lite)          (Driver Distance Checks)        Neural TTS
   via google-genai SDK              500m → Landmarks               VoiceId: "Kajal"
   Raw audio → structured JSON       20m  → Digital Doorbell        Engine: neural
   (waypoints, destination,                │                        Bilingual EN/HI
    door details, driver_audio_script)     │                        readout of
              │                            │                        driver_audio_script
              └──────────────┬─────────────┘                            │
                              ▼                                         │
                    Amazon DynamoDB                                     │
                    (Deliveries State Table)                            │
                              │                                         │
                              └───────────────────┬─────────────────────┘
                                                   ▼
                                     Driver HUD & Admin Simulator (Web)
                                     — 3 visual landmark tags
                                     — 🔊 "Listen to Route" (Polly playback)
                                     — Digital Doorbell state machine
                                     — Admin raw audio preview player
```

### Flow Summary

1. **Capture** — The customer records a short voice note (`.m4a`) at checkout, uploaded directly to **Amazon S3**.
2. **Trigger** — An **AWS Lambda Orchestrator** fires automatically on the S3 `ObjectCreated` event.
3. **Multimodal Ingestion** — The Lambda calls **Google Gemini (`gemini-3.1-flash-lite`)** via the `google-genai` SDK, passing the *raw audio file directly* (no intermediate speech-to-text/translation hop). This avoids compounding transcription errors on code-mixed Hinglish audio and returns a single structured JSON payload containing waypoints, destination details, door instructions, do-not-call flags, and a chronological `driver_audio_script`.
4. **Authorization** — The **Cedar Policy Engine** evaluates driver-to-pin distance on every HUD refresh, gating two independent capabilities: landmark visibility at **500m** and Digital Doorbell activation at **20m**.
5. **Persistence** — The structured payload and delivery state are written to **Amazon DynamoDB** (`Deliveries` table), the single source of truth for the HUD.
6. **Voice Synthesis** — On driver request, **Amazon Polly** (Neural engine, `VoiceId: Kajal`) synthesizes the AI-generated `driver_audio_script` into natural, bilingual Indian English/Hindi audio, returned to the frontend as base64-encoded MP3 for hands-free, privacy-compliant playback.
7. **Presentation** — The **Driver HUD** renders high-contrast visual tags, a "Listen to Route" TTS control, and the Digital Doorbell state machine (chime alerts, ping retries, fallback masked calling). A parallel **Admin Simulator** panel lets judges/testers swap between seeded packages and preview the raw uploaded audio inline.

---

## 🔐 Core Features

| Feature | Description |
|---|---|
| **Raw Multimodal Audio Ingestion** | Customer `.m4a` voice notes are sent directly to **Google Gemini (AI Studio)** for parsing — no separate ASR/translation step, preserving accuracy on code-mixed Hinglish speech. |
| **AI-Generated `driver_audio_script`** | Alongside structured landmark JSON, Gemini produces a chronological, plain-language route summary purpose-built for spoken narration. |
| **Amazon Polly Neural TTS Playback** | The Driver HUD's "🔊 Listen to Route" control calls a backend `SYNTHESIZE_SPEECH` action, which invokes **Amazon Polly** (Neural engine, `VoiceId: Kajal`) to generate bilingual Indian English/Hindi audio for hands-free, eyes-on-road navigation. |
| **Admin Simulator with Raw Audio Preview** | A demo-only control panel lets testers switch the HUD's active package and preview the *original* uploaded voice note via an inline HTML5 `<audio>` player, independent of the synthesized Polly output. |
| **Geo-Fenced Cedar Shield** | Dual-stage authorization: landmark tags unlock within 500m of the delivery pin; the Digital Doorbell unlocks only within 20m — enforced via Cedar policy evaluation, not client-side trust. |
| **Status-Aware Digital Doorbell** | A full state machine handles 30-second chime alerts, notification opt-out detection, a 2-ping retry cap, and fallback masked calling — with Do-Not-Call flags respected throughout. |

---

## 🛠️ Tech Stack Matrix

| Layer | Local Emulation | Cloud (Production) |
|---|---|---|
| Compute | SAM Local (`sam local start-api`) | **AWS Lambda** |
| Object Storage | LocalStack S3 | **Amazon S3** |
| Database | LocalStack DynamoDB | **Amazon DynamoDB** (`Deliveries` table) |
| Voice Synthesis | Polly-compatible local stub / direct AWS call | **Amazon Polly** — Neural engine, `VoiceId: Kajal` |
| Infrastructure-as-Code | AWS SAM CLI | **AWS SAM CLI** (`sam build && sam deploy`) |
| Cloud Emulation Layer | **LocalStack v3.8.0** | — |
| AI / ML (multimodal ingestion) | **Google Gemini** — `gemini-3.1-flash-lite` via `google-genai` SDK | Same (external API, environment-agnostic) |
| Authorization | **Cedar Policy Engine** (`cedar-policy-cli`) | Same |
| Backend | **Python 3.12**, `boto3` | Same |
| Frontend | **HTML5**, Vanilla JavaScript, **CSS3** (Dark Slate / Amazon-themed) | Same |

---

## 🚦 Digital Doorbell State Machine

| Condition | Behavior |
|---|---|
| Distance > 20m | Doorbell `DISABLED` — "Locked by Cedar Policy" |
| Notifications Disabled | HUD skips doorbell → `[ 📞 Direct Call Required ]` |
| Distance ≤ 20m & First Tap | Sends 30s chime → state `RINGING_30S` |
| Timeout / 2nd Tap | Button → `[ 🔄 Ping Once More ]` |
| Max Pings Exceeded (2) | State `MAX_PINGS_EXCEEDED` → unlocks `[ 📞 Masked Direct Call ]` (unless Do-Not-Call flag is set) |

---

## 🚀 Step-by-Step Installation, Local Emulation & Deployment Guide

### 1. Start LocalStack (cloud emulation layer)

```bash
# Requires LocalStack v3.8.0+
localstack start -d
```

### 2. Run the local API server

```bash
# Boots the Lambda orchestrator logic against LocalStack-backed
# S3 / DynamoDB endpoints for fast iteration without touching real AWS
python api_server.py
```

### 3. Build and deploy to real AWS via SAM

```bash
# Compile the SAM template and package dependencies
sam build

# One-time cloud deployment (guided config on first run)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### 4. Validate Cedar authorization policies

```bash
cedar validate --policies policies/ --schema schema.cedarschema
```

### 5. Environment variables required

| Variable | Purpose |
|---|---|
| `GOOGLE_GENAI_API_KEY` | Authenticates requests to Gemini for multimodal audio parsing |
| `AWS_REGION` | Target region for S3 / DynamoDB / Polly |
| `POLLY_VOICE_ID` | Defaults to `Kajal`; override for alternate Neural voices |
| `DYNAMODB_TABLE_NAME` | Name of the `Deliveries` table (LocalStack or live) |

---

## ⚙️ Engineering Challenges Overcome

| Challenge | Root Cause | Solution |
|---|---|---|
| **LocalStack vs. real AWS credential conflicts** | `boto3` sessions picked up ambient real AWS credentials when running against LocalStack endpoints, causing auth mismatches and silent failures. | Applied safe `os.environ.setdefault(...)` fallbacks for dummy LocalStack credentials, ensuring real credentials are only used when explicitly present and never silently overridden. |
| **Bedrock marketplace access restrictions** | Fresh AWS accounts require manual model-access approval for Bedrock foundation models (including Claude 3 Haiku), which is not instant and blocked hackathon-speed iteration. | Migrated the extraction pipeline to **Google Gemini (`gemini-3.1-flash-lite`)** via the `google-genai` SDK, ingesting raw `.m4a` audio directly and removing the Bedrock dependency entirely from the critical path. |
| **CloudFormation circular dependencies** | Wiring an S3 bucket's event notification directly to a Lambda function, whose IAM role in turn referenced the same bucket ARN, created a circular resource dependency during `sam deploy`. | Hardcoded a static, pre-declared bucket name in `template.yaml` instead of relying on CloudFormation's auto-generated bucket reference, breaking the dependency cycle. |
| **SAM runtime / packaging mismatches in Codespaces** | Native dependency compilation for Python Lambda layers was unreliable inside GitHub Codespaces without Docker-in-Docker support. | Standardized the SAM template and local dev environment on **Python 3.12**, aligning local interpreter, SAM build target, and Lambda runtime so packaging succeeds natively without container-in-container builds. |

---

## 🏆 Hackathon Attribution

Built for the **AWS & WeMakeDevs "First Commit" Hackathon**.

This submission reflects the project's full evolution — from a LocalStack-emulated, Bedrock-based prototype to a production-shaped hybrid architecture combining Google Gemini's multimodal reasoning with AWS's delivery, storage, authorization, and voice infrastructure.