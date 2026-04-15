"""
PART 5 — Model Training & Evaluation
======================================
Trains a Random Forest classifier to predict Grand Slam upsets.
Two model variants are compared:
  A. "Traditional only"   — rank + CTFI features, no NLP
  B. "Full model"         — rank + CTFI + NLP transcript features

Steps:
  1. Load feature matrix (features.csv from Part 4)
  2. Impute / encode categoricals
  3. Train / test split (time-based: train on older matches, test on recent)
  4. Hyperparameter search (GridSearchCV)
  5. Evaluation: ROC-AUC, precision/recall, confusion matrix
  6. SHAP feature importance
  7. Export model to upset_model.pkl

Install dependencies:
    pip install scikit-learn shap matplotlib pandas numpy joblib

Usage:
    python part5_model.py
"""

import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # headless rendering
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.pipeline  import Pipeline
from sklearn.compose   import ColumnTransformer
from sklearn.preprocessing import (
    StandardScaler, OrdinalEncoder, LabelEncoder
)
from sklearn.impute    import SimpleImputer
from sklearn.model_selection import (
    TimeSeriesSplit, GridSearchCV, cross_val_score
)
from sklearn.metrics import (
    classification_report, roc_auc_score, roc_curve,
    confusion_matrix, ConfusionMatrixDisplay,
    average_precision_score, PrecisionRecallDisplay,
)
from sklearn.calibration import CalibratedClassifierCV

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("[WARN] shap not installed — feature importance plot will be skipped.")

warnings.filterwarnings("ignore", category=UserWarning)

FEATURES_CSV  = "features.csv"
MODEL_OUT     = "upset_model.pkl"
PLOTS_DIR     = "."

# feature definitions 

# Features available without any transcripts
TRADITIONAL_FEATURES = [
    "rank",
    "opp_rank",
    "rank_ratio",
    "log_rank_diff",
    "is_underdog",
    "round_num",
    "best_of",
    "ctfi",
]

# Additional features from NLP
NLP_FEATURES = [
    "sentiment_polarity",
    "fatigue_total",
    "fatigue_word_density",
    "fatigue_physical",
    "fatigue_mental",
    "fatigue_schedule",
    "fatigue_injury",
    "fatigue_motivation",
    "first_person_rate",
    "negation_rate",
    "llm_is_fatigued",
]

CATEGORICAL_FEATURES = ["rank_bin"]

TARGET = "upset"


# data loading 

def load_features(path: str = FEATURES_CSV) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        print(f"Loaded {len(df):,} rows, {len(df.columns)} columns from {path}")
    except FileNotFoundError:
        print(f"[WARN] {path} not found — generating synthetic data for demonstration.")
        df = _generate_synthetic_data()
    return df


def _generate_synthetic_data(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic dataset that mimics the real feature structure.
    Used for end-to-end testing without scraped data.
    """
    rng = np.random.default_rng(seed)

    rank        = rng.integers(1, 200, n)
    opp_rank    = rng.integers(1, 200, n)
    rank_ratio  = rank / opp_rank
    log_rank_diff = np.sign(rank - opp_rank) * np.log1p(np.abs(rank - opp_rank))
    is_underdog = (rank > opp_rank).astype(int)
    round_num   = rng.integers(1, 8, n)
    best_of     = rng.choice([3, 5], n)
    ctfi        = rng.integers(0, 20, n)

    # NLP features (many missing — as in real data)
    has_transcript = rng.random(n) < 0.45  # ~45% have a transcript
    sentiment_polarity = np.where(has_transcript, rng.uniform(-1, 1, n), np.nan)
    fatigue_total      = np.where(has_transcript, rng.integers(0, 12, n).astype(float), np.nan)
    fatigue_density    = np.where(has_transcript, rng.uniform(0, 3, n), np.nan)
    first_person_rate  = np.where(has_transcript, rng.uniform(0.05, 0.25, n), np.nan)
    negation_rate      = np.where(has_transcript, rng.uniform(0.01, 0.10, n), np.nan)
    llm_is_fatigued    = np.where(has_transcript, rng.choice([0, 1], n, p=[0.7, 0.3]).astype(float), np.nan)

    # Target: upset probability influenced by rank gap + fatigue
    log_odds = (
        0.5 * (rank / 100)
        - 0.8 * (opp_rank / 100)
        - 0.1 * log_rank_diff
        + 0.05 * ctfi
        + np.where(np.isnan(fatigue_total), 0, 0.08 * fatigue_total)
        + np.where(np.isnan(sentiment_polarity), 0, -0.15 * sentiment_polarity)
        + rng.normal(0, 0.4, n)
    )
    prob  = 1 / (1 + np.exp(-log_odds))
    upset = (rng.random(n) < prob).astype(int)

    rank_bin_vals = pd.cut(
        rank,
        bins=[0, 10, 30, 100, np.inf],
        labels=["top10", "top30", "top100", "outside100"],
    )

    return pd.DataFrame({
        "rank": rank, "opp_rank": opp_rank, "rank_ratio": rank_ratio,
        "log_rank_diff": log_rank_diff, "is_underdog": is_underdog,
        "round_num": round_num, "best_of": best_of, "ctfi": ctfi,
        "sentiment_polarity": sentiment_polarity,
        "fatigue_total": fatigue_total,
        "fatigue_word_density": fatigue_density,
        "fatigue_physical": np.where(has_transcript, rng.integers(0, 5, n).astype(float), np.nan),
        "fatigue_mental":   np.where(has_transcript, rng.integers(0, 3, n).astype(float), np.nan),
        "fatigue_schedule": np.where(has_transcript, rng.integers(0, 4, n).astype(float), np.nan),
        "fatigue_injury":   np.where(has_transcript, rng.integers(0, 3, n).astype(float), np.nan),
        "fatigue_motivation": np.where(has_transcript, rng.integers(0, 2, n).astype(float), np.nan),
        "first_person_rate": first_person_rate,
        "negation_rate": negation_rate,
        "llm_is_fatigued": llm_is_fatigued,
        "rank_bin": rank_bin_vals,
        "upset": upset,
    })


# preprocessing 

def build_preprocessor(feature_cols: list[str], categorical_cols: list[str]):
    """
    Build a ColumnTransformer that:
      - Imputes missing numerics with median
      - Standard-scales numerics
      - Ordinal-encodes categoricals (with imputation)
    """
    numeric_cols = [c for c in feature_cols if c not in categorical_cols]

    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])

    steps = [("num", numeric_transformer, numeric_cols)]
    if categorical_cols:
        steps.append(("cat", categorical_transformer, categorical_cols))

    return ColumnTransformer(steps, remainder="drop")


# model pipeline 

def build_pipeline(feature_cols: list[str], categorical_cols: list[str]) -> Pipeline:
    preprocessor = build_preprocessor(feature_cols, categorical_cols)
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=5,
        class_weight="balanced",  # handles class imbalance
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([
        ("prep",  preprocessor),
        ("model", rf),
    ])


# time-based train/test split 

def time_split(df: pd.DataFrame, test_frac: float = 0.20):
    """
    Sort by match date (or index as proxy) and use the last `test_frac`
    of rows as the holdout test set.
    """
    n_test = int(len(df) * test_frac)
    train  = df.iloc[:-n_test].copy()
    test   = df.iloc[-n_test:].copy()
    print(f"Train: {len(train):,} rows | Test: {len(test):,} rows")
    return train, test


# hyperparameter search 

PARAM_GRID = {
    "model__n_estimators":   [200, 400],
    "model__max_depth":      [None, 8, 15],
    "model__min_samples_leaf": [3, 7],
    "model__max_features":   ["sqrt", 0.5],
}


def tune_model(pipeline: Pipeline, X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    """
    Run a grid search with time-series-aware cross-validation.
    Returns the best estimator fitted on the full training set.
    """
    tscv = TimeSeriesSplit(n_splits=4)
    gs   = GridSearchCV(
        pipeline,
        PARAM_GRID,
        cv=tscv,
        scoring="roc_auc",
        n_jobs=-1,
        verbose=0,
        refit=True,
    )
    gs.fit(X_train, y_train)
    print(f"\nBest CV ROC-AUC : {gs.best_score_:.4f}")
    print(f"Best params     : {gs.best_params_}")
    return gs.best_estimator_


# evaluation

def evaluate(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series,
             label: str = "Model") -> dict:
    """Print classification metrics and return them as a dict."""
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    auc    = roc_auc_score(y_test, y_prob)
    ap     = average_precision_score(y_test, y_prob)

    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  ROC-AUC           : {auc:.4f}")
    print(f"  Average Precision : {ap:.4f}")
    print(f"\n  Classification report (threshold=0.5):")
    print(classification_report(y_test, y_pred, target_names=["No upset", "Upset"]))

    return {"label": label, "roc_auc": auc, "avg_precision": ap,
            "y_prob": y_prob, "y_pred": y_pred}


# plots

def plot_roc_comparison(results_a: dict, results_b: dict,
                        y_test: pd.Series) -> None:
    """Plot ROC curves for both models side by side."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, result in zip(axes, [results_a, results_b]):
        fpr, tpr, _ = roc_curve(y_test, result["y_prob"])
        ax.plot(fpr, tpr, lw=2, label=f"AUC = {result['roc_auc']:.3f}")
        ax.plot([0, 1], [0, 1], "k--", lw=1)
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title(result["label"])
        ax.legend(loc="lower right")
        ax.grid(alpha=0.3)

    plt.suptitle("ROC curves: traditional vs full (NLP) model", fontsize=13)
    plt.tight_layout()
    out = f"{PLOTS_DIR}/roc_comparison.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  ROC plot saved → {out}")


def plot_confusion_matrices(results_a: dict, results_b: dict,
                            y_test: pd.Series) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, result in zip(axes, [results_a, results_b]):
        cm  = confusion_matrix(y_test, result["y_pred"])
        cmd = ConfusionMatrixDisplay(cm, display_labels=["No upset", "Upset"])
        cmd.plot(ax=ax, colorbar=False)
        ax.set_title(result["label"])
    plt.suptitle("Confusion matrices", fontsize=13)
    plt.tight_layout()
    out = f"{PLOTS_DIR}/confusion_matrices.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Confusion matrix plot saved → {out}")


def plot_shap_importance(model: Pipeline, X_test: pd.DataFrame,
                         feature_names: list[str], label: str) -> None:
    """SHAP summary bar plot for the full model."""
    if not SHAP_AVAILABLE:
        return

    # Extract the preprocessed matrix
    X_transformed = model.named_steps["prep"].transform(X_test)

    rf_model = model.named_steps["model"]
    explainer = shap.TreeExplainer(rf_model)
    shap_vals = explainer.shap_values(X_transformed)

    # shap_values returns [neg_class, pos_class] for binary RF
    sv = shap_vals[1] if isinstance(shap_vals, list) else shap_vals

    # Map transformed feature names back (numeric first, then categorical)
    prep = model.named_steps["prep"]
    num_names = prep.transformers_[0][2]                      # numeric cols
    cat_names = prep.transformers_[1][2] if len(prep.transformers_) > 1 else []
    all_names = num_names + list(cat_names)

    fig, ax = plt.subplots(figsize=(9, 7))
    mean_abs = np.abs(sv).mean(axis=0)
    sorted_idx = np.argsort(mean_abs)[::-1][:20]

    ax.barh(
        [all_names[i] if i < len(all_names) else f"feat_{i}" for i in sorted_idx[::-1]],
        mean_abs[sorted_idx[::-1]],
        color="#5C5CE0",
        edgecolor="none",
    )
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title(f"SHAP feature importance — {label}")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    out = f"{PLOTS_DIR}/shap_importance.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  SHAP plot saved → {out}")


def plot_upset_rate_by_fatigue(df: pd.DataFrame) -> None:
    """Bar chart: upset rate split by fatigue quartile (hypothesis check)."""
    if "fatigue_total" not in df.columns or df["fatigue_total"].isna().all():
        return

    df_sub = df[df["fatigue_total"].notna()].copy()
    df_sub["fatigue_quartile"] = pd.qcut(
        df_sub["fatigue_total"], q=4,
        labels=["Low (Q1)", "Mid-low (Q2)", "Mid-high (Q3)", "High (Q4)"],
        duplicates="drop",
    )

    upset_by_quartile = (
        df_sub.groupby("fatigue_quartile", observed=True)["upset"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "upset_rate", "count": "n"})
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        upset_by_quartile.index,
        upset_by_quartile["upset_rate"] * 100,
        color=["#9FE1CB", "#5DCAA5", "#1D9E75", "#0F6E56"],
        edgecolor="none",
    )
    for bar, (_, row) in zip(bars, upset_by_quartile.iterrows()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"n={row['n']:.0f}",
            ha="center", va="bottom", fontsize=9, color="#333",
        )
    ax.set_xlabel("Fatigue keyword quartile")
    ax.set_ylabel("Upset rate (%)")
    ax.set_title("Upset rate by pre-match fatigue language level\n(hypothesis check)")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = f"{PLOTS_DIR}/upset_rate_by_fatigue.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Hypothesis plot saved → {out}")


# main 

def main() -> None:
    print("=" * 60)
    print("  PART 5 — Model Training & Evaluation")
    print("=" * 60)

    # 1. Load data
    df = load_features(FEATURES_CSV)
    df = df.dropna(subset=[TARGET])

    # 2. Time-based split
    train, test = time_split(df)
    y_train = train[TARGET]
    y_test  = test[TARGET]

    # model A: Traditional features only 
    print("\n[A] Traditional model (rank + CTFI, no NLP)")
    trad_cols = [c for c in TRADITIONAL_FEATURES if c in df.columns]
    cat_cols_a = [c for c in CATEGORICAL_FEATURES if c in trad_cols]

    pipe_a = build_pipeline(trad_cols, cat_cols_a)
    pipe_a = tune_model(pipe_a, train[trad_cols], y_train)
    res_a  = evaluate(pipe_a, test[trad_cols], y_test, label="Traditional (no NLP)")

    # model b: full features 
    #  traditional + NLP
    print("\n[B] Full model (rank + CTFI + NLP transcript features)")
    all_features = TRADITIONAL_FEATURES + NLP_FEATURES
    full_cols    = [c for c in all_features if c in df.columns]
    cat_cols_b   = [c for c in CATEGORICAL_FEATURES if c in full_cols]

    pipe_b = build_pipeline(full_cols, cat_cols_b)
    pipe_b = tune_model(pipe_b, train[full_cols], y_train)
    res_b  = evaluate(pipe_b, test[full_cols], y_test, label="Full model (with NLP)")

    # comparison
    print("\n── Model comparison ──────────────────────────────")
    print(f"  Traditional  ROC-AUC : {res_a['roc_auc']:.4f}")
    print(f"  Full (NLP)   ROC-AUC : {res_b['roc_auc']:.4f}")
    delta = res_b['roc_auc'] - res_a['roc_auc']
    print(f"  Delta (NLP uplift)   : {delta:+.4f}")
    print("──────────────────────────────────────────────────")

    # plots
    print("\nGenerating plots …")
    plot_roc_comparison(res_a, res_b, y_test)
    plot_confusion_matrices(res_a, res_b, y_test)
    plot_shap_importance(pipe_b, test[full_cols], full_cols, label="Full model")
    plot_upset_rate_by_fatigue(df)

    # save model


    save_package = {
        "model_b":          pipe_b,
        "model_a":          pipe_a,
        "traditional_cols": trad_cols,
        "full_cols":        full_cols,
        "results_a":        {k: v for k, v in res_a.items() if k not in ("y_prob", "y_pred")},
        "results_b":        {k: v for k, v in res_b.items() if k not in ("y_prob", "y_pred")},
    }
    joblib.dump(save_package, MODEL_OUT)
    print(f"\nModel saved to: {MODEL_OUT}")
    print("\nPart 5 complete! 🎾")
    print("\nOutputs:")
    print(f"  {MODEL_OUT}                — pickled model")
    print(f"  roc_comparison.png         — ROC-AUC comparison plot")
    print(f"  confusion_matrices.png     — confusion matrices")
    print(f"  shap_importance.png        — SHAP feature importances")
    print(f"  upset_rate_by_fatigue.png  — hypothesis check plot")


# infrence helper

def predict_upset_probability(
    model_path: str = MODEL_OUT,
    player_rank: int = 45,
    opponent_rank: int = 12,
    ctfi: float = 8.0,
    sentiment_polarity: float = -0.3,
    fatigue_total: int = 5,
    round_num: int = 4,
    best_of: int = 5,
) -> float:
    """
    Convenience function to get an upset probability for a single match.
    Use after training.
    """
    pkg  = joblib.load(model_path)
    pipe = pkg["model_b"]
    cols = pkg["full_cols"]

    row = {
        "rank": player_rank, "opp_rank": opponent_rank,
        "rank_ratio": player_rank / opponent_rank,
        "log_rank_diff": np.sign(player_rank - opponent_rank) * np.log1p(abs(player_rank - opponent_rank)),
        "is_underdog": int(player_rank > opponent_rank),
        "round_num": round_num, "best_of": best_of, "ctfi": ctfi,
        "rank_bin": "top100" if player_rank <= 100 else "outside100",
        "sentiment_polarity": sentiment_polarity,
        "fatigue_total": fatigue_total,
        "fatigue_word_density": fatigue_total / 100,
        "fatigue_physical": max(0, fatigue_total - 2),
        "fatigue_mental": max(0, fatigue_total - 3),
        "fatigue_schedule": max(0, fatigue_total - 4),
        "fatigue_injury": 0, "fatigue_motivation": 0,
        "first_person_rate": 0.15, "negation_rate": 0.05,
        "llm_is_fatigued": 0.5,
    }
    df = pd.DataFrame([row])[[c for c in cols if c in row]]
    prob = pipe.predict_proba(df)[0, 1]
    print(f"\nUpset probability (rank {player_rank} vs rank {opponent_rank}): {prob:.3f}")
    return prob


if __name__ == "__main__":
    main()