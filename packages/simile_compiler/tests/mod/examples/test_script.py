import pathlib
from typing import Any, Generator

EXAMPLES_FOLDER = pathlib.Path(__file__).parent / "examples"


def test_examples() -> Generator[str, Any, None]:
    for example_file in EXAMPLES_FOLDER.glob("*.sim"):
        print(f"Testing example: {example_file}")
        with open(example_file, "r") as f:
            source = f.read()
        yield source
