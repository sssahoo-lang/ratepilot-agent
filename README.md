# BillFight
> AI-powered bill negotiation agent that researches competitor pricing and negotiates lower rates autonomously.

## What it does

BillFight helps people lower recurring bills by turning a bill upload into an autonomous negotiation workflow. A user uploads a PDF, text export, or photo of a bill; the agent extracts the key account details, researches live competitor pricing, builds a negotiation strategy, and drafts a provider-ready email. The app can send that email through Gmail, track provider replies, classify the next best action, and preserve every step in a negotiation timeline. Savings outcomes are summarized in a dashboard with monthly savings, annual projections, win rate, and per-negotiation PDF exports.

## How the agent works

1. Upload — user uploads bill (PDF, TXT, or photo)
2. Parse — Claude vision or text extraction reads the bill
3. Research — live web search retrieves real competitor pricing
4. Strategy — agent builds negotiation strategy with target price, walkaway threshold, and leverage points
5. Draft — agent writes a personalized negotiation email
6. Send — email sent directly to provider via Gmail
7. Classify — agent reads provider reply and decides: accept, counter, or escalate
8. Track — outcome logged, savings dashboard updated

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite, vanilla CSS |
| Backend | Python, FastAPI, SQLite |
| AI | Anthropic Claude API, web search tool use |
| Email | Gmail API via OAuth |
| Deploy | Railway (backend), Netlify (frontend) |

## Project structure

```text
.
├── README.md
├── agent_service.py
├── database.py
├── gmail_service.py
├── main.py
├── provider_emails.py
├── requirements.txt
├── sample_bill.txt
├── seed_data.py
├── routers/
│   ├── __init__.py
│   ├── agent.py
│   ├── bills.py
│   ├── email_router.py
│   └── negotiations.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── constants.js
        ├── index.css
        ├── main.jsx
        ├── components/
        │   └── Logo.jsx
        └── utils/
            └── savings.js
```

## Local setup

1. Clone the repo

```bash
git clone <repo-url>
cd billfight-agent
```

2. Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_claude_api_key
python main.py
```

The API runs at `http://localhost:8000`.

3. Frontend run

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`. `frontend/.env.development` is included and points the app at `http://localhost:8000/api`.

4. Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| ANTHROPIC_API_KEY | Yes | Claude API key for agent pipeline |
| SEED_DEMO_DATA | No | Set to "true" to seed demo negotiations |

## Features

- Autonomous multi-stage negotiation pipeline
- Live competitor pricing via web search (not hallucinated)
- PDF, TXT, and image bill upload with Claude vision
- Real email sending to providers via Gmail API
- Multi-turn negotiation with counter-offer context preserved
- Savings dashboard with win rate, total saved, annual projection
- Per-negotiation PDF export with full negotiation summary
- Failed pipeline recovery with retry support
- Dark/light theme toggle

## Known limitations

- Gmail OAuth requires local setup (`credentials.json`)
- SQLite resets on Railway redeploy without a persistent volume
- No user authentication — all negotiations are shared
