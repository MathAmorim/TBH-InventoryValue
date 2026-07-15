import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List

class HistoryManager:
    def __init__(self, file_path: str = "history.json"):
        self.file_path = file_path
        self.history: List[Dict[str, Any]] = []
        self.load_history()

    def load_history(self) -> None:
        """Loads value history from history.json."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def save_history(self) -> None:
        """Saves value history to history.json."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save history: {e}")

    def add_entry(self, value_usd: float) -> bool:
        """
        Adds a new valuation record in USD to the history.
        Returns True if a new entry was appended, False if skipped as redundant.
        """
        now = time.time()
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Check last entry to avoid duplicate noise (same value within 10 minutes)
        if self.history:
            last_entry = self.history[-1]
            last_time = last_entry.get("timestamp", 0.0)
            last_val = last_entry.get("total_value_usd", 0.0)
            
            if abs(last_val - value_usd) < 0.001 and (now - last_time < 600):
                return False
                
        self.history.append({
            "timestamp": now,
            "date": date_str,
            "total_value_usd": round(value_usd, 2)
        })
        self.save_history()
        return True

    def get_entries(self) -> List[Dict[str, Any]]:
        """Returns the list of all valuation records."""
        return self.history
