# AIContentWriter 🚀

This is a fully autonomous, AI-driven content and outreach system that:
- Writes long-form SEO blog posts from keyword queues
- Adds images, YouTube videos, citations, and internal links
- Publishes the post via API
- Then researches 100+ relevant websites, finds emails, writes personalized pitches, and sends outreach campaigns — all automatically.

Built using a custom stack of LangChain agents, AI tool integrations, FastAPI, and SendGrid.

---

## 🧠 Core Capabilities

### 📝 Blog Post Generation
- Pops keywords from a queue and runs deep research via Serper, YouTube API, and more
- Generates long-form blog content using OpenAI + Google Gemini
- Adds:
  - Internal links (based on site structure)
  - Relevant images (via Imagen or scraped assets)
  - Embedded YouTube videos
  - Citations for factual claims
- SEO optimization included: metadata, keyword targeting, readability

### 🔗 AI-Powered Backlink Outreach
- AI agent reads each blog post and identifies 100+ relevant websites to pitch
- Evaluates site quality and audience match using AI
- Finds real email addresses using web scraping and pattern recognition
- Writes **uniquely personalized emails** per site (no templates)
  - Compliments their writing
  - Justifies the blog post’s value to their audience
- Sends via SendGrid and tracks delivery + responses

---

## 🛠️ Tech Stack

### 🧠 AI & Agents
- OpenAI GPT (LangChain agents)
- Google Gemini (factual validation + content synthesis)
- Google Imagen (optional image generation)
- LangChain with multi-agent orchestration

### 🌍 APIs & Services
- Serper API (for web search)
- YouTube Data API (video embedding)
- SendGrid (outbound email)
- Google Cloud (LLMs, storage)

### 💻 Backend
- **FastAPI** (Python)
- Uvicorn (ASGI server)
- REST API endpoints for orchestration
- Modular `src/` architecture

### 🗃️ Database
- MySQL (MariaDB)
- Used to store:
  - Prospective outreach URLs
  - Keyword queue
  - Blog metadata
  - Email delivery stats

### ⚙️ DevOps & Infrastructure
- Dockerized
- Vercel (optional serverless deployment)
- Render support (via `render.yaml`)
- `.env` based secrets handling

---

## 🧩 Key Modules

| File | Purpose |
|:--|:--|
| `main.py` | FastAPI app entry point |
| `src/ContentAPIHandler.py` | Blog writer + optimizer agent |
| `src/ProspectGenerator.py` | Backlink research & outreach |
| `src/EmailReplyProcessor.py` | Email tracking + response handling |
| `src/DatabaseService.py` | DB connection + query methods |
| `local_tests.py` | Manual CLI test runner |
| `render.yaml` / `vercel.json` | Hosting configs |

---

## 🧠 What Makes It Unique

- Fully autonomous from **keyword → published post → AI outreach**
- No templates: each pitch is written by an LLM for that specific site/contact
- AI agents choose the strategy dynamically based on blog content
- Real-world infrastructure: emails are delivered, links go live, stats are tracked

---

## 🔐 Security & Credentials

- API keys are secured via `.env`
- SendGrid and DB credentials handled securely
- Never commit sensitive keys — system uses dynamic environment config
- 
---

## 🧪 Status
- ✅ Content generation working
- ✅ Outreach agent functioning
- ✅ Posts published and live
- ✅ Email tracking implemented

---

