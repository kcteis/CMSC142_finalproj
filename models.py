from dataclasses import dataclass, field
from typing import List


@dataclass
class ReliefItem:
    name: str
    weight_kg: float
    benefit: int
    quantity: int

    def __repr__(self):
        return f"{self.name} ({self.weight_kg}kg, benefit={self.benefit})"


@dataclass
class Family:
    family_id: str
    size: int
    vulnerable_count: int   # elderly, infants, pregnant members
    damage_level: int       # 1=minor, 2=partial, 3=total loss
    registration_order: int = 0

    # Filled after scoring
    formula_score: float = 0.0
    ml_score: float = 0.0
    final_score: float = 0.0

    def compute_formula_score(self) -> float:
        self.formula_score = (
            (self.size * 2) +
            (self.vulnerable_count * 5) +
            (self.damage_level * 3)
        )
        return self.formula_score


@dataclass
class AssignmentResult:
    family: Family
    bag_contents: List[ReliefItem]
    bag_weight: float
    bag_benefit: int
    served: bool


@dataclass
class OperationSummary:
    total_families: int
    served: int
    unserved: int
    total_benefit_delivered: int
    bag_contents: List[ReliefItem]
    bag_weight: float
    bag_benefit: int
    assignments: List[AssignmentResult]
