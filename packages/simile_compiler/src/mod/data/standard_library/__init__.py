import pathlib

STANDARD_LIBRARY_FOLDER = pathlib.Path(__file__).resolve().parent

STANDARD_LIBRARY_FILE_NAMES = [
    "bag",
    "math",
    "relation",
    "sequence",
    "set",
    "type",
]

STANDARD_LIBRARY_FILES = [STANDARD_LIBRARY_FOLDER / f"{file}.sim" for file in STANDARD_LIBRARY_FILE_NAMES]
