"""
Module 3 — ML Vulnerability Risk Classifier
---------------------------------------------
Trains a Decision Tree on synthetic DSWD-aligned data to predict
a vulnerability risk label (high / medium / low) for each family.

The predicted label is converted to a numeric score and blended
with the formula score inside priority.py:
    final_score = 0.6 × formula_score + 0.4 × ml_score

This means the ML does NOT replace the knapsack or greedy —
it improves the INPUT to the greedy ranker automatically.

Member responsibilities
-----------------------
M1  → this file (train, predict)
"""

import os
import pickle
import numpy as np
from typing import List, Tuple
from models import Family

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model.pkl")

LABEL_SCORE = {"high": 40, "medium": 25, "low": 10}
FEATURES    = ["family_size", "vulnerable_count", "damage_level"]


# ── Synthetic training data ───────────────────────────────────────────────────

def _generate_data(n: int = 800, seed: int = 42) -> Tuple[np.ndarray, List[str]]:
    """
    Simulate realistic DSWD prioritization patterns:
      high   → vulnerable_count >= 2 AND damage_level == 3, OR
               vulnerable_count >= 3, OR
               damage_level == 3 AND family_size >= 5
      low    → damage_level == 1 AND vulnerable_count == 0
      medium → everything else
    """
    rng  = np.random.default_rng(seed)
    size = rng.integers(1, 13, n)
    vuln = np.minimum(rng.integers(0, 7, n), size)
    dmg  = rng.integers(1, 4, n)

    labels = []
    for s, v, d in zip(size, vuln, dmg):
        if (v >= 2 and d == 3) or v >= 3 or (d == 3 and s >= 5):
            labels.append("high")
        elif d == 1 and v == 0:
            labels.append("low")
        else:
            labels.append("medium")

    return np.column_stack([size, vuln, dmg]), labels


# ── Train ─────────────────────────────────────────────────────────────────────

def train_model(verbose: bool = True) -> object:
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score

    X, y = _generate_data()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = DecisionTreeClassifier(max_depth=6, random_state=42)
    model.fit(X_tr, y_tr)

    if verbose:
        acc = accuracy_score(y_te, model.predict(X_te))
        print(f"\n{'ML Validation':=^50}")
        print(f"Test accuracy: {acc:.2%}")
        print(classification_report(y_te, model.predict(X_te),
                                    target_names=["high", "low", "medium"]))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    return model


# ── Load ──────────────────────────────────────────────────────────────────────

def _load() -> object:
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return train_model(verbose=False)


# ── Predict ───────────────────────────────────────────────────────────────────

def score_families(families: List[Family]) -> List[Family]:
    """
    Predict ML risk label for each family and populate family.ml_score.
    Called automatically by priority.assign_bags() when use_ml=True.
    """
    if not families:
        return families
    model = _load()
    X = np.array([[f.size, f.vulnerable_count, f.damage_level] for f in families])
    labels = model.predict(X)
    for fam, lbl in zip(families, labels):
        fam.ml_score = LABEL_SCORE[lbl]
    return families


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    train_model(verbose=True)
    test = [
        Family("F-001", 7, 3, 3, 1),
        Family("F-002", 2, 0, 1, 2),
        Family("F-003", 4, 2, 2, 3),
    ]
    scored = score_families(test)
    print(f"\n{'Sample predictions':=^40}")
    for f in scored:
        f.compute_formula_score()
        print(f"  {f.family_id}  formula={f.formula_score:.0f}  ml={f.ml_score:.0f}")
