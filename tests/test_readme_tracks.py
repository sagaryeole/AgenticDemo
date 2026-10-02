"""Every agent folder must appear in exactly one learning track in the README."""
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_each_agent_is_in_exactly_one_track():
    readme = (ROOT / "README.md").read_text()
    section = readme.split("## Learning tracks", 1)[1].split("\n## ", 1)[0]
    linked = Counter(re.findall(r"\]\((agent\d\d_\w+)/CASES\.md\)", section))
    folders = {p.name for p in ROOT.glob("agent[0-9][0-9]_*") if p.is_dir()}
    assert set(linked) == folders
    assert all(count == 1 for count in linked.values()), [a for a, c in linked.items() if c > 1]
    for folder in folders:
        assert (ROOT / folder / "CASES.md").exists(), folder
