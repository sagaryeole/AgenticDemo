"""Twenty small tools for a study helper. Plain functions: ADK builds each tool's description from its name, parameters and docstring.

Several tools are close neighbours on purpose (three date tools, two percentage tools, two random tools, two text-length tools),
because that is where a model gets confused when it has many tools to choose from.
"""
import math
import random
from datetime import date, timedelta

RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "SEK": 10.6, "JPY": 150.0}  # made-up fixed rates, for the demo only


def convert_length(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts a length between units: mm, cm, m, km, inch, ft, mile.

    Args:
        value: The number to convert.
        from_unit: The unit the value is in, e.g. 'km'.
        to_unit: The unit to convert to, e.g. 'mile'.
    """
    metres = {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "inch": 0.0254, "ft": 0.3048, "mile": 1609.344}
    return {"result": round(value * metres[from_unit] / metres[to_unit], 4), "unit": to_unit}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts a temperature between Celsius (C), Fahrenheit (F) and Kelvin (K).

    Args:
        value: The temperature to convert.
        from_unit: 'C', 'F' or 'K'.
        to_unit: 'C', 'F' or 'K'.
    """
    celsius = value if from_unit == "C" else (value - 32) * 5 / 9 if from_unit == "F" else value - 273.15
    result = celsius if to_unit == "C" else celsius * 9 / 5 + 32 if to_unit == "F" else celsius + 273.15
    return {"result": round(result, 2), "unit": to_unit}


def convert_weight(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts a weight or mass between units: g, kg, oz, lb.

    Args:
        value: The number to convert.
        from_unit: The unit the value is in, e.g. 'kg'.
        to_unit: The unit to convert to, e.g. 'lb'.
    """
    grams = {"g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592}
    return {"result": round(value * grams[from_unit] / grams[to_unit], 4), "unit": to_unit}


def convert_money(amount: float, from_currency: str, to_currency: str) -> dict:
    """Converts an amount of money from one currency to another (USD, EUR, GBP, SEK, JPY) at fixed demo rates.

    Args:
        amount: The amount of money.
        from_currency: Currency code of the amount, e.g. 'USD'.
        to_currency: Currency code to convert to, e.g. 'EUR'.
    """
    return {"result": round(amount / RATES[from_currency] * RATES[to_currency], 2), "currency": to_currency}


def percentage_of(percent: float, number: float) -> dict:
    """Calculates a percentage of a number, e.g. 15 percent of 80.

    Args:
        percent: The percentage, e.g. 15.
        number: The number to take the percentage of.
    """
    return {"result": round(percent / 100 * number, 4)}


def percent_change(old_value: float, new_value: float) -> dict:
    """Calculates by how many percent a value went up or down from an old value to a new value.

    Args:
        old_value: The starting value.
        new_value: The final value.
    """
    return {"percent_change": round((new_value - old_value) / old_value * 100, 2)}


def average(numbers: list[float]) -> dict:
    """Calculates the average (mean) of a list of numbers.

    Args:
        numbers: The numbers to average.
    """
    return {"average": round(sum(numbers) / len(numbers), 4)}


def split_bill(total: float, people: int, tip_percent: float = 0) -> dict:
    """Splits a restaurant bill evenly between people, with an optional tip.

    Args:
        total: The bill before the tip.
        people: How many people share it.
        tip_percent: The tip as a percentage of the bill (default 0).
    """
    return {"each_pays": round(total * (1 + tip_percent / 100) / people, 2)}


def days_between(start_date: str, end_date: str) -> dict:
    """Counts the days from one date to another. Dates are written YYYY-MM-DD.

    Args:
        start_date: The first date.
        end_date: The second date.
    """
    return {"days": (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days}


def add_days(start_date: str, days: int) -> dict:
    """Finds the date that is a number of days after (or before, if negative) a given date. Dates are written YYYY-MM-DD.

    Args:
        start_date: The date to start from.
        days: How many days to add (negative to go back).
    """
    return {"date": (date.fromisoformat(start_date) + timedelta(days=days)).isoformat()}


def weekday_of(day: str) -> dict:
    """Tells which day of the week (Monday, Tuesday, ...) a date falls on. Dates are written YYYY-MM-DD.

    Args:
        day: The date.
    """
    return {"weekday": date.fromisoformat(day).strftime("%A")}


def count_words(text: str) -> dict:
    """Counts how many words a text contains.

    Args:
        text: The text to count.
    """
    return {"words": len(text.split())}


def reading_time(text: str) -> dict:
    """Estimates how many minutes it takes to read a text aloud or silently, at 200 words per minute.

    Args:
        text: The text to time.
    """
    return {"minutes": round(len(text.split()) / 200, 2)}


def reverse_text(text: str) -> dict:
    """Writes a text backwards, letter by letter.

    Args:
        text: The text to reverse.
    """
    return {"reversed": text[::-1]}


def to_uppercase(text: str) -> dict:
    """Turns a text into CAPITAL LETTERS.

    Args:
        text: The text to change.
    """
    return {"text": text.upper()}


def roll_dice(sides: int = 6) -> dict:
    """Rolls one die with the given number of sides and tells what came up.

    Args:
        sides: How many sides the die has (default 6).
    """
    return {"rolled": random.randint(1, sides)}


def flip_coin() -> dict:
    """Flips a coin and tells whether it landed on heads or tails."""
    return {"result": random.choice(["heads", "tails"])}


def random_number(low: int, high: int) -> dict:
    """Picks a random whole number between low and high, both included.

    Args:
        low: The smallest possible number.
        high: The largest possible number.
    """
    return {"number": random.randint(low, high)}


def is_prime(number: int) -> dict:
    """Checks whether a whole number is a prime number.

    Args:
        number: The number to check.
    """
    prime = number > 1 and all(number % d for d in range(2, int(math.sqrt(number)) + 1))
    return {"is_prime": prime}


def square_root(number: float) -> dict:
    """Calculates the square root of a number.

    Args:
        number: A number that is zero or larger.
    """
    return {"result": round(math.sqrt(number), 6)}


ALL_TOOLS = [
    convert_length, convert_temperature, convert_weight, convert_money, percentage_of, percent_change, average, split_bill,
    days_between, add_days, weekday_of, count_words, reading_time, reverse_text, to_uppercase, roll_dice, flip_coin,
    random_number, is_prime, square_root,
]

# (question, the tool that should be called FIRST)
QUESTIONS = [
    ("How many miles is 42 kilometres?", "convert_length"),
    ("It is 77 degrees Fahrenheit outside, what is that in Celsius?", "convert_temperature"),
    ("How many pounds is 12 kg?", "convert_weight"),
    ("How much is 250 US dollars in euros?", "convert_money"),
    ("What is 15 percent of 80?", "percentage_of"),
    ("The price went from 40 to 50. By how many percent did it go up?", "percent_change"),
    ("What is the average of 7, 9, 12 and 20?", "average"),
    ("Four of us had dinner for 96 dollars. Split it evenly with a 10 percent tip.", "split_bill"),
    ("How many days are there from 2026-03-01 to 2026-05-15?", "days_between"),
    ("What date is 45 days after 2026-01-10?", "add_days"),
    ("Which day of the week is 2026-12-25?", "weekday_of"),
    ("How many words are in 'the quick brown fox jumps over the lazy dog'?", "count_words"),
    ("How many minutes does it take to read this aloud: 'the quick brown fox jumps over the lazy dog'?", "reading_time"),
    ("Write 'photosynthesis' backwards.", "reverse_text"),
    ("Make 'study hard' all capital letters.", "to_uppercase"),
    ("Roll a 20-sided die for me.", "roll_dice"),
    ("Flip a coin.", "flip_coin"),
    ("Pick a number between 1 and 50.", "random_number"),
    ("Is 91 a prime number?", "is_prime"),
    ("What is the square root of 144?", "square_root"),
    ("How heavy is 3 pounds in grams?", "convert_weight"),
    ("What is 20% of 350?", "percentage_of"),
    ("My savings dropped from 500 to 450. What is the percentage change?", "percent_change"),
    ("How many days until 2026-12-31 if today is 2026-10-02?", "days_between"),
]
