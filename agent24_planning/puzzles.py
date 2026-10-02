"""Three small puzzles with ONE correct answer each, used to compare how an agent reasons.

Run `uv run python agent24_planning/puzzles.py` to re-check by brute force that every answer is the only possible one.
"""
import re
from itertools import permutations

ANSWER_RULE = " Reply with ONLY one line in exactly this form, with no explanation or working shown: ANSWER: <your answer>"

SEATING = (
    "Five friends, Ana, Ben, Cleo, Dan and Eve, sit in a row of five seats numbered 1 to 5 from left to right. "
    "Ana sits somewhere to the left of Ben. Cleo does not sit at either end. Dan sits next to Eve. "
    "Ben sits exactly two seats away from Cleo. Eve does not sit next to Ben. Ana does not sit in seat 1. "
    "Dan does not sit in seat 1. "
    "Who sits in each seat?" + ANSWER_RULE.replace("<your answer>", "<the five names from seat 1 to seat 5, separated by commas>")
)
SEATING_ANSWER = "Eve, Dan, Cleo, Ana, Ben"  # verified as the only solution by check_seating() below

SCHEDULE = (
    "Mia starts work at 09:00 and works without a break except for the fixed events below. She must write a report that "
    "needs 3 hours 30 minutes of work in total. She may pause the report and continue later. Fixed events she must attend: "
    "a client call from 11:00 to 11:30, and lunch from 12:30 to 13:15. When the report is finished she needs 45 minutes to "
    "review it, and the review cannot be paused. What is the earliest time she can finish the review?"
    + ANSWER_RULE.replace("<your answer>", "<the time as HH:MM>")
)
SCHEDULE_ANSWER = "14:30"

PETS = (
    "Four neighbours, Ana, Ben, Cleo and Dan, each own a different pet (cat, dog, fish, bird) and each drinks a different "
    "drink (tea, coffee, juice, milk). The cat owner drinks tea. Ana does not own the dog and does not drink coffee. "
    "Ben drinks milk. The bird owner drinks juice. Dan owns neither the cat nor the fish. Cleo does not drink tea. "
    "Dan drinks coffee. "
    "Who owns the fish?" + ANSWER_RULE.replace("<your answer>", "<one name>")
)
PETS_ANSWER = "Ben"

SEATING7_CLUES = (
    "Ana does not sit in seat 4. Finn sits next to Ana. Ana does not sit in seat 6. Dan does not sit next to Ben. "
    "Finn does not sit next to Eve. Eve sits next to Ben. Dan does not sit in seat 2. Ben does not sit in seat 6. "
    "Ben sits next to Cleo. Cleo does not sit at either end. Ben sits exactly two seats away from Gus. "
    "Dan sits somewhere to the left of Ben. Ben does not sit in seat 4. Finn does not sit in seat 6. "
    "Eve sits somewhere to the left of Cleo. Dan does not sit next to Ana. Ana sits exactly two seats away from Ben."
)
SEATING7 = (
    "Seven friends, Ana, Ben, Cleo, Dan, Eve, Finn and Gus, sit in a row of seven seats numbered 1 to 7 from left to right. "
    + SEATING7_CLUES + " Who sits in each seat?"
    + ANSWER_RULE.replace("<your answer>", "<the seven names from seat 1 to seat 7, separated by commas>")
)
SEATING7_ANSWER = "Dan, Finn, Ana, Eve, Ben, Cleo, Gus"  # verified as the only solution by check_seating7() below

PUZZLES = [
    ("seating", SEATING, SEATING_ANSWER),
    ("schedule", SCHEDULE, SCHEDULE_ANSWER),
    ("pets", PETS, PETS_ANSWER),
    ("seating7", SEATING7, SEATING7_ANSWER),
]


def check_seating() -> list[tuple]:
    names = ["Ana", "Ben", "Cleo", "Dan", "Eve"]
    solutions = []
    for order in permutations(names):                       # order[0] is seat 1
        seat = {n: i + 1 for i, n in enumerate(order)}
        if (seat["Ana"] < seat["Ben"] and seat["Cleo"] not in (1, 5) and abs(seat["Dan"] - seat["Eve"]) == 1
                and abs(seat["Ben"] - seat["Cleo"]) == 2 and abs(seat["Eve"] - seat["Ben"]) != 1 and seat["Ana"] != 1
                and seat["Dan"] != 1):
            solutions.append(order)
    return solutions


def check_pets() -> set:
    people = ["Ana", "Ben", "Cleo", "Dan"]
    fish_owners = set()
    for pets in permutations(["cat", "dog", "fish", "bird"]):
        pet = dict(zip(people, pets))
        for drinks in permutations(["tea", "coffee", "juice", "milk"]):
            drink = dict(zip(people, drinks))
            owner = {v: k for k, v in pet.items()}
            if (drink[owner["cat"]] == "tea" and pet["Ana"] != "dog" and drink["Ana"] != "coffee" and drink["Ben"] == "milk"
                    and drink[owner["bird"]] == "juice" and pet["Dan"] not in ("cat", "fish") and drink["Cleo"] != "tea"
                    and drink["Dan"] == "coffee"):
                fish_owners.add(owner["fish"])
    return fish_owners


def check_schedule() -> str:
    """Minutes since midnight: work 09:00-11:00 (120), call, 11:30-12:30 (60), lunch, 13:15-13:45 (30) = 210 total."""
    needed, t = 210, 9 * 60
    breaks = [(11 * 60, 11 * 60 + 30), (12 * 60 + 30, 13 * 60 + 15)]
    while needed > 0:
        if not any(a <= t < b for a, b in breaks):
            needed -= 1
        t += 1
    t += 45
    return f"{t // 60:02d}:{t % 60:02d}"


def parse_clues(clues: str, seats: int) -> list[tuple]:
    """Turn clue sentences into (sentence, rule) pairs. A rule takes {name: seat_number} and returns True if it holds.

    Understands six kinds of sentence: 'A does not sit in seat 3.', 'A sits next to B.', 'A does not sit next to B.',
    'A does not sit at either end.', 'A sits somewhere to the left of B.', 'A sits exactly two seats away from B.'
    """
    rules = []
    for clue in re.split(r"(?<=\.)\s+", clues.strip()):
        if m := re.fullmatch(r"(\w+) does not sit in seat (\d)\.", clue):
            rules.append((clue, lambda s, a=m[1], k=int(m[2]): s[a] != k))
        elif m := re.fullmatch(r"(\w+) sits next to (\w+)\.", clue):
            rules.append((clue, lambda s, a=m[1], b=m[2]: abs(s[a] - s[b]) == 1))
        elif m := re.fullmatch(r"(\w+) does not sit next to (\w+)\.", clue):
            rules.append((clue, lambda s, a=m[1], b=m[2]: abs(s[a] - s[b]) != 1))
        elif m := re.fullmatch(r"(\w+) does not sit at either end\.", clue):
            rules.append((clue, lambda s, a=m[1]: s[a] not in (1, seats)))
        elif m := re.fullmatch(r"(\w+) sits somewhere to the left of (\w+)\.", clue):
            rules.append((clue, lambda s, a=m[1], b=m[2]: s[a] < s[b]))
        elif m := re.fullmatch(r"(\w+) sits exactly two seats away from (\w+)\.", clue):
            rules.append((clue, lambda s, a=m[1], b=m[2]: abs(s[a] - s[b]) == 2))
        else:
            raise ValueError(f"clue not understood: {clue!r}")
    return rules


def check_seating7() -> list[tuple]:
    """Brute-force the 7-seat puzzle by reading the clue SENTENCES themselves, so the text and the check cannot drift apart."""
    names = ["Ana", "Ben", "Cleo", "Dan", "Eve", "Finn", "Gus"]
    rules = parse_clues(SEATING7_CLUES, 7)
    solutions = []
    for order in permutations(names):
        seat = {n: i + 1 for i, n in enumerate(order)}
        if all(rule(seat) for _, rule in rules):
            solutions.append(order)
    return solutions


if __name__ == "__main__":
    seating = check_seating()
    print("seating solutions:", [", ".join(s) for s in seating], "-> unique" if len(seating) == 1 else "-> NOT UNIQUE")
    print("pets: fish owner(s):", check_pets())
    print("schedule: finish at", check_schedule())
    seven = check_seating7()
    print("seating7 solutions:", [", ".join(x) for x in seven], "-> unique" if len(seven) == 1 else "-> NOT UNIQUE")
