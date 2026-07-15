import os
import json
import time
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

# Currencies mapping
SUPPORTED_CURRENCIES = {
    "USD": {"id": 1, "symbol": "$", "format": "${:.2f}", "fallback_rate": 1.0},
    "BRL": {"id": 7, "symbol": "R$", "format": "R$ {:.2f}", "fallback_rate": 5.50},
    "EUR": {"id": 3, "symbol": "€", "format": "€{:.2f}", "fallback_rate": 0.92},
    "GBP": {"id": 2, "symbol": "£", "format": "£{:.2f}", "fallback_rate": 0.78},
    "CNY": {"id": 23, "symbol": "¥", "format": "¥{:.2f}", "fallback_rate": 7.25},
    "RUB": {"id": 5, "symbol": "₽", "format": "{:.2f} ₽", "fallback_rate": 90.00},
}

def parse_price_string(price_str: str) -> float:
    """Parses a localized currency string from Steam market into a numeric float."""
    if not price_str or price_str == "N/A":
        return 0.0
    
    # Extract only numbers, dots, and commas
    cleaned = "".join([c for c in price_str if c.isdigit() or c in ['.', ',']])
    if not cleaned:
        return 0.0
        
    dots = cleaned.count('.')
    commas = cleaned.count(',')
    
    try:
        if dots == 1 and commas == 0:
            return float(cleaned)
        elif commas == 1 and dots == 0:
            return float(cleaned.replace(',', '.'))
        elif commas > 0 and dots > 0:
            # Last one is decimal separator
            dot_idx = cleaned.rfind('.')
            comma_idx = cleaned.rfind(',')
            if dot_idx > comma_idx:
                return float(cleaned.replace(',', ''))
            else:
                return float(cleaned.replace('.', '').replace(',', '.'))
        else:
            return float(cleaned)
    except ValueError:
        return 0.0

class ExchangeRateManager:
    """Manages real-time exchange rates relative to USD."""
    def __init__(self):
        self.rates: Dict[str, float] = {k: v["fallback_rate"] for k, v in SUPPORTED_CURRENCIES.items()}
        self.last_fetch_time = 0.0
        self.fetch_rates()

    def fetch_rates(self) -> None:
        """Fetches latest exchange rates from open-er API."""
        now = time.time()
        # Fetch once every 6 hours
        if now - self.last_fetch_time < 6 * 3600:
            return
            
        try:
            req = urllib.request.Request(
                "https://open.er-api.com/v6/latest/USD",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("result") == "success":
                    fetched_rates = data.get("rates", {})
                    for k in self.rates.keys():
                        if k in fetched_rates:
                            self.rates[k] = fetched_rates[k]
                    self.last_fetch_time = now
        except Exception as e:
            print(f"[WARNING] Exchange rate fetch failed, using fallbacks: {e}")

    def convert(self, amount: float, from_curr: str, to_curr: str) -> float:
        """Converts an amount from one currency to another using active rates."""
        self.fetch_rates()
        if from_curr not in self.rates or to_curr not in self.rates:
            return amount
        # Convert to USD base, then to target
        amount_usd = amount / self.rates[from_curr]
        return amount_usd * self.rates[to_curr]

class SteamPriceWorker(QThread):
    """Asynchronous worker that fetches Steam prices sequentially to respect rate limits."""
    progress = pyqtSignal(int, int, str, str)  # current_idx, total_count, item_name, price_str
    finished = pyqtSignal(dict, bool)  # results dict, rate_limit_hit flag

    def __init__(self, item_names: List[str], currency_code: str, cache_file_path: str = "market_cache.json"):
        super().__init__()
        self.item_names = list(set(item_names))  # Unique item names
        self.currency_code = currency_code
        self.cache_file_path = cache_file_path
        self.cache: Dict[str, Any] = {}
        self.load_cache()

    def load_cache(self) -> None:
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if it's flat format (e.g. keys are item names instead of currency codes)
                is_flat = False
                for k, v in data.items():
                    if isinstance(v, dict) and "price" in v:
                        is_flat = True
                        break
                
                if is_flat:
                    # Migrate to BRL since the original cache was BRL
                    self.cache = {"BRL": data}
                else:
                    self.cache = data
            except Exception:
                self.cache = {}

    def save_cache(self) -> None:
        try:
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save market cache: {e}")

    def get_cached_price(self, item_name: str, ignore_age: bool = False) -> str | None:
        """Returns the price from cache if it is fresh (< 12 hours) or if ignore_age is True."""
        curr_cache = self.cache.setdefault(self.currency_code, {})
        if item_name in curr_cache:
            entry = curr_cache[item_name]
            cached_time = entry.get("timestamp", 0.0)
            if ignore_age or (time.time() - cached_time < 12 * 3600):
                return entry.get("price", "N/A")
        return None

    def cache_price(self, item_name: str, price: str) -> None:
        curr_cache = self.cache.setdefault(self.currency_code, {})
        curr_cache[item_name] = {
            "price": price,
            "timestamp": time.time()
        }
        self.save_cache()

    def run(self) -> None:
        results = {}
        total = len(self.item_names)
        currency_id = SUPPORTED_CURRENCIES.get(self.currency_code, {"id": 1})["id"]

        rate_limit_active = False

        for idx, name in enumerate(self.item_names):
            # Check cache first (enforcing 12-hour age limit)
            cached = self.get_cached_price(name)
            if cached is not None:
                results[name] = cached
                self.progress.emit(idx + 1, total, name, cached)
                continue

            # If rate limit was hit, use stale cache price if available, otherwise "N/A"
            if rate_limit_active:
                stale_price = self.get_cached_price(name, ignore_age=True) or "N/A"
                results[name] = stale_price
                self.progress.emit(idx + 1, total, name, stale_price)
                continue

            # Fetch from Steam API
            price_str = "N/A"
            network_called = False
            try:
                encoded_name = urllib.parse.quote(name)
                url = f"https://steamcommunity.com/market/priceoverview/?appid=3678970&currency={currency_id}&market_hash_name={encoded_name}"
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    network_called = True
                    if data.get("success"):
                        price_str = data.get("lowest_price", data.get("median_price", "N/A"))
            except Exception as e:
                price_str = "N/A"
                if hasattr(e, 'code') and getattr(e, 'code') == 429:
                    rate_limit_active = True
                    # Fallback immediately to stale cache if available
                    price_str = self.get_cached_price(name, ignore_age=True) or "N/A"

            # Cache the result only if it's a successful network lookup or a non-rate-limit "N/A"
            if not rate_limit_active or price_str != "N/A":
                self.cache_price(name, price_str)

            results[name] = price_str
            self.progress.emit(idx + 1, total, name, price_str)

            # Introduce delay to avoid steam rate-limit (1.2 seconds, only if we actually hit the network)
            if network_called and not rate_limit_active:
                time.sleep(1.2)

        self.finished.emit(results, rate_limit_active)
