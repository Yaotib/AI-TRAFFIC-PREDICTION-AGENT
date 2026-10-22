# [DepartWise] — The Agent That Explains Why

> An AI agent that tells Accra commuters **when to leave**, and shows exactly **why**, using real, traceable data.

**Hackathon track:** The Agent That Can Explain Why
**Status:** MVP, built for [Hackathon Name] 2026
**Team:** [Names and roles]
**Demo:** [Link] · **Video:** [Link]

---

## The Problem

Traffic in Accra is unpredictable, and commuters usually decide when to leave by guesswork, habit or WhatsApp updates. Navigation apps show current conditions, but rarely explain **why** one departure time beats another or how confident the advice is.

## Our Solution

DepartWise helps a commuter answer one question: **"When should I leave?"**

1. Enter an origin, a destination, and a departure time or arrival deadline.
2. The agent checks traffic-aware estimates for several candidate departure times.
3. A deterministic decision engine compares them and picks the best time.
4. The agent explains the recommendation in plain language, using only the retrieved data.

Every claim in an explanation traces back to a real data point. If data is missing, the agent says so instead of guessing.

## Why It Is Different

- **The AI never does the maths.** Times, differences and rankings come from tested Python code, not the LLM.
- **Grounded explanations.** The language model can only describe results the backend supplies, and it cannot override the decision engine.
- **Honest about uncertainty.** Estimates are labelled by type: provider estimate, traffic-aware estimate, or simulated demo data. Simulated data is always visibly marked.

## How It Works

```
User (origin, destination, time/deadline)
        │
        ▼
  Frontend (Next.js)
        │
        ▼
  Backend API (FastAPI)
        │
        ▼
  AI Agent (NVIDIA Nemotron)
        ├── Geocoding tool
        ├── Route / departure-time sweep tool
        └── Context tool (Zetaris)
        │
        ▼
  Deterministic Decision Engine
        │
        ▼
  Grounded Explanation ──► Frontend shows recommendation
```

| Layer | Responsibility |
|---|---|
| **NVIDIA Nemotron** | Understands the request, asks clarifying questions, selects approved tools, writes the explanation from supplied results |
| **Python backend** | Validates input, calls providers, checks returned data, calculates differences, applies selection rules, handles errors and timeouts |
| **Zetaris** | Data integration: exposes supporting context data (e.g., weather) through a queryable source for the backend |
| **Decision engine** | Ranks candidate departure times and checks deadlines. Fully deterministic and unit-tested |

## Tech Stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic, httpx |
| Routing and geocoding | Google Routes API, Google Geocoding API |
| LLM | NVIDIA Nemotron via build.nvidia.com (OpenAI-compatible API) |
| Data integration | Zetaris |
| Testing | pytest, respx, Playwright |
| Hosting | Vercel (frontend), [Render / local] (backend) |

## Verification Status

We only claim what we have tested.

- [ ] Google Routes returns traffic-aware durations for Accra trips
- [ ] Future-departure estimates vary plausibly across the day
- [ ] Nemotron free endpoint tested with tool calling (model: `[model-id]`)
- [ ] Zetaris end-to-end query succeeds from the backend
- [ ] Full demo flow passes twice in a row

## Getting Started

> Adjust paths to match the repository layout.

### Prerequisites
- Python 3.11+ and Node.js 18+
- A Google Maps Platform API key (Routes and Geocoding enabled)
- An NVIDIA API key from [build.nvidia.com](https://build.nvidia.com)
- (Optional) A running Zetaris instance

### Environment variables

Create a `.env` file in the backend folder. **Never commit it.**

```
LLM_PROVIDER=nvidia
LLM_MODEL=<verified-model-id>
NVIDIA_API_KEY=<secret>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
GOOGLE_MAPS_API_KEY=<secret>
ZETARIS_ENABLED=false
DEMO_MODE=false
```

Set `ZETARIS_ENABLED=true` only after the Zetaris connection is configured and tested.

### Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Run the frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Run the tests
```bash
cd backend && pytest
cd frontend && npx playwright test
```

## Demo Script (about 3 minutes)

1. **Problem (20s):** Accra commuters guess when to leave.
2. **Input (20s):** Enter "Madina → Accra Central, arrive by 9:00."
3. **Retrieval (30s):** Show real candidate departure times and their durations.
4. **Decision (30s):** The decision engine ranks them and recommends a time, with the margin before the deadline.
5. **Explanation (40s):** Nemotron explains the choice using only retrieved data, including uncertainty.
6. **Honesty (20s):** Trigger a missing-data case. The agent states the limitation instead of guessing.
7. **Integration (20s):** Show the Zetaris context data feeding the explanation. Skip this if it is not verified.

## Data Honesty

- Traffic claims appear only when the provider response supports them.
- Predictions are **provider-based estimates**, not our own trained model.
- Anything simulated is labelled "Simulated" in the interface.

## Known Limitations

- Traffic quality for Accra depends on the routing provider's coverage and has been tested only on a small set of routes.
- No accounts, saved trips or push notifications in the MVP.
- Free API tiers have rate limits; the app enforces request limits and timeouts.
- [Add anything else you discover.]

## Roadmap

- Historical data collection and prediction-versus-actual evaluation
- Congestion alerts
- Learned prediction models once reliable data exists
- Expansion to other Ghanaian cities

## Project Structure

```
/frontend    Next.js app
/backend     FastAPI, decision engine, provider adapters
/backend/agent   Nemotron client, tools, prompts
/docs        Architecture notes
```

## Branching

`main` (demo-ready) · `frontend` · `backend` · `ai`. Merge into `main` through pull requests only.

## Team

| Name | Role |
|---|---|
| Cassandra Adoley Ankamah, David Okyere Adarkwah | Frontend |
| Caleb Baffoe, Calvin Duah | Backend |
| Jeffery Kwasi Anyimah, Yaw Oti Boachie | AI |

## Acknowledgements

NVIDIA Nemotron · Zetaris · Google Maps Platform

