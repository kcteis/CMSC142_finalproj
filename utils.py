"""
validator.py — Input validation & supply warnings
report.py    — TXT and CSV export
(combined into one file for simplicity)
"""

import csv
from datetime import datetime
from typing import List, Tuple
from models import ReliefItem, Family, OperationSummary


# ── Validation ────────────────────────────────────────────────────────────────

def validate_item(name, weight, benefit, quantity) -> Tuple[bool, str]:
    if not str(name).strip():
        return False, "Item name cannot be empty."
    try:
        w = float(weight)
    except ValueError:
        return False, f"Weight must be a number (got '{weight}')."
    if w <= 0 or w > 20:
        return False, "Weight must be between 0.1 and 20 kg."
    try:
        b = int(benefit)
    except ValueError:
        return False, f"Benefit must be a whole number (got '{benefit}')."
    if not (1 <= b <= 10):
        return False, "Benefit must be between 1 and 10."
    try:
        q = int(quantity)
    except ValueError:
        return False, f"Quantity must be a whole number (got '{quantity}')."
    if q < 1:
        return False, "Quantity must be at least 1."
    return True, ""


def validate_capacity(cap) -> Tuple[bool, str]:
    try:
        c = float(cap)
    except ValueError:
        return False, f"Capacity must be a number (got '{cap}')."
    if c <= 0 or c > 50:
        return False, "Capacity must be between 0.1 and 50 kg."
    return True, ""


def validate_family(fid, size, vuln, dmg) -> Tuple[bool, str]:
    if not str(fid).strip():
        return False, "Family ID cannot be empty."
    try:
        s = int(size)
    except ValueError:
        return False, "Family size must be a whole number."
    if not (1 <= s <= 20):
        return False, "Family size must be between 1 and 20."
    try:
        v = int(vuln)
    except ValueError:
        return False, "Vulnerable count must be a whole number."
    if v < 0 or v > s:
        return False, "Vulnerable count must be 0 to family size."
    try:
        d = int(dmg)
    except ValueError:
        return False, "Damage level must be 1, 2, or 3."
    if d not in (1, 2, 3):
        return False, "Damage level must be 1 (minor), 2 (partial), or 3 (total loss)."
    return True, ""


def check_supply_warnings(families: List[Family], supply: int) -> List[str]:
    warnings = []
    n = len(families)
    shortage = n - supply
    if shortage > 0:
        warnings.append(
            f"Supply shortage: {supply} bags for {n} families — "
            f"{shortage} family/families will NOT receive relief."
        )
        if shortage / n > 0.5:
            warnings.append(
                "Critical: more than half of registered families will be unserved. "
                "Consider requesting additional supply."
            )
    high_vuln = [f for f in families if f.vulnerable_count >= 3]
    if high_vuln and shortage > 0:
        warnings.append(
            f"{len(high_vuln)} family/families have 3+ vulnerable members — "
            "verify they fall within the served group after ranking."
        )
    return warnings


# ── Report export ─────────────────────────────────────────────────────────────

def build_text_report(summary: OperationSummary,
                      disaster: str = "", barangay: str = "") -> str:
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines += ["=" * 60,
              "  BARANGAY RELIEF DISTRIBUTION REPORT",
              "=" * 60]
    if disaster: lines.append(f"  Disaster  : {disaster}")
    if barangay: lines.append(f"  Barangay  : {barangay}")
    lines.append(f"  Generated : {now}")
    lines += ["",
              "OPTIMIZED BAG CONTENTS (0/1 Knapsack DP)",
              "-" * 40]
    for it in summary.bag_contents:
        lines.append(f"  {it.name:20} {it.weight_kg} kg  benefit={it.benefit}")
    lines.append(f"  {'TOTAL':20} {summary.bag_weight} kg  benefit={summary.bag_benefit}")
    lines += ["",
              "SUPPLY SUMMARY",
              "-" * 40,
              f"  Total families   : {summary.total_families}",
              f"  Families SERVED  : {summary.served}",
              f"  Families UNSERVED: {summary.unserved}",
              f"  Total benefit    : {summary.total_benefit_delivered}",
              "",
              "PRIORITY ASSIGNMENT",
              "-" * 60,
              f"  {'#':>3}  {'Family':8}  {'Score':>7}  {'Size':>4}  "
              f"{'Vuln':>4}  {'Dmg':>3}  Status",
              "  " + "-" * 55]
    for rank, a in enumerate(summary.assignments, 1):
        f = a.family
        lines.append(
            f"  {rank:>3}  {f.family_id:8}  {f.final_score:>7.1f}"
            f"  {f.size:>4}  {f.vulnerable_count:>4}  {f.damage_level:>3}"
            f"  {'SERVED' if a.served else 'NO SUPPLY'}"
        )
    lines += ["", "=" * 60,
              "  Barangay Relief Pack Optimizer",
              "=" * 60]
    return "\n".join(lines)


def export_text(summary: OperationSummary, path: str,
                disaster: str = "", barangay: str = "") -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_text_report(summary, disaster, barangay))
    return path


def export_csv(summary: OperationSummary, path: str) -> str:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Rank","Family ID","Final Score","Formula Score",
                    "Size","Vulnerable","Damage","Status","Bag Weight","Bag Benefit"])
        for rank, a in enumerate(summary.assignments, 1):
            fam = a.family
            w.writerow([rank, fam.family_id, fam.final_score, fam.formula_score,
                        fam.size, fam.vulnerable_count, fam.damage_level,
                        "SERVED" if a.served else "UNSERVED",
                        a.bag_weight, a.bag_benefit])
    return path
