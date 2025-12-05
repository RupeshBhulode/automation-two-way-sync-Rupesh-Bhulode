import os
from typing import List, Dict, Optional, Any
import gspread
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
SHEET_ID = os.getenv("SHEET_ID")

class GoogleSheetClient:
    def __init__(self, credentials_file: str = CREDENTIALS_FILE, sheet_id: str = SHEET_ID):
        if not credentials_file or not sheet_id:
            raise RuntimeError("Please set CREDENTIALS_FILE and SHEET_ID in env")
        self.gc = gspread.service_account(filename=credentials_file)
        self.sheet = self.gc.open_by_key(sheet_id)
        self.ws = self.sheet.get_worksheet(0)

    def read_rows(self) -> List[Dict[str, Any]]:
        records = self.ws.get_all_records(empty2zero=False)
        normalized = []
        for r in records:
            norm = {}
            for k, v in r.items():
                norm[k.strip().lower()] = v
            normalized.append(norm)
        return normalized

    def append_row(self, row: List[Any]):
        self.ws.append_row([str(x) for x in row])

    def find_row_index_by_id(self, sheet_id_value: str) -> Optional[int]:
        
        header = self.ws.row_values(1)
        id_col = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "id":
                id_col = idx
                break
        if id_col is None:
            return None

        col_vals = self.ws.col_values(id_col)
        for row_idx, cell_val in enumerate(col_vals, start=1):
            if row_idx == 1: 
                continue
            if cell_val is not None and str(cell_val).strip() == str(sheet_id_value).strip():
                return row_idx
        return None

    def update_category_by_row_index(self, row_index: int, new_category: str):
        header = self.ws.row_values(1)
        col_index = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "category":
                col_index = idx
                break
        if col_index is None:
            raise RuntimeError("Sheet has no 'category' header")
        self.ws.update_cell(row_index, col_index, new_category)

    def update_name_by_row_index(self, row_index: int, new_name: str):
        header = self.ws.row_values(1)
        col_index = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "name":
                col_index = idx
                break
        if col_index is None:
            raise RuntimeError("Sheet has no 'name' header")
        self.ws.update_cell(row_index, col_index, new_name)

    def update_email_by_row_index(self, row_index: int, new_email: str):
        header = self.ws.row_values(1)
        col_index = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "email":
                col_index = idx
                break
        if col_index is None:
            raise RuntimeError("Sheet has no 'email' header")
        self.ws.update_cell(row_index, col_index, new_email)

    def update_note_by_row_index(self, row_index: int, new_note: str):
        header = self.ws.row_values(1)
        col_index = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "note":
                col_index = idx
                break
        if col_index is None:
            raise RuntimeError("Sheet has no 'note' header")
        self.ws.update_cell(row_index, col_index, new_note)

    def update_source_by_row_index(self, row_index: int, new_source: str):
        header = self.ws.row_values(1)
        col_index = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().lower() == "source":
                col_index = idx
                break
        if col_index is None:
            raise RuntimeError("Sheet has no 'source' header")
        self.ws.update_cell(row_index, col_index, new_source)