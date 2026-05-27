# Barangay Relief Pack Optimizer

A desktop application that helps barangay disaster-response officers make two
decisions under time pressure after a typhoon: **what to pack into each relief
bag**, and **which families should receive bags first** when supply is limited.

The project is the final deliverable for **CMSC 142** (Analysis of Algorithms).

**Team:** Kate Capadocia, RJ Michelle Jayme, Shaina Marie Talisay

---

## Algorithms

The system runs two algorithms in sequence.

**Module 1 — 0/1 Knapsack via Dynamic Programming** (`knapsack.py`)
Given a list of relief items with `(weight_kg, benefit, quantity)` and a bag
weight capacity `W`, it builds a 2D DP table and backtracks to recover the
optimal subset of items that maximizes total benefit without exceeding `W`.
Item weights are scaled to 0.1 kg precision so the DP table works in integer
units. Result is exactly optimal — not an approximation.

- Time: `O(n × W)`
- Space: `O(n × W)`

**Module 2 — Greedy Priority Assignment** (`priority.py`)
Each registered family is scored using the formula

```
priority_score = (family_size × 2) + (vulnerable_count × 5) + (damage_level × 3)
```

Families are sorted in descending order of score. Ties are broken first by
larger household size, then by earlier registration order. The greedy step
assigns one optimized bag to each family in ranked order until supply is
exhausted.

- Time: `O(F log F)` for the sort, `O(F)` for the pass.

**Optional — Decision-Tree Vulnerability Scorer** (`ml_scorer.py`)
A scikit-learn `DecisionTreeClassifier` trained on synthetic DSWD-aligned data
predicts a risk label (high / medium / low) for each family. The label is
converted to a numeric `ml_score` and blended with the formula score as
`final_score = 0.6 × formula_score + 0.4 × ml_score`. **This module is an
enhancement layered on top of the proposed algorithm — it is not in the
original proposal.** It can be toggled off in the Family Registry screen.

---

## Project structure

```
CMSC142_finalproj/
├── app.py             # Tkinter GUI — entry point
├── models.py          # ReliefItem, Family, AssignmentResult, OperationSummary
├── knapsack.py        # Module 1 — 0/1 Knapsack DP
├── priority.py        # Module 2 — Greedy assignment
├── ml_scorer.py       # Optional Decision Tree classifier
├── ml_model.pkl       # Trained model (auto-generated on first run)
├── utils.py           # Input validation, supply warnings, TXT/CSV export
├── requirements.txt   # Third-party deps (numpy, scikit-learn)
└── README.md
```

---

## Requirements

- **Python 3.9 or newer** (PEP 585 generic type hints are used)
- **tkinter** — ships with most Python distributions. On Debian/Ubuntu:
  `sudo apt install python3-tk`
- The pip packages in `requirements.txt` (only needed if you keep the ML
  module enabled)

---

## Installation

```bash
git clone <repo-url>
cd CMSC142_finalproj
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Running

```bash
python app.py
```

On the first launch, the ML model is trained automatically and saved to
`ml_model.pkl`. Subsequent launches load the cached model.

You can also run the algorithm modules directly for a quick sanity check:

```bash
python knapsack.py    # prints an optimal bag for sample inventory
python priority.py    # prints a ranked assignment for sample families
python ml_scorer.py   # trains the model and prints validation metrics
```

---

## Using the app

The GUI has four screens, accessed from the left sidebar.

1. **Inventory Setup** — Enter the disaster name and barangay (sidebar
   fields), the maximum bag weight in kg, and the number of bags available.
   Add or edit rows in the relief items table (name, weight, benefit 1–10,
   quantity), then click **Optimize Bag** to run the DP.
2. **Family Registry** — Add each affected family with size, vulnerable
   member count, and damage level (1 minor, 2 partial, 3 total loss).
   Toggle ML scoring on or off. Click **Generate Assignment** to run the
   greedy step.
3. **Results** — Shows the optimized bag manifest on the left, a ranked
   assignment table on the right, and summary stats at the top. Includes a
   **View DP Table** button that opens the full DP table used by Module 1,
   and **Export TXT / CSV** buttons for field use.

Click **New Disaster** in the sidebar to clear all data.

---

## Notes for the final report

- **Module 1 is provably optimal.** The DP recurrence
  `dp[i][w] = max(dp[i-1][w], benefit[i] + dp[i-1][w - weight[i]])`
  evaluates every feasible inclusion/exclusion combination implicitly, so the
  result is guaranteed to be the best possible packing within the weight
  limit.
- **Module 2 is locally optimal but not globally optimal.** Greedy priority
  assignment never skips a higher-priority family in favor of a lower one,
  which is the property that matters in a humanitarian context. The trade-off
  is intentional and is justified in the proposal under section 3(a).
- **Practicality.** With `n = 6` item types and capacity discretized to 0.1
  kg (so `W ≈ 100` for a 10 kg bag), and at most a few hundred families per
  barangay, the system runs in milliseconds on the kind of low-end hardware
  realistically available to a barangay office, and works offline.
