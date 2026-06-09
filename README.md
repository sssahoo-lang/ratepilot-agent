# RatePilot — Autonomous Bill Negotiation Agent

> An autonomous AI agent that negotiates your monthly bills — researches competitor pricing, builds a data-driven strategy, and drafts personalized negotiation emails, all without human input.

---

## What It Does

Most people overpay on recurring bills simply because negotiating is time-consuming and awkward. RatePilot automates the entire process.

Upload a bill — internet, wireless, cable, or any recurring service — and the agent independently analyzes the market, identifies leverage points, and produces a ready-to-send negotiation email backed by real competitor data. When the provider replies, paste their response and the agent decides whether to accept, counter, or escalate. Every decision is logged with reasoning, and all outcomes are tracked on a savings dashboard.

---

## How the Agent Works

The pipeline runs autonomously across eight stages:

1. **Upload** — User uploads a bill as PDF, TXT, or photo (JPG/PNG/WEBP)
2. **Parse** — Extracts provider, amount, account number, and line count using regex and Claude vision for images
3. **Research** — Agent analyzes competitor pricing using market knowledge, tailored to account type (individual vs. family/multi-line)
4. **Strategy** — Builds a negotiation plan with opening position, key arguments, target price, and walkaway threshold
5. **Draft** — Generates a personalized negotiation email grounded in real account details and market data
6. **Send** — Email sent directly to the provider via Gmail API *(optional — requires Gmail OAuth setup)*
7. **Classify** — Agent reads the provider's reply and autonomously decides: accept, counter, or escalate
8. **Track** — Outcome logged, savings dashboard updated with monthly and annual savings

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, vanilla CSS |
| Backend | Python 3.13, FastAPI, SQLite |
| AI | Anthropic Claude API, multi-stage agentic pipeline |
| Email | Gmail API via OAuth 2.0 |
| Export | jsPDF — client-side PDF generation |
| Deploy | Railway (backend), Netlify (frontend) |

---

## Features

- **Autonomous multi-stage negotiation pipeline** — research → strategy → draft → classify → escalate
- **Multi-line family plan support** — detects line count and compares correct family plan pricing
- **PDF, TXT, and image bill upload** — Claude vision handles photographed paper bills
- **Real email sending** to providers via Gmail API
- **Multi-turn negotiation loop** — counter-offers preserve full bill context across rounds
- **Confidence scoring** — every agent decision includes a confidence score and reasoning
- **Full audit trail** — every pipeline step logged with reasoning and decision
- **Savings dashboard** — win rate, total saved, annual projection, per-provider breakdown
- **PDF export** — one-click negotiation summary with full timeline, strategy, and outcome
- **Failed pipeline recovery** — automatic error detection, error message display, retry button
- **Dark / light theme toggle**

---

## Project Structure

```
RatePilot-agent/
├── main.py                  # FastAPI app entrypoint
├── agent_service.py         # Claude API — research, strategy, email draft
├── database.py              # SQLite schema and migrations
├── gmail_service.py         # Gmail OAuth send/reply helpers
├── provider_emails.py       # Provider customer service email lookup
├── requirements.txt
├── seed_data.py             # Demo data (disabled by default)
├── routers/
│   ├── agent.py             # Pipeline orchestration — /api/agent
│   ├── bills.py             # Bill upload and parsing — /api/bills
│   ├── negotiations.py      # Negotiation CRUD — /api/negotiations
│   └── email_router.py      # Email send/check — /api/email
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main React app — all views and state
    │   ├── index.css         # Design system — dark SaaS theme
    │   ├── constants.js      # API base URL (env-based)
    │   ├── utils/savings.js  # Savings computation helpers
    │   └── components/
    │       └── Logo.jsx      # Brand, nav icons, sidebar
    ├── .env.development      # Points to localhost:8000
    ├── .env.production       # Points to Railway backend
    └── vite.config.js
```

---
# RatePilot

> An autonomous AI agent that negotiates your monthly bills...

**Live Demo:** https://meek-tartufo-0c3f73.netlify.app

---



## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for the full agent pipeline |
| `SEED_DEMO_DATA` | No | Set to `true` to seed demo negotiations on startup |

### Gmail Email Sending *(optional)*

Email sending requires Gmail OAuth credentials. Place these files in the project root:

- `credentials.json` — from Google Cloud Console (OAuth 2.0 Desktop app)
- `gmail_token.json` — generated on first run via browser OAuth flow

Without these files the app runs fully — email sending is skipped and the negotiation email is displayed for manual copying.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/bills/upload` | Upload bill (PDF, TXT, JPG, PNG, WEBP) |
| `GET` | `/api/bills/{id}` | Get parsed bill data |
| `POST` | `/api/agent/start` | Start negotiation pipeline |
| `POST` | `/api/agent/simulate-reply` | Submit provider reply for classification |
| `POST` | `/api/agent/retry` | Retry a failed negotiation |
| `GET` | `/api/negotiations/` | List all negotiations |
| `GET` | `/api/negotiations/{id}` | Get full negotiation with steps |
| `DELETE` | `/api/negotiations/{id}` | Delete a negotiation |
| `POST` | `/api/email/send` | Send negotiation email via Gmail |
| `POST` | `/api/email/check-reply` | Check Gmail for provider reply |

---

## Known Limitations

- **Gmail OAuth requires local setup** — the interactive browser flow does not work in server production without additional configuration
- **SQLite resets on Railway redeploy** — without a persistent volume, negotiation history is lost on each deployment
- **No user authentication** — all negotiations are visible to anyone with the URL; designed as a single-user tool
- **Free tier API limits** — Anthropic free tier (10K tokens/minute) may slow the pipeline on large multi-page bills; upgrading to Tier 1 ($5) resolves this

---

## Roadmap

- [ ] PostgreSQL for persistent production storage
- [ ] JWT authentication and multi-user support
- [ ] Live web search integration for real-time competitor pricing
- [ ] Celery + Redis for async task queue
- [ ] Chrome extension for in-browser bill detection
- [ ] Provider reply auto-detection via Gmail polling

---

## Author

**Sriya Smita Sahoo**
MS Computer Science — Indiana University Bloomington
[linkedin.com/in/sriya-smita-sahoo](https://linkedin.com/in/sriya-smita-sahoo) · [github.com/sssahoo-lang](https://github.com/sssahoo-lang)
