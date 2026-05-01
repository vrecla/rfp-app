# RFP Tendering Workflow

AI-assisted tendering tool: RFP → Internal Brief → Ops Questions → Estimate Draft.

Built with Python/Flask + Anthropic Claude API.

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/rfp-tender-app.git
cd rfp-tender-app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env
# Edit .env and paste your Anthropic API key

# 5. Run locally
python app.py
# Open http://localhost:5000
```

---

## Deploy to Railway (recommended — free tier available)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo
4. Go to **Variables** and add:
   - `ANTHROPIC_API_KEY` = your key from [console.anthropic.com](https://console.anthropic.com)
5. Railway auto-deploys. Your app gets a public URL.

---

## Deploy to Render (free tier)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. Add environment variable: `ANTHROPIC_API_KEY`
6. Deploy

---

## Deploy to Heroku

```bash
heroku create your-app-name
heroku config:set ANTHROPIC_API_KEY=your_key_here
git push heroku main
```

---

## How It Works

| Stage | What happens |
|-------|-------------|
| 1. RFP Brief | Paste RFP text → Claude extracts and structures a job brief |
| 2. Ops Input | Claude generates tailored ops questions → team fills in form |
| 3. Estimate Draft | Brief + ops answers → structured estimate and proposal draft |

All AI calls stream in real time so you see output as it's generated.

---

## Project Structure

```
rfp-tender-app/
├── app.py              # Flask app + API routes
├── templates/
│   └── index.html      # Full frontend (single page)
├── requirements.txt
├── Procfile            # For Railway/Heroku
├── railway.toml        # Railway config
├── .env.example
├── .gitignore
└── README.md
```
