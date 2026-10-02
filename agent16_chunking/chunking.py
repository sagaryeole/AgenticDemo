"""Lab 16: chunking. Cut a document into pieces, and see which cuts break the facts.

Run:   uv run python agent16_chunking/chunking.py
       uv run python agent16_chunking/chunking.py --size 200 --overlap 40
       uv run python agent16_chunking/chunking.py --show sections

No model and no network needed. This is plain Python.
"""
import argparse
import re
from pathlib import Path

HANDBOOK = Path(__file__).resolve().parent.parent / "data" / "handbook.md"

# Sentences from the handbook that a good chunk should keep WHOLE. If a cut falls inside one of
# these, a question about it can no longer be answered from a single chunk.
FACTS = [
    "Late books cost 25 cents per day, up to a maximum of 5 dollars per book",
    "Members can borrow up to 8 books at the same time",
    "Each book can be kept for 21 days",
    "Wi-Fi is free: connect to the network \"Riverside-Guest\"",
    "needs registration through form LB-204",
    "If you lose your card, a replacement costs 3 dollars",
    "Printing costs 10 cents per black-and-white page and 50 cents per colour page",
    "The library accepts donated books in good condition on Tuesdays and Thursdays between 10:00 and 12:00",
    "A booking is cancelled automatically if nobody arrives within 15 minutes of the start time",
    "We are closed on Sunday and Monday",
    "Borrowing is blocked while your unpaid fees are higher than 10 dollars",
]


# ---------------------------------------------------------------------------
# The chunking strategies. Each takes the whole text and returns a list of strings.
# ---------------------------------------------------------------------------

def fixed_size(text: str, size: int = 300, overlap: int = 0) -> list[str]:
    """Cut every `size` characters, no matter what the text says. `overlap` repeats the end of a chunk
    at the start of the next one, so a fact cut at the boundary appears whole in one of the two."""
    step = max(1, size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        chunks.append(text[start:start + size])
        if start + size >= len(text):  # this chunk already reaches the end, a further one would be a copy of its tail
            break
    return [c for c in chunks if c.strip()]


def sentences(text: str, per_chunk: int = 2) -> list[str]:
    """Group every `per_chunk` sentences. Keeps sentences whole, but ignores the document's structure."""
    flat = re.sub(r"\s+", " ", re.sub(r"^#+ .*$", "", text, flags=re.M)).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    return [" ".join(parts[i:i + per_chunk]) for i in range(0, len(parts), per_chunk)]


def paragraphs(text: str) -> list[str]:
    """One chunk per paragraph (text between blank lines), with the heading lines removed. Each chunk is
    a clean piece of text, but it no longer says which section it came from."""
    without_headings = re.sub(r"(?m)^#+ .*\n?", "", text)
    return [b.strip() for b in re.split(r"\n\s*\n", without_headings) if b.strip()]


def sections(text: str) -> list[str]:
    """One chunk per `## ` section, heading included. Follows the structure the author wrote."""
    blocks = re.split(r"(?m)^(?=## )", text)
    return [b.strip() for b in blocks if b.strip().startswith("## ")]


def paragraphs_with_heading(text: str) -> list[str]:
    """One chunk per paragraph, with its section title put in front. Small chunks, but each one
    still says which topic it belongs to."""
    chunks = []
    for section in sections(text):
        title, _, body = section.partition("\n")
        for paragraph in re.split(r"\n\s*\n", body.strip()):
            if paragraph.strip():
                chunks.append(f"{title.lstrip('# ').strip()}: {paragraph.strip()}")
    return chunks


def build_strategies(size: int, overlap: int) -> dict:
    return {
        "fixed": lambda t: fixed_size(t, size, 0),
        "fixed+overlap": lambda t: fixed_size(t, size, overlap),
        "sentences": lambda t: sentences(t, 2),
        "paragraphs": paragraphs,
        "sections": sections,
        "paragraphs+heading": paragraphs_with_heading,
    }


# ---------------------------------------------------------------------------
# Measuring
# ---------------------------------------------------------------------------

def flat(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def facts_intact(chunks: list[str]) -> list[str]:
    """Which FACTS appear completely inside at least one chunk?"""
    joined = [flat(c) for c in chunks]
    return [f for f in FACTS if any(f in c for c in joined)]


def show_break(chunks: list[str], fact: str) -> None:
    """Print the place where a fact was cut in two."""
    head = fact[:20]
    for i, chunk in enumerate(chunks):
        c = flat(chunk)
        pos = c.find(head)
        if pos != -1 and fact not in c:
            print(f"   chunk {i} ends with: ...{c[-60:]!r}")
            if i + 1 < len(chunks):
                print(f"   chunk {i + 1} starts: {flat(chunks[i + 1])[:60]!r}...")
            return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=int, default=300, help="characters per chunk for the fixed strategies")
    parser.add_argument("--overlap", type=int, default=60, help="overlap for 'fixed+overlap'")
    parser.add_argument("--show", help="print every chunk of one strategy, e.g. --show sections")
    args = parser.parse_args()

    text = HANDBOOK.read_text()
    strategies = build_strategies(args.size, args.overlap)

    if args.show:
        chunks = strategies[args.show](text)
        for i, chunk in enumerate(chunks):
            print(f"--- chunk {i} ({len(chunk)} chars)\n{chunk}\n")
        return

    print(f"Document: {HANDBOOK.name}, {len(text)} characters, {len(FACTS)} key facts to keep whole\n")
    print(f"{'strategy':<20} {'chunks':>6} {'avg chars':>10} {'min..max':>11} {'facts intact':>13}")
    for name, make in strategies.items():
        chunks = make(text)
        lengths = [len(c) for c in chunks]
        intact = facts_intact(chunks)
        print(f"{name:<20} {len(chunks):>6} {sum(lengths) // len(lengths):>10} "
              f"{min(lengths):>5}..{max(lengths):<5} {len(intact):>8}/{len(FACTS)}")

    broken = [f for f in FACTS if f not in facts_intact(strategies['fixed'](text))]
    if broken:
        print(f"\nExample of a fact cut in two by the 'fixed' strategy (size {args.size}):")
        print(f"   fact: {broken[0]!r}")
        show_break(strategies["fixed"](text), broken[0])


if __name__ == "__main__":
    main()
