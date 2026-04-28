"""
Prediction service: loads the trained model and computes
SHAP values for a single match input.
Falls back to a lightweight synthetic model when no .pkl exists.
"""

import os
import numpy as np
import pandas as pd

MODEL_PKG_PATH = "upset_model.pkl"
FEATURES_CSV   = "features.csv"

_model_pkg      = None
_shap_explainer = None
_synthetic_pipe = None   # fallback


# ─── Model loading ────────────────────────────────────────────────────────────

def _load_real_model():
    """Load saved model package from disk."""
    global _model_pkg, _shap_explainer
    if _model_pkg is not None:
        return True
    try:
        import joblib, shap
        _model_pkg = joblib.load(MODEL_PKG_PATH)
        pipe = _model_pkg["model_b"]

        # Build background data for SHAP explainer
        if os.path.exists(FEATURES_CSV):
            X_bg = (pd.read_csv(FEATURES_CSV)
                      .dropna(subset=["upset"])
                      .sample(min(200, 1000), random_state=42)
                      [_model_pkg["full_cols"]])
            prep        = pipe.named_steps["prep"]
            X_bg_t      = prep.transform(X_bg)
            _shap_explainer = shap.TreeExplainer(
                pipe.named_steps["model"], X_bg_t
            )
        return True
    except Exception as e:
        print(f"[WARN] Could not load real model: {e}")
        return False


def _load_synthetic_model():
    """Build a tiny RF on synthetic data as demo fallback."""
    global _synthetic_pipe
    if _synthetic_pipe is not None:
        return
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline  import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer

    rng  = np.random.default_rng(42)
    n    = 3000
    rank = rng.integers(1, 200, n)
    opp  = rng.integers(1, 200, n)
    ctfi = rng.integers(0, 20,  n)
    sent = rng.uniform(-1, 1,   n)
    fat  = rng.integers(0, 12,  n)
    rnd  = rng.integers(1, 8,   n)
    bof  = rng.choice([3, 5],   n)

    X = np.column_stack([rank, opp, rank/opp,
                         np.sign(rank-opp)*np.log1p(np.abs(rank-opp)),
                         (rank>opp).astype(int),
                         rnd, bof, ctfi, sent, fat])
    y = ((rng.random(n) < 1/(1+np.exp(-0.3*(rank/opp - 1) + 0.05*ctfi
                                        - 0.1*sent + 0.08*fat
                                        + rng.normal(0,.4,n)))).astype(int))

    pipe = Pipeline([
        ("imp",   SimpleImputer(strategy="median")),
        ("scl",   StandardScaler()),
        ("model", RandomForestClassifier(n_estimators=100, random_state=42)),
    ])
    pipe.fit(X, y)
    _synthetic_pipe = pipe


FULL_COLS = [
    "rank","opp_rank","rank_ratio","log_rank_diff","is_underdog",
    "round_num","best_of","ctfi",
    "sentiment_polarity","fatigue_total","fatigue_word_density",
    "fatigue_physical","fatigue_mental","fatigue_schedule",
    "fatigue_injury","fatigue_motivation",
    "first_person_rate","negation_rate","llm_is_fatigued",
]


def _build_row(player_rank, opp_rank, ctfi, sentiment_polarity,
               fatigue_total, round_num, best_of, extra=None):
    row = {
        "rank":              player_rank,
        "opp_rank":          opp_rank,
        "rank_ratio":        player_rank / max(opp_rank, 1),
        "log_rank_diff":     np.sign(player_rank-opp_rank)*np.log1p(abs(player_rank-opp_rank)),
        "is_underdog":       int(player_rank > opp_rank),
        "round_num":         round_num,
        "best_of":           best_of,
        "ctfi":              ctfi,
        "sentiment_polarity": sentiment_polarity,
        "fatigue_total":     fatigue_total,
        "fatigue_word_density": fatigue_total / 100,
        "fatigue_physical":  max(0, fatigue_total - 2),
        "fatigue_mental":    max(0, fatigue_total - 3),
        "fatigue_schedule":  max(0, fatigue_total - 4),
        "fatigue_injury":    0,
        "fatigue_motivation": 0,
        "first_person_rate": 0.15,
        "negation_rate":     0.05,
        "llm_is_fatigued":   0.5,
        "rank_bin":          "top100" if player_rank <= 100 else "outside100",
    }
    if extra:
        row.update(extra)
    return row


# ─── Public API ───────────────────────────────────────────────────────────────

def predict_with_explanation(player_rank, opp_rank, ctfi,
                              sentiment_polarity, fatigue_total,
                              round_num, best_of, extra=None):
    """
    Returns (probability: float, shap_dict: dict[feature→shap_value]).
    shap_dict is None when running in synthetic-fallback mode.
    """
    row = _build_row(player_rank, opp_rank, ctfi, sentiment_polarity,
                     fatigue_total, round_num, best_of, extra)

    # Try real model first
    if os.path.exists(MODEL_PKG_PATH) and _load_real_model():
        pipe = _model_pkg["model_b"]
        cols = _model_pkg["full_cols"]
        df   = pd.DataFrame([row])[[c for c in cols if c in row]]
        prob = float(pipe.predict_proba(df)[0, 1])

        shap_dict = {}
        if _shap_explainer is not None:
            prep   = pipe.named_steps["prep"]
            X_t    = prep.transform(df)
            sv     = _shap_explainer.shap_values(X_t)
            vals   = sv[1][0] if isinstance(sv, list) else sv[0]
            num_cols = prep.transformers_[0][2]
            cat_cols = prep.transformers_[1][2] if len(prep.transformers_) > 1 else []
            all_cols = list(num_cols) + list(cat_cols)
            shap_dict = {c: float(v) for c, v in zip(all_cols, vals)}

        return prob, shap_dict

    # Fallback: synthetic model
    _load_synthetic_model()
    x = np.array([[row["rank"], row["opp_rank"], row["rank_ratio"],
                   row["log_rank_diff"], row["is_underdog"],
                   row["round_num"], row["best_of"], row["ctfi"],
                   row["sentiment_polarity"], row["fatigue_total"]]])
    prob = float(_synthetic_pipe.predict_proba(x)[0, 1])

    # Approximate "SHAP" via feature deltas (for demo purposes)
    shap_dict = _approx_shap(row, prob)
    return prob, shap_dict


def _approx_shap(row, base_prob):
    """Rough feature attribution when real SHAP is unavailable."""
    _load_synthetic_model()
    contribs = {}
    base_x = np.array([[row["rank"], row["opp_rank"], row["rank_ratio"],
                         row["log_rank_diff"], row["is_underdog"],
                         row["round_num"], row["best_of"], row["ctfi"],
                         row["sentiment_polarity"], row["fatigue_total"]]])

    feature_names = ["rank","opp_rank","rank_ratio","log_rank_diff",
                     "is_underdog","round_num","best_of","ctfi",
                     "sentiment_polarity","fatigue_total"]
    for i, name in enumerate(feature_names):
        perturbed = base_x.copy()
        perturbed[0, i] = 0
        delta = base_prob - float(_synthetic_pipe.predict_proba(perturbed)[0, 1])
        contribs[name] = round(delta, 4)
    return contribs
