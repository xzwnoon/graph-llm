import json
import logging
import sys

def setup_logger():
    """
    Configures a basic console logger for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(module)s.py] - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_json(filepath: str) -> dict | None:
    """
    Loads a JSON file from the given path.

    Args:
        filepath: The path to the JSON file.

    Returns:
        A dictionary representation of the JSON, or None if an error occurs.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"JSON file not found at path: {filepath}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {filepath}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while loading JSON from {filepath}: {e}")
        return None
