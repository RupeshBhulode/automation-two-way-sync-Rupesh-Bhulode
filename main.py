import os
import time
import json
import logging
from dotenv import load_dotenv

from lead_client import GoogleSheetClient
from task_client import TrelloClient
from sync_logic import sync_sheet_to_trello, sync_trello_to_sheet

load_dotenv()


DATA_JSON_PATH = os.getenv("DATA_JSON_PATH", "data.json")


POLL_INTERVAL = int(os.getenv("POLL_INTERVAL"))


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sync")


def load_state(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"mappings": {}}
    except json.JSONDecodeError:
        return {"mappings": {}}


def save_state(path, state):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def main():
    sheet = GoogleSheetClient()
    trello = TrelloClient()
    trello.ensure_list_map(["TODO", "INPROGRESS", "DONE"])

    state = load_state(DATA_JSON_PATH)
    mappings = state.setdefault("mappings", {}) 

    logger.info("Starting two-way sync loop (title=name, desc=email/note/source). Poll interval %s seconds",
                POLL_INTERVAL)
    
    while True:
        try:
            sync_sheet_to_trello(sheet, trello, mappings, state, save_state, DATA_JSON_PATH)
            sync_trello_to_sheet(sheet, trello, mappings, state, save_state, DATA_JSON_PATH)

        except Exception as e:
            logger.exception("Error during sync loop: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()