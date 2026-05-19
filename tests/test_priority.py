"""
Tests for Module 2 — Greedy Priority Assignment (priority.py)
==============================================================
Proves the proposal's claims:
  • priority_score = (size × 2) + (vulnerable × 5) + (damage × 3)
  • Families are served in descending priority order
  • Tie-breaking: larger size first, then earlier registration_order
  • "No higher-priority family is ever skipped in favor of a lower-priority one"
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from models import Family, ReliefItem
from priority import compute_scores, rank_families, assign_bags


def make_bag():
    """A fixed sample bag used as the assignment payload."""
    return (
        [ReliefItem("Rice", 3.0, 9, 50), ReliefItem("Water", 2.0, 8, 60)],
        5.0,   # bag_weight
        17,    # bag_benefit
    )


# ── Formula score ─────────────────────────────────────────────────────────────
class TestFormulaScore(unittest.TestCase):

    def test_proposal_formula(self):
        # priority = size*2 + vuln*5 + damage*3
        cases = [
            (Family("F1", 5, 2, 3, 1),  5*2 + 2*5 + 3*3),   # 29
            (Family("F2", 1, 0, 1, 2),  1*2 + 0*5 + 1*3),   # 5
            (Family("F3", 10, 5, 3, 3), 10*2 + 5*5 + 3*3),  # 54
            (Family("F4", 3, 0, 2, 4),  3*2 + 0*5 + 2*3),   # 12
        ]
        for fam, expected in cases:
            with self.subTest(fam=fam.family_id):
                self.assertEqual(fam.compute_formula_score(), expected)
                self.assertEqual(fam.formula_score, expected)


# ── Ranking ───────────────────────────────────────────────────────────────────
class TestRanking(unittest.TestCase):

    def test_higher_score_comes_first(self):
        fams = [
            Family("F-A", 2, 0, 1, 1),   # score 7
            Family("F-B", 5, 3, 3, 2),   # score 34
            Family("F-C", 3, 1, 2, 3),   # score 17
        ]
        compute_scores(fams)
        ranked = rank_families(fams)
        self.assertEqual([f.family_id for f in ranked], ["F-B", "F-C", "F-A"])

    def test_tie_broken_by_larger_size(self):
        # Both families have score 12 — F-LARGE (size 4) should rank before F-SMALL (size 2).
        # F-LARGE: 4*2 + 0*5 + 0*3? No — pick values that genuinely tie.
        # size 4, vuln 0, dmg 0? dmg must be 1-3. Use size=3,vuln=0,dmg=2 (score 12)
        # vs size=2,vuln=1,dmg=1 (score 12).
        f_large = Family("F-LARGE", 3, 0, 2, 1)  # 6+0+6 = 12
        f_small = Family("F-SMALL", 2, 1, 1, 2)  # 4+5+3 = 12
        compute_scores([f_large, f_small])
        self.assertEqual(f_large.formula_score, f_small.formula_score)
        ranked = rank_families([f_small, f_large])
        self.assertEqual(ranked[0].family_id, "F-LARGE")

    def test_tie_broken_by_registration_order_when_size_equal(self):
        # Same score AND same size — earlier registration_order wins.
        f_early = Family("F-EARLY", 3, 0, 2, 1)  # score 12, size 3, reg 1
        f_late  = Family("F-LATE",  3, 0, 2, 5)  # score 12, size 3, reg 5
        compute_scores([f_early, f_late])
        ranked = rank_families([f_late, f_early])  # input order shouldn't matter
        self.assertEqual(ranked[0].family_id, "F-EARLY")


# ── Assignment ────────────────────────────────────────────────────────────────
class TestAssignment(unittest.TestCase):

    def test_supply_exhaustion_unserved_marked(self):
        fams = [
            Family("F1", 5, 2, 3, 1),  # 29
            Family("F2", 3, 0, 2, 2),  # 12
            Family("F3", 4, 3, 3, 3),  # 32
            Family("F4", 2, 1, 1, 4),  # 12
        ]
        bag, wt, ben = make_bag()
        summary = assign_bags(fams, bag, wt, ben, supply=2)

        self.assertEqual(summary.total_families, 4)
        self.assertEqual(summary.served, 2)
        self.assertEqual(summary.unserved, 2)
        # Top 2 should be served, bottom 2 should not
        served_ids   = [a.family.family_id for a in summary.assignments if a.served]
        unserved_ids = [a.family.family_id for a in summary.assignments if not a.served]
        self.assertEqual(served_ids,   ["F3", "F1"])
        self.assertEqual(unserved_ids, ["F2", "F4"])  # tie-broken by size

    def test_no_higher_priority_skipped(self):
        """The proposal's key correctness claim for Module 2:
        no higher-priority family is ever skipped in favor of a lower-priority one."""
        fams = [
            Family("A", 4, 2, 2, 1),
            Family("B", 1, 0, 1, 2),
            Family("C", 6, 4, 3, 3),
            Family("D", 2, 1, 1, 4),
            Family("E", 3, 3, 2, 5),
        ]
        bag, wt, ben = make_bag()
        summary = assign_bags(fams, bag, wt, ben, supply=3)

        # Walk the assignment list (already in ranked order) and check the invariant:
        # once we see an UNSERVED family, every family after it must also be unserved
        # (because they are equal or lower priority).
        seen_unserved = False
        for a in summary.assignments:
            if not a.served:
                seen_unserved = True
            elif seen_unserved:
                self.fail(
                    f"Family {a.family.family_id} (score {a.family.final_score}) was "
                    f"SERVED after an unserved higher-priority family — proposal claim violated."
                )

    def test_supply_zero_serves_nobody(self):
        fams = [Family("F1", 5, 2, 3, 1)]
        bag, wt, ben = make_bag()
        summary = assign_bags(fams, bag, wt, ben, supply=0)
        self.assertEqual(summary.served, 0)
        self.assertEqual(summary.unserved, 1)
        self.assertFalse(summary.assignments[0].served)

    def test_supply_exceeds_families_everyone_served(self):
        fams = [
            Family("F1", 5, 2, 3, 1),
            Family("F2", 3, 0, 2, 2),
        ]
        bag, wt, ben = make_bag()
        summary = assign_bags(fams, bag, wt, ben, supply=10)
        self.assertEqual(summary.served, 2)
        self.assertEqual(summary.unserved, 0)

    def test_total_benefit_delivered(self):
        fams = [
            Family("F1", 5, 2, 3, 1),
            Family("F2", 3, 0, 2, 2),
            Family("F3", 4, 3, 3, 3),
        ]
        bag, wt, ben = make_bag()
        # bag_benefit = 17, supply = 2 → 17 * 2 = 34
        summary = assign_bags(fams, bag, wt, ben, supply=2)
        self.assertEqual(summary.total_benefit_delivered, ben * 2)

    def test_unserved_bag_is_empty(self):
        """Unserved families should not be credited with a bag."""
        fams = [Family("F1", 5, 2, 3, 1), Family("F2", 3, 0, 2, 2)]
        bag, wt, ben = make_bag()
        summary = assign_bags(fams, bag, wt, ben, supply=1)
        unserved = [a for a in summary.assignments if not a.served][0]
        self.assertEqual(unserved.bag_contents, [])
        self.assertEqual(unserved.bag_weight, 0.0)
        self.assertEqual(unserved.bag_benefit, 0)


if __name__ == "__main__":
    unittest.main()
