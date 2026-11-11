import pathlib

EXAMPLES_FOLDER = pathlib.Path(__file__).resolve().parent

EXAMPLES_SUBFOLDERS = [
    "algorithms",
    "data_processing",
    "simulations",
]

EXAMPLES_FILES = [file for folder in EXAMPLES_SUBFOLDERS for file in (EXAMPLES_FOLDER / folder).iterdir() if file.is_file() and file.suffix == ".sim"]
