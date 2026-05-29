import sys
import time
import unittest

from models import Family, ReliefItem
from knapsack import optimize_bag
from priority import assign_bags


def print_usage():
    print("Usage: python checker.py <option>")
    print("<option>: quick, full")


def check_knapsack_case():
    items = [
        ReliefItem("Rice", 3.0, 9, 50),
        ReliefItem("Canned goods", 1.5, 7, 80),
        ReliefItem("Water", 2.0, 8, 60),
        ReliefItem("Medicine", 0.5, 10, 40),
        ReliefItem("Blanket", 1.5, 5, 30),
        ReliefItem("Hygiene kit", 0.5, 6, 50),
    ]
    selected, weight, benefit = optimize_bag(items, 10.0)

    assert round(weight, 2) == 9.0, f"Knapsack weight mismatch: got {weight}"
    assert benefit == 45, f"Knapsack benefit mismatch: got {benefit}"
    assert len(selected) == 6, f"Knapsack selected count mismatch: got {len(selected)}"


def check_priority_case():
    bag = [
        ReliefItem("Rice", 3.0, 9, 50),
        ReliefItem("Water", 2.0, 8, 60),
    ]
    families = [
        Family("F-001", 5, 2, 3, 1),
        Family("F-002", 3, 0, 2, 2),
        Family("F-003", 4, 3, 3, 3),
        Family("F-004", 2, 1, 1, 4),
    ]

    summary = assign_bags(families, bag, 5.0, 17, supply=2)

    assert summary.served == 2, f"Served mismatch: got {summary.served}"
    assert summary.unserved == 2, f"Unserved mismatch: got {summary.unserved}"
    assert (
        summary.total_benefit_delivered == 34
    ), f"Total benefit mismatch: got {summary.total_benefit_delivered}"

    got_order = [a.family.family_id for a in summary.assignments]
    exp_order = ["F-003", "F-001", "F-002", "F-004"]
    assert got_order == exp_order, f"Rank order mismatch: got {got_order}"


def run_unittests():
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return result.wasSuccessful()


def run_checks(option: str):
    passed = 0
    failed = 0

    checks = [
        ("knapsack_case", check_knapsack_case),
        ("priority_case", check_priority_case),
    ]
    if option == "full":
        checks.append(("unit_tests", None))

    for name, check_fn in checks:
        try:
            if name == "unit_tests":
                ok = run_unittests()
                if not ok:
                    raise AssertionError("Unit tests failed")
            else:
                check_fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1

    print(f"\nSummary: PASS={passed}, FAIL={failed}")
    return 0 if failed == 0 else 1


def main():
    if len(sys.argv) != 2:
        print_usage()
        return 1

    option = sys.argv[1].strip().lower()
    if option not in {"quick", "full"}:
        print("Error: option not found")
        print_usage()
        return 1

    return run_checks(option)


if __name__ == "__main__":
    start = time.time()
    code = main()
    end = time.time()
    print(f"Ran for: {end - start:.4f} seconds")
    raise SystemExit(code)
