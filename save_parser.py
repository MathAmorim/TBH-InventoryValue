import os
import json
from typing import Any, Dict, List, Set, Tuple

# AES-CBC decryption imports
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Active grades to display (Legendary and above)
LEGENDARY_GRADES = {
    "LEGENDARY",
    "IMMORTAL",
    "ARCANA",
    "BEYOND",
    "CELESTIAL",
    "DIVINE",
    "COSMIC"
}

class SaveParser:
    def __init__(self, items_db_path: str = "items.json"):
        self.items_db_path = items_db_path
        self.items_db: Dict[int, Dict[str, Any]] = {}
        self.load_items_db()

    def load_items_db(self) -> None:
        """Loads the database of all items from items.json."""
        if os.path.exists(self.items_db_path):
            try:
                with open(self.items_db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Create a fast lookup map: ID -> Item Metadata
                    self.items_db = {item["id"]: item for item in data if "id" in item}
            except Exception as e:
                print(f"[ERROR] Failed to load items database: {e}")

    def decrypt_es3_file(self, file_path: str, password: str = "emuMqG3bLYJ938ZDCfieWJ") -> Dict[str, Any] | None:
        """Decrypts a Unity ES3 encrypted save file using AES-CBC."""
        try:
            if not os.path.exists(file_path):
                return None
            
            # Read encrypted bytes
            with open(file_path, "rb") as f:
                data = f.read()
                
            if len(data) < 32:
                return None
                
            iv = data[:16]
            ciphertext = data[16:]
            
            # Derive PBKDF2 key using SHA1 (matching Easy Save 3 defaults)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA1(),
                length=16,
                salt=iv,
                iterations=100,
                backend=default_backend()
            )
            key = kdf.derive(password.encode('utf-8'))
            
            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            pad_len = decrypted_bytes[-1]
            if 1 <= pad_len <= 16:
                decrypted_bytes = decrypted_bytes[:-pad_len]
                
            decrypted_text = decrypted_bytes.decode('utf-8', errors='ignore')
            return json.loads(decrypted_text)
        except Exception as e:
            print(f"[ERROR] Decrypting save file failed: {e}")
            return None

    def get_active_item_uids(self, player_data: Dict[str, Any]) -> Set[int]:
        """
        Extracts all unique item IDs currently in active possession:
        - inventorySaveDatas (active slots in player inventory)
        - stashSaveDatas (active slots in player stash)
        - heroSaveDatas (active items equipped on heroes)
        """
        active_uids = set()

        # 1. Inventory slots
        inventory_slots = player_data.get("inventorySaveDatas", [])
        for slot in inventory_slots:
            uid = slot.get("ItemUniqueId")
            if uid and uid != 0:
                active_uids.add(uid)

        # 2. Stash slots
        stash_slots = player_data.get("stashSaveDatas", [])
        for slot in stash_slots:
            uid = slot.get("ItemUniqueId")
            if uid and uid != 0:
                active_uids.add(uid)

        # 3. Hero equipped items
        heroes = player_data.get("heroSaveDatas", [])
        for hero in heroes:
            equipped_ids = hero.get("equippedItemIds", [])
            for uid in equipped_ids:
                if uid and uid != 0:
                    active_uids.add(uid)

        return active_uids

    def parse_inventory(self, save_file_path: str) -> List[Dict[str, Any]]:
        """
        Decrypts the save file, retrieves the player inventory/stash, 
        and groups them by ItemKey (showing Legendary and above).
        """
        save_data = self.decrypt_es3_file(save_file_path)
        if not save_data:
            return []

        player_save_str = save_data.get("PlayerSaveData", {}).get("value", "")
        if not player_save_str:
            return []

        try:
            player_data = json.loads(player_save_str)
        except Exception as e:
            print(f"[ERROR] Failed to parse PlayerSaveData JSON: {e}")
            return []

        active_uids = self.get_active_item_uids(player_data)
        item_save_datas = player_data.get("itemSaveDatas", [])

        # Group items in active possession by ItemKey
        grouped_items: Dict[int, List[Dict[str, Any]]] = {}
        for item in item_save_datas:
            uid = item.get("UniqueId")
            if uid in active_uids:
                item_key = item.get("ItemKey")
                if item_key is not None:
                    grouped_items.setdefault(item_key, []).append(item)

        parsed_inventory = []
        for item_key, items_list in grouped_items.items():
            db_info = self.items_db.get(item_key)
            if not db_info:
                # Fallback if item is not in items.json
                continue
                
            grade = db_info.get("grade", "COMMON").upper()
            if grade not in LEGENDARY_GRADES:
                # Filter out items below Legendary
                continue

            name_dict = db_info.get("name", {})
            name = name_dict.get("en-US", name_dict.get("en", f"Item {item_key}"))
            level = db_info.get("level")

            parsed_inventory.append({
                "item_key": item_key,
                "name": name,
                "grade": grade,
                "level": level if level is not None else 1,
                "quantity": len(items_list),
                "unique_ids": [it.get("UniqueId") for it in items_list]
            })

        # Sort the output by name for cleanliness
        parsed_inventory.sort(key=lambda x: x["name"])
        return parsed_inventory
