🧩 Project Overview

AI QA Team is an intelligent test-automation platform that helps QA leads and engineers generate, organize, and execute test cases using AI. It supports open-source frameworks such as Playwright, Selenium, Robot Framework, and n8n, with optional Git repository integration for versioned scripts.

🏗️ Monorepo Structure
ai-qa-team/
├── ai-qa-team-api/   # FastAPI backend (Poetry, MongoDB, Redis)
├── ai-qa-team-ui/    # Next.js frontend (Tailwind + ShadCN)
├── .gitignore
└── README.md

⚙️ Backend Setup — FastAPI + Poetry
🧰 Prerequisites

Python 3.11 or later

Poetry ≥ 2.0

MongoDB Atlas (or local instance)

Redis Cloud (for MVP)

⚙️ Environment File

Create ai-qa-team-api/.env

MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
MONGO_DB=ai_qa_team

REDIS_URL=redis://default:<password>@<host>:<port>

AI_PROVIDER=openai
OPENAI_API_KEY=<your_openai_key>
APP_ENV=development
APP_PORT=8000

🚀 Quick Start
cd ai-qa-team-api
poetry install
poetry run uvicorn app.main:app --reload

<!-- LOCAL -->
py -m uvicorn app.main:app --host localhost --port 8000 --reload


Open http://127.0.0.1:8000/docs
 for the interactive Swagger UI.

💻 Frontend Setup — Next.js + Tailwind + ShadCN
🧰 Prerequisites

Node 18 or later

npm / yarn / pnpm

⚙️ Environment File

Create ai-qa-team-ui/.env.local

NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

🚀 Quick Start
cd ai-qa-team-ui
npm install
npm run dev


Frontend runs at http://localhost:3000

🔁 API ↔ Frontend Integration

Frontend communicates with backend via NEXT_PUBLIC_API_BASE_URL.
Core routes include:

Endpoint	Purpose
/stories	Create / List Stories
/scenarios	AI-generated Test Scenarios
/testcases	CRUD + Smoke/Regression tags
/results	Test Execution Logs
🧠 Tech Stack Summary
Layer	Technology
Frontend	Next.js 14, React 19, Tailwind 3, ShadCN UI
Backend	FastAPI (ASGI), Poetry for dependencies
Database	MongoDB Atlas
Cache/Queue	Redis Cloud
AI Integration	OpenAI (GPT / LLM)
Deployment	Render / Fly.io / Vercel
🧰 Optional Tools
Tool	Purpose
MongoDB Compass	Visualize DB collections
Redis Insight	Inspect Redis keys
Docker Compose	Local Mongo + Redis
VS Code Extensions	Python, Prettier, ESLint
📅 Roadmap
Stage	Milestone
✅	Backend & Frontend setup
🔜	Story → Scenario → TestCase APIs
🔜	AI-based Scenario Generation
🔜	Test Execution + Reports
🔜	Git Integration (Post-MVP)
🛡️ Best Practices

Keep .env files out of version control.

Use role-based access control (Admin → QA Lead → Tester).

In production, store secrets in environment variables or secure vaults.

👥 Contributing

Fork the repo

Create a branch: git checkout -b feature/new-api

Commit: git commit -m "Add Story API"

Push & open a Pull Request

📜 License

Licensed under the MIT License — feel free to use, modify, and distribute with attribution.