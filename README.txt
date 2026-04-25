# 🎾 GrandSlam IQ — Tennis Upset Intelligence

> **Can AI predict a Grand Slam tennis upset before it happens?**
>
> This project combines 10 years of ATP match data with 2,279 real player press conference
> transcripts to detect fatigue signals and forecast upsets at the four Grand Slams.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![ROC-AUC](https://img.shields.io/badge/ROC--AUC-0.70-green)
![Transcripts](https://img.shields.io/badge/Transcripts-2%2C279-yellow)

---

## What This Does

An upset in tennis is when the lower-ranked player beats the higher-ranked favourite.
At Grand Slams, roughly 1 in 4 matches is an upset — but which ones? This project
builds a machine learning pipeline that predicts upsets using:

- **Player rankings** and rank gap between competitors
- **Cumulative Tournament Fatigue Index (CTFI)** — sets already played in the tournament
- **NLP signals from press conferences** — what players say about their physical and mental state

The key hypothesis: *players who are about to be upset often telegraph it in their post-match
press conferences the day before.*

---

## Three Tools

| Tool | What It Does | Tech |
|------|-------------|------|
| ⚡ **Upset Alert** | Enter two players → get upset probability + AI explanation | Random Forest · SHAP · Groq LLM |
| ◎ **Scouting Report** | Ask about a player's fatigue history → get tactical report | Transcript search · Groq LLM |
| ◉ **Ask the Model** | Chat with 10 years of match data in plain English | SQL routing · Transcript search · Groq |

---

## Results

| Metric | Value |
|--------|-------|
| Model ROC-AUC | **0.70** |
| Baseline (rank only) | 0.62 |
| Average upset rate | 26% |
| Transcripts collected | 2,279 |
| Match rows | 9,876 |
| Tournaments covered | 12 Grand Slams (2022–2024) |

The model correctly ranks an actual upset above a non-upset **70% of the time** — a meaningful
improvement over simply using rankings (62%).

---

## Key Findings

1. **Wimbledon is the most unpredictable Grand Slam** — 30.5% upset rate vs 26.7% at the US Open
2. **Fatigue language is a real signal** — transcripts with 5+ fatigue keywords before a match
   where the speaker was the favourite showed higher upset rates
3. **CTFI matters** — players who've already played 15+ sets before their quarterfinal are
   significantly more upset-prone
4. **Top-10 players are not immune** — Nadal (17), Djokovic (16), Zverev (15) lead the
   upset-loss list despite being favourites

---

## Project Structure

```
aiml_nlp/
│
├── app.py                  ← Streamlit app (single file, all pages)
│
├── data_ingestion.py       ← Part 1: download ATP match data from GitHub
├── scraping.py             ← Part 2: scrape ASAP Sports press conferences
├── nlp.py                  ← Part 3: NLP pipeline (fatigue detection, sentiment)
├── features.py             ← Part 4: build feature matrix (features.csv)
├── model.py                ← Part 5: train Random Forest, compute SHAP
│
├── tennis_upsets.db        ← SQLite database (matches + transcripts)
├── upset_model.pkl         ← Trained model package
├── features.csv            ← Feature matrix (9,876 rows × 26 cols)
│
└── requirements.txt
```

---

## Setup & Running Locally

### Prerequisites

- Python 3.11+
- A free [Groq API key](https://console.groq.com) (for AI explanations)

### Step 1 — Install

```bash
git clone https://github.com/YOUR_USERNAME/aiml_nlp.git
cd aiml_nlp

python3.11 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Step 2 — Run the data pipeline

```bash
python data_ingestion.py    # Download match data (~2 min)
python scraping.py          # Scrape press conferences (~2 hours, 2,279 transcripts)
python nlp.py               # Run NLP pipeline (~30 min)
python features.py          # Build feature matrix
python model.py             # Train model + generate plots
```

> **Note:** `scraping.py` takes ~2 hours because it politely delays between requests
> (1.5–3.5 seconds) to avoid overwhelming ASAP Sports servers. Once complete,
> re-running is fast because already-scraped transcripts are skipped.

### Step 3 — Launch the app

```bash
streamlit run app.py
```

Open `http://localhost:8501`. Enter your Groq API key in the Home page.

---

## Deploying to Streamlit Cloud (Free)

```bash
git add .
git commit -m "initial commit"
git push origin main
```

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo
3. Set main file: `app.py`
4. Add secret: `GROQ_API_KEY = "gsk_your_key_here"`
5. Deploy

Your app will be live at `https://your-username-aiml-nlp-app-XXXXX.streamlit.app`

---

## Data Sources

| Source | What | License |
|--------|------|---------|
| [Jeff Sackmann / tennis_atp](https://github.com/JeffSackmann/tennis_atp) | ATP match results 2015–2024 | CC BY-NC-SA 4.0 |
| [ASAP Sports](https://www.asapsports.com) | Press conference transcripts | Public archive, scraped for research |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| ML Model | scikit-learn Random Forest |
| Explainability | SHAP (TreeExplainer) |
| NLP | spaCy, Hugging Face DistilBERT |
| Sentiment | DistilBERT-SST2 via `transformers` |
| Web scraping | requests + BeautifulSoup |
| Database | SQLite |
| Vector store | ChromaDB (optional RAG) |
| LLM | Groq API (Llama 3 70B, free tier) |
| App framework | Streamlit |
| Hosting | Streamlit Cloud (free) |

---

## How the NLP Works

Each transcript is analysed for **60+ fatigue phrases** across five categories:

| Category | Example phrases |
|----------|----------------|
| Physical | "tired", "heavy legs", "cramping", "not 100%", "drained" |
| Mental | "mentally exhausted", "couldn't focus", "lost concentration" |
| Schedule | "back-to-back", "five sets", "tough schedule", "no rest" |
| Injury | "my knee", "my shoulder", "blister", "medical timeout" |
| Motivation | "doubt", "question mark", "hard to believe", "uncertain" |

These counts are combined with a **DistilBERT sentiment score**, **first-person pronoun rate**,
and **negation rate** to create the NLP feature block.

---

## Limitations

- **This is not a betting system.** Sport has irreducible randomness.
- NLP features currently have limited uplift (0.70 vs 0.62 baseline) because transcript-to-match
  linking is imperfect — not all transcripts are from the day before the match in question.
- The model was trained on 2015–2024 data; player styles and ranking systems evolve.
- The scraper only covers 2022–2024 due to time constraints. Extending to 2015–2021 would
  significantly improve NLP feature coverage.

---

## What's Next

- [ ] Real-time pipeline: scrape transcript tonight → predict tomorrow's upset
- [ ] Extend scraping to 2015–2021 for more NLP training data
- [ ] Add women's draw (WTA) transcripts
- [ ] Fine-tune a small LLM on tennis transcripts for better fatigue detection
- [ ] Add live ATP ranking feeds

---

## Author

**Sonakshi Sharma** — AI/ML project combining sports analytics, NLP, and machine learning.

Built with Python, scikit-learn, Streamlit, and a lot of tennis press conference reading.