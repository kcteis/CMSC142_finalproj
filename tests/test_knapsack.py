"""
Tests for Module 1 — 0/1 Knapsack DP (knapsack.py)
====================================================
These tests prove the optimality claim from the proposal:
"Module 1 produces an exact optimal solution, not an approximation."

Strongest test: `test_dp_matches_bruteforce_on_random_instances`
  — generates 60 random small instances and compares DP output against a
    brute-force 2^n exhaustive search. If they ever disagree, DP is wrong.
"""

import itertools
import os
import random
import sys
import unittest

# Make the project root importable when running `python -m unittest discover`
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from knapsack import optimize_bag, PRECISION
from models import ReliefItem


# ── Brute-force reference solver ──────────────────────────────────────────────
def brute_force_optimum(items, capacity_kg):
    """O(2^n) reference solver — only correct for small n. Returns (best_benefit, best_weight)."""
    best_benefit = 0
    best_weight = 0.0
    n = len(items)
    for mask in range(1 << n):
        w = 0.0
        b = 0
        for i in range(n):
            if mask & (1 << i):
                w += items[i].weight_kg
                b += items[i].benefit
        # Allow tiny floating slack to match the DP's discretization
        if w <= capacity_kg + 1e-9 and b > best_benefit:
            best_benefit = b
            best_weight = w
    return best_benefit, best_weight


# ── Tests ─────────────────────────────────────────────────────────────────────
class TestKnapsackEdgeCases(unittest.TestCase):

    def test_empty_items_returns_empty_bag(self):
        sel, wt, ben = optimize_bag([], capacity_kg=10.0)
        self.assertEqual(sel, [])
        self.assertEqual(wt, 0)
        self.assertEqual(ben, 0)

    def test_zero_capacity_returns_empty_bag(self):
        items = [ReliefItem("Rice", 3.0, 9, 50)]
        sel, wt, ben = optimize_bag(items, capacity_kg=0.0)
        self.assertEqual(sel, [])
        self.assertEqual(wt, 0)
        self.assertEqual(ben, 0)

    def test_single_item_that_fits(self):
        items = [ReliefItem("Medicine", 0.5, 10, 40)]
        sel, wt, ben = optimize_bag(items, capacity_kg=1.0)
        self.assertEqual(len(sel), 1)
        self.assertEqual(sel[0].name, "Medicine")
        self.assertEqual(ben, 10)

    def test_single_item_too_heavy_excluded(self):
        items = [ReliefItem("Rice", 5.0, 9, 50)]
        sel, wt, ben = optimize_bag(items, capacity_kg=2.0)
        self.assertEqual(sel, [])
        self.assertEqual(ben, 0)


class TestKnapsackKnownAnswers(unittest.TestCase):

    def test_proposal_sample_inventory_capacity_10kg(self):
        """At W=10 kg, total weight of the 6 sample items is 9 kg — take everything."""
        items = [
            ReliefItem("Rice",         3.0, 9, 50),
            ReliefItem("Canned goods", 1.5, 7, 80),
            ReliefItem("Water",        2.0, 8, 60),
            ReliefItem("Medicine",     0.5,10, 40),
            ReliefItem("Blanket",      1.5, 5, 30),
            ReliefItem("Hygiene kit",  0.5, 6, 50),
        ]
        sel, wt, ben = optimize_bag(items, capacity_kg=10.0)
        self.assertEqual(len(sel), 6)
        self.assertAlmostEqual(wt, 9.0, places=2)
        self.assertEqual(ben, 6 + 5 + 10 + 8 + 7 + 9)  # 45

    def test_must_choose_under_tight_capacity(self):
        """Capacity forces the DP to drop the worst-ratio items."""
        items = [
            ReliefItem("Rice",     3.0, 9, 50),   # ratio 3.0
            ReliefItem("Water",    2.0, 8, 60),   # ratio 4.0
            ReliefItem("Medicine", 0.5,10, 40),   # ratio 20.0 — best
            ReliefItem("Blanket",  1.5, 5, 30),   # ratio 3.33
        ]
        sel, wt, ben = optimize_bag(items, capacity_kg=2.5)
        # Brute force the optimum and verify DP matches
        expected_ben, _ = brute_force_optimum(items, 2.5)
        self.assertEqual(ben, expected_ben)
        self.assertLessEqual(round(wt, 2), 2.5)

    def test_classic_textbook_instance(self):
        """Classic CLRS-style instance: items (1,1), (3,4), (4,5), (5,7) at W=7.
        Optimum is items {(3,4),(4,5)} → benefit 9 at weight 7."""
        items = [
            ReliefItem("A", 1.0, 1, 1),
            ReliefItem("B", 3.0, 4, 1),
            ReliefItem("C", 4.0, 5, 1),
            ReliefItem("D", 5.0, 7, 1),
        ]
        sel, wt, ben = optimize_bag(items, capacity_kg=7.0)
        self.assertEqual(ben, 9)
        self.assertAlmostEqual(wt, 7.0, places=2)


class TestKnapsackBacktracking(unittest.TestCase):

    def test_returned_items_consistent_with_totals(self):
        """The items returned must actually sum to the reported weight and benefit."""
        items = [
            ReliefItem("Rice",         3.0, 9, 1),
            ReliefItem("Canned goods", 1.5, 7, 1),
            ReliefItem("Water",        2.0, 8, 1),
            ReliefItem("Medicine",     0.5,10, 1),
            ReliefItem("Blanket",      1.5, 5, 1),
        ]
        sel, wt, ben = optimize_bag(items, capacity_kg=5.0)
        actual_weight  = sum(it.weight_kg for it in sel)
        actual_benefit = sum(it.benefit  for it in sel)
        self.assertAlmostEqual(actual_weight, wt, places=2)
        self.assertEqual(actual_benefit, ben)

    def test_returned_items_fit_within_capacity(self):
        for cap in [0.5, 1.0, 2.5, 5.0, 7.5, 10.0]:
            with self.subTest(cap=cap):
                items = [
                    ReliefItem("Rice",     3.0, 9, 1),
                    ReliefItem("Water",    2.0, 8, 1),
                    ReliefItem("Medicine", 0.5,10, 1),
                    ReliefItem("Blanket",  1.5, 5, 1),
                ]
                sel, wt, ben = optimize_bag(items, capacity_kg=cap)
                self.assertLessEqual(round(wt, 2), cap + 1e-9)


class TestKnapsackOptimalityVsBruteForce(unittest.TestCase):
    """The headline test. If DP ever disagrees with brute-force on any instance,
    the optimality claim from section 3(a) of the proposal is false."""

    def test_dp_matches_bruteforce_on_random_instances(self):
        rng = random.Random(20260519)  # deterministic
        n_instances = 60
        for trial in range(n_instances):
            n = rng.randint(1, 8)
            # Weights are multiples of 0.1 to align with PRECISION=10
            items = [
                ReliefItem(
                    name=f"I{i}",
                    weight_kg=round(rng.uniform(0.1, 5.0), 1),
                    benefit=rng.randint(1, 20),
                    quantity=1,
                )
                for i in range(n)
            ]
            capacity = round(rng.uniform(0.5, 8.0), 1)

            _, dp_wt, dp_ben    = optimize_bag(items, capacity)
            brute_ben, brute_wt = brute_force_optimum(items, capacity)

            with self.subTest(trial=trial, n=n, W=capacity):
                self.assertEqual(
                    dp_ben, brute_ben,
                    msg=f"DP benefit {dp_ben} != brute-force {brute_ben} "
                        f"on instance: items={items}, W={capacity}"
                )


if __name__ == "__main__":
    unittest.main()
