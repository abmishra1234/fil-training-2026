"""Characterization (golden-master) tests: the legacy output IS the spec.
Run:  STEP=step4_extract pytest -q test_golden.py
"""
import importlib, os, random
from report_before import process as legacy

step = importlib.import_module(os.environ.get("STEP", "step6_fixed"))
Order = getattr(step, "Order", None)
run = getattr(step, "build_report", None) or step.process


def new(orders):
    return run([Order(**o) for o in orders] if Order else orders)


def random_orders(rng):
    return [{"id": f"O{i}", "type": rng.choice(["EQ", "FI", "FX", "XX"]),
             "qty": rng.randint(1, 5000),
             "px": round(rng.uniform(0.01, 500), rng.choice([2, 4]))}
            for i in range(rng.randint(0, 6))]


EDGE_CASES = [
    [],                                                       # empty report
    [{"id": "U", "type": "??", "qty": 1, "px": 1.0}],         # unknown type
    [{"id": "M", "type": "EQ", "qty": 10, "px": 10.0}],       # fee 0.25 -> min
    [{"id": "B", "type": "EQ", "qty": 400, "px": 1.0}],       # fee exactly 1.0
    [{"id": "X", "type": "FX", "qty": 1, "px": 99.0}],        # flat fee
]


def test_edge_cases():
    for orders in EDGE_CASES:
        assert new(orders) == legacy(orders)


def test_random_orders_match_legacy():
    rng = random.Random(1)
    failures = [o for o in (random_orders(rng) for _ in range(200_000))
                if new(o) != legacy(o)]
    assert not failures, f"{len(failures)} mismatches, e.g. {failures[0]}"
