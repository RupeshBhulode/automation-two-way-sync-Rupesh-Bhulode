import os
import requests
from typing import Dict, Optional, List
from dotenv import load_dotenv
import re

load_dotenv()

API_KEY = os.getenv("TRELLO_API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
BOARD_ID = os.getenv("TRELLO_BOARD_ID")
BASE = "https://api.trello.com/1"

if not (API_KEY and TOKEN and BOARD_ID):
    raise RuntimeError("Set TRELLO_API_KEY, TRELLO_TOKEN and BOARD_ID (or TRELLO_BOARD_ID) in env or file")


class TrelloClient:
    def __init__(self, api_key=API_KEY, token=TOKEN, board_id=BOARD_ID):
        self.key = api_key
        self.token = token
        self.board_id = board_id
        self.lists = {}  

    def _get(self, path, params=None):
        if params is None:
            params = {}
        params.update({"key": self.key, "token": self.token})
        url = f"{BASE}{path}"
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, path, data=None):
        if data is None:
            data = {}
        data.update({"key": self.key, "token": self.token})
        url = f"{BASE}{path}"
        r = requests.post(url, data=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _put(self, path, data=None):
        if data is None:
            data = {}
        data.update({"key": self.key, "token": self.token})
        url = f"{BASE}{path}"
        r = requests.put(url, data=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_lists_by_name(self) -> Dict[str, str]:
        lists = self._get(f"/boards/{self.board_id}/lists")
        name_map = {}
        for l in lists:
            name = (l.get("name") or "").strip().lower()
            name_map[name] = l.get("id")
        self.lists = name_map
        return name_map

    def ensure_list_map(self, required_names: List[str]):
        self.get_lists_by_name()
        for name in required_names:
            lname = name.lower().strip()
            if lname not in self.lists:
                data = {"name": name, "idBoard": self.board_id, "pos": "bottom"}
                created = self._post("/lists", data)
                self.lists[lname] = created.get("id")
        return self.lists

    def create_card(self, list_name: str, card_name: str, desc: str = "") -> str:
        lname = list_name.lower().strip()
        if not self.lists:
            self.get_lists_by_name()
        if lname not in self.lists:
            raise RuntimeError(f"Trello list '{list_name}' not found on board {self.board_id}")
        list_id = self.lists[lname]
        data = {"name": card_name, "idList": list_id, "desc": desc}
        card = self._post("/cards", data)
        return card.get("id")

    def get_card(self, card_id: str) -> dict:
        return self._get(f"/cards/{card_id}")

    def update_card_name(self, card_id: str, new_name: str) -> dict:
        return self._put(f"/cards/{card_id}", data={"name": new_name})

    def update_card_fields(self, card_id: str, new_fields: Dict[str, str]) -> dict:
        card = self.get_card(card_id)
        current_desc = card.get("desc") or ""
        parsed = self.parse_desc_to_fields(current_desc)

        for k, v in new_fields.items():
            if v is None:
                continue
            parsed[k.strip().lower()] = str(v).strip()

        canon = {}
        if "email" in parsed:
            canon["Email"] = parsed["email"]
        if "note" in parsed:
            canon["Note"] = parsed["note"]
        if "source" in parsed:
            canon["Source"] = parsed["source"]

        new_desc = self.render_fields_to_desc(canon)
        return self._put(f"/cards/{card_id}", data={"desc": new_desc})

    def move_card(self, card_id: str, dest_list_name: str) -> dict:
        if not self.lists:
            self.get_lists_by_name()
        lname = dest_list_name.lower().strip()
        if lname not in self.lists:
            raise RuntimeError(f"Destination list '{dest_list_name}' not found")
        dest_list_id = self.lists[lname]
        return self._put(f"/cards/{card_id}", data={"idList": dest_list_id})

    def get_cards_on_board(self) -> List[dict]:
        return self._get(f"/boards/{self.board_id}/cards")

    def archive_card(self, card_id: str) -> dict:
        return self._put(f"/cards/{card_id}", data={"closed": "true"})

    def render_fields_to_desc(self, fields: Dict[str, str]) -> str:
        parts = []
        if any(k.lower() == "email" for k in fields.keys()):
            parts.append(f"Email: {fields.get('email') or fields.get('Email')}")
        if any(k.lower() == "note" for k in fields.keys()):
            parts.append(f"Note: {fields.get('note') or fields.get('Note')}")
        if any(k.lower() == "source" for k in fields.keys()):
            parts.append(f"Source: {fields.get('source') or fields.get('Source')}")
        return "\n".join([p for p in parts if p is not None])

    

    def parse_desc_to_fields(self, desc: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if not desc:
            return result

        for line in desc.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            k = key.strip().lower()
            v = val.strip()
            if v == "":
                continue
            if k == "email":
               result[k] = self.extract_email(v)   
            elif k in ("note", "source"):
               result[k] = v 
        return result

    def extract_email(self,text: str) -> str:
       m = re.search(r'([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})', text)
       return m.group(1) if m else text