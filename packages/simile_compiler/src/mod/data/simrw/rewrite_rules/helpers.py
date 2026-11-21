import pathlib

REWRITE_RULES_FOLDER = pathlib.Path(__file__).resolve().parent


def get_rewrite_rule_file_paths(folder_name: str, file_names: list[str]) -> list[pathlib.Path]:
    return [REWRITE_RULES_FOLDER / folder_name / f"{file_name}.simrw" for file_name in file_names]
