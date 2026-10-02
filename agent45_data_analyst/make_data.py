"""Writes grades.csv: 24 made-up students, three classes, three tests. Run once (the file is already in this folder).

    uv run python agent45_data_analyst/make_data.py

The values come from a fixed random seed, so the file is always the same and the right answers to every question can be computed exactly.
"""
import csv
import random
from pathlib import Path

NAMES = ["Alma", "Bruno", "Chloe", "Dario", "Elin", "Felix", "Greta", "Hugo", "Ines", "Jonas", "Klara", "Leo",
         "Mira", "Nils", "Olga", "Pablo", "Quinn", "Rosa", "Sven", "Tilda", "Ulf", "Vera", "Wilmer", "Yara"]
CLASSES = ["Maple", "Oak", "Birch"]


def main() -> None:
    rng = random.Random(2)
    rows = []
    for i, name in enumerate(NAMES):
        base = rng.randint(35, 85)
        test1 = base + rng.randint(-6, 6)
        test2 = test1 + rng.randint(-8, 12)
        test3 = test2 + rng.randint(-8, 14)
        clamp = lambda v: max(0, min(100, v))
        rows.append({"student": name, "class": CLASSES[i % 3], "test1": clamp(test1), "test2": clamp(test2), "test3": clamp(test3)})
    path = Path(__file__).resolve().parent / "grades.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["student", "class", "test1", "test2", "test3"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
