"""
Module 1 — 0/1 Knapsack via Dynamic Programming
-------------------------------------------------
Finds the optimal subset of relief items to pack into one bag,
maximizing total benefit without exceeding the weight capacity.

Time:  O(n × W)   Space: O(n × W)
"""

from typing import List, Tuple
from models import ReliefItem

PRECISION = 10  # work in 0.1 kg steps


def optimize_bag(
    items: List[ReliefItem],
    capacity_kg: float,
) -> Tuple[List[ReliefItem], float, int]:
    """
    Returns (selected_items, total_weight_kg, total_benefit).
    Each item is either included (1) or excluded (0) — no fractions.
    """
    W = int(capacity_kg * PRECISION)
    weights  = [int(round(it.weight_kg * PRECISION)) for it in items]
    benefits = [it.benefit for it in items]
    n = len(items)

    # Build DP table bottom-up
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, bi = weights[i - 1], benefits[i - 1]
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wi <= w:
                val = dp[i - 1][w - wi] + bi
                if val > dp[i][w]:
                    dp[i][w] = val

    # Backtrack to recover selected items
    selected, w = [], W
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1])
            w -= weights[i - 1]

    total_weight  = round(sum(it.weight_kg for it in selected), 2)
    total_benefit = dp[n][W]
    return selected, total_weight, total_benefit


def get_dp_table(items: List[ReliefItem], capacity_kg: float):
    """Return the full DP table and metadata (for display in GUI)."""
    W = int(capacity_kg * PRECISION)
    weights  = [int(round(it.weight_kg * PRECISION)) for it in items]
    benefits = [it.benefit for it in items]
    n = len(items)

    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, bi = weights[i - 1], benefits[i - 1]
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wi <= w:
                val = dp[i - 1][w - wi] + bi
                if val > dp[i][w]:
                    dp[i][w] = val

    return dp, items, W, PRECISION


if __name__ == "__main__":
    sample = [
        ReliefItem("Rice",         3.0, 9, 50),
        ReliefItem("Canned goods", 1.5, 7, 80),
        ReliefItem("Water",        2.0, 8, 60),
        ReliefItem("Medicine",     0.5,10, 40),
        ReliefItem("Blanket",      1.5, 5, 30),
        ReliefItem("Hygiene kit",  0.5, 6, 50),
    ]
    sel, wt, ben = optimize_bag(sample, 10.0)
    print("Selected items:")
    for it in sel:
        print(f"  {it.name:15} {it.weight_kg} kg  benefit={it.benefit}")
    print(f"Total: {wt} kg  benefit={ben}")
