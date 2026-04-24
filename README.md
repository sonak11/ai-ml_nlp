# 🎾 Tennis Upset Predictor — Streamlit App

A GenAI-powered dashboard for analysing Grand Slam upsets, built on top of your existing
`tennis_upsets.db`, `upset_model.pkl`, and NLP pipeline.

## Three features

| Page | What it does | Key tech |
|---|---|---|
| 🚨 Upset Alert | Predict upset probability + LLM explanation | Random Forest · SHAP · Groq |
| 📋 Scouting Report | RAG-based player fatigue profile | ChromaDB · Sentence Transformers · Groq |
| 💬 Ask the Model | Conversational SQL + transcript agent | LangChain · Groq · SQLite |

---

## Local setup

```bash
# 1. Clone / copy files into one folder
cp tennis_upsets.db upset_model.pkl features.csv tennis_app/
cd tennis_app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Groq API key (free at console.groq.com)
export GROQ_API_KEY="gsk_xxxxxxxxxxxx"

# 4. Run
streamlit run app.py
```

The app works **without** a Groq key — it falls back to rule-based explanations.
It also works without a trained model — it uses a synthetic fallback RF.

---

## Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repository.
2. Include your `tennis_upsets.db` (if < 25 MB) and `upset_model.pkl`.
   - For larger DBs, see the "Large data" section below.
3. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select your repo.
4. Set **Secrets** in the dashboard:
   ```toml
   GROQ_API_KEY = "gsk_xxxxxxxxxxxx"
   HF_API_TOKEN = "hf_xxxxxxxxxxxx"   # optional
   ```
5. Click **Deploy**.

### Large data (> 25 MB)

If your DB is large, download it at startup. Add to `app.py`:

```python
import requests, os
if not os.path.exists("tennis_upsets.db"):
    url = "https://your-public-url/tennis_upsets.db"
    with open("tennis_upsets.db", "wb") as f:
        f.write(requests.get(url).content)
```

Free hosts: Dropbox (direct link), GitHub Releases, Hugging Face Datasets.

---

## File structure

```
tennis_app/
├── app.py                  # Main Streamlit entry point (multi-page)
├── prediction_service.py   # Model loading + SHAP
├── rag_service.py          # ChromaDB indexing + retrieval
├── agent_service.py        # LangChain SQL + vector agent
├── requirements.txt
├── pages/
│   ├── __init__.py
│   ├── upset_alert.py      # Page 1
│   ├── scouting_report.py  # Page 2
│   └── agent_chat.py       # Page 3
└── README.md

# Data files (copy from your pipeline output):
├── tennis_upsets.db
├── upset_model.pkl
└── features.csv
```

---

## Pipeline integration

Run these in order before starting the app:

```bash
python data_ingestion.py    # → tennis_upsets.db
python scraping.py          # → transcripts table
python nlp.py               # → NLP columns in transcripts
python features.py          # → features.csv
python model.py             # → upset_model.pkl
```

Then start the app — it reads everything automatically.

---

## API keys

| Key | Where to get | Cost |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free (60 rpm) |
| `HF_API_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Free |
