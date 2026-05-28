"""
Module 2 — Greedy Priority Assignment
---------------------------------------
Ranks families by priority score (formula),
then assigns bags in descending order until supply runs out.

Tie-breaking: higher size → earlier registration_order
"""

from typing import List
from models import Family, ReliefItem, AssignmentResult, OperationSummary


def compute_scores(families: List[Family]) -> List[Family]:
    for f in families:
        f.compute_formula_score()
        f.final_score = f.formula_score
    return families


def rank_families(families: List[Family]) -> List[Family]:
    return sorted(
        families,
        key=lambda f: (-f.final_score, -f.size, f.registration_order),
    )


def assign_bags(
    families: List[Family],
    bag_contents: List[ReliefItem],
    bag_weight: float,
    bag_benefit: int,
    supply: int,
) -> OperationSummary:
    families = compute_scores(families)
    ranked   = rank_families(families)

    assignments = []
    bags_left   = supply

    for family in ranked:
        served = bags_left > 0
        if served:
            bags_left -= 1
        assignments.append(AssignmentResult(
            family=family,
            bag_contents=bag_contents if served else [],
            bag_weight=bag_weight if served else 0.0,
            bag_benefit=bag_benefit if served else 0,
            served=served,
        ))

    served_count  = sum(1 for a in assignments if a.served)
    total_benefit = sum(a.bag_benefit for a in assignments)

    return OperationSummary(
        total_families=len(families),
        served=served_count,
        unserved=len(families) - served_count,
        total_benefit_delivered=total_benefit,
        bag_contents=bag_contents,
        bag_weight=bag_weight,
        bag_benefit=bag_benefit,
        assignments=assignments,
    )


if __name__ == "__main__":
    from models import Family, ReliefItem
    fams = [
        Family("F-001", 5, 2, 3, 1),
        Family("F-002", 3, 0, 2, 2),
        Family("F-003", 4, 3, 3, 3),
        Family("F-004", 2, 1, 1, 4),
    ]
    bag = [ReliefItem("Rice", 3.0, 9, 50), ReliefItem("Water", 2.0, 8, 60)]
    s = assign_bags(fams, bag, 5.0, 17, supply=2)
    for a in s.assignments:
        print(f"{a.family.family_id}  score={a.family.final_score}  {'SERVED' if a.served else 'unserved'}")
