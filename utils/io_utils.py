import os
import glob
import argparse
import yaml


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run the workflow using a YAML configuration file."
    )
    parser.add_argument(
        "config",
        help="Path to the YAML configuration file."
    )
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """
    Load processing settings from a YAML config file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as HH:MM:SS.
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def file_locator(input_folder: str, pattern: str = "**/*_RGB.tif") -> str:
    """
    Recursively search the input folder for a file with a specified name pattern and/or extension, e.g. '**/*_RGB.tif'.

    Args:
        input_folder (str): Path to the folder in which to search.
        pattern (str): Recursive filename pattern to match.
            Defaults to `"**/*_RGB.tif"`.

    Returns:
        str: Normalized path to the matching file.
    """
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    search_pattern = os.path.join(input_folder, pattern)
    matches = glob.glob(search_pattern, recursive=True)

    files = [
        os.path.normpath(path)
        for path in matches
        if os.path.isfile(path)
    ]

    if not files:
        raise FileNotFoundError(
            f"No TIFF file ending with 'RGB.tif' found in: {input_folder}"
        )

    if len(files) > 1:
        raise RuntimeError(
            f"More than one matching file with the pattern {pattern} found:\n" + "\n".join(files)
        )

    return files[0]
