import os
import json
import time
from typing import Any, Dict, List, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QStackedWidget, QSizePolicy,
    QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize, QTimer
from PyQt6.QtGui import QPixmap, QColor, QFont, QIcon

from save_parser import SaveParser
from steam_market import SteamPriceWorker, ExchangeRateManager, SUPPORTED_CURRENCIES, parse_price_string
from history_manager import HistoryManager
from custom_chart import HistoryChartWidget

# Color constants
COLOR_BG = "#0b0b0b"
COLOR_FRAME = "#141414"
COLOR_PRIMARY = "#c8a24b"
COLOR_HOVER = "#f2c94c"
COLOR_SECONDARY = "#1d1d1d"
COLOR_SEC_HOVER = "#2a2a2a"
COLOR_TEXT = "#e8e8e8"
COLOR_MUTED = "#b8b8b8"
COLOR_ENTRY_BG = "#111111"
COLOR_BORDER = "#2f2f2f"

GRADE_COLORS = {
    "COMMON": "#e4e4e4",
    "UNCOMMON": "#54fc0c",
    "RARE": "#2f8bfc",
    "LEGENDARY": "#fc9c0c",
    "IMMORTAL": "#fc2424",
    "ARCANA": "#b40cfc",
    "BEYOND": "#fc246c",
    "CELESTIAL": "#6ccce4",
    "DIVINE": "#fce454",
    "COSMIC": "#fcfcfc",
}

GRADE_ORDER = {
    "COMMON": 1,
    "UNCOMMON": 2,
    "RARE": 3,
    "LEGENDARY": 4,
    "IMMORTAL": 5,
    "ARCANA": 6,
    "BEYOND": 7,
    "CELESTIAL": 8,
    "DIVINE": 9,
    "COSMIC": 10
}

class SpriteLoader:
    def __init__(self, mapping_path: str = "id_to_sprite.json", sprites_dir: str = "cache_sprites"):
        self.sprites_dir = sprites_dir
        self.mapping: Dict[str, str] = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    self.mapping = json.load(f)
            except Exception:
                pass

    def get_sprite_path(self, item_key: int) -> str:
        s_key = str(item_key)
        sprite_name = self.mapping.get(s_key)
        if not sprite_name:
            if s_key.startswith('910'):
                sprite_name = "Item_910011.png"
            elif s_key.startswith('920'):
                sprite_name = "Item_920011.png"
            elif s_key.startswith('930'):
                sprite_name = "Item_930011.png"
            else:
                sprite_name = f"Item_{item_key}.png"
        
        path = os.path.join(self.sprites_dir, sprite_name)
        if os.path.exists(path):
            return path
        return ""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Bar Hero - Inventory Value")
        self.resize(1100, 800)

        # Core systems
        self.parser = SaveParser()
        self.history_mgr = HistoryManager()
        self.rate_mgr = ExchangeRateManager()
        self.sprite_loader = SpriteLoader()

        # Session properties
        self.save_file_path = ""
        self.active_currency = "BRL"
        self.view_mode = "list"  # 'list' or 'grid'
        self.current_parsed_inventory: List[Dict[str, Any]] = []
        self.resolved_prices: Dict[str, str] = {}
        self.is_fetching = False

        # Load configurations
        self.load_config()

        # Init UI elements
        self.init_ui()

        # Update initial valuation on startup
        QTimer.singleShot(100, self.refresh_data)

    def load_config(self) -> None:
        """Loads app settings from config.json."""
        config_path = "config.json"
        default_path = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\TesseractStudio\TaskbarHero\SaveFile_Live.es3")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.save_file_path = cfg.get("save_file_path", default_path)
                    self.active_currency = cfg.get("currency", "BRL")
                    self.view_mode = cfg.get("view_mode", "list")
            except Exception:
                self.save_file_path = default_path
        else:
            self.save_file_path = default_path
            self.save_config()

    def save_config(self) -> None:
        """Saves active configurations to config.json."""
        config_path = "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "save_file_path": self.save_file_path,
                    "currency": self.active_currency,
                    "view_mode": self.view_mode
                }, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

    def init_ui(self) -> None:
        # Central Widget & Main Vertical Layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ----------------- HEADER PANEL -----------------
        header_widget = QFrame()
        header_widget.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Save File Path Section
        path_layout = QHBoxLayout()
        path_layout.setSpacing(5)
        path_label = QLabel("Save File:")
        path_label.setStyleSheet("font-weight: bold; color: #c8a24b;")
        self.path_edit = QLineEdit(self.save_file_path)
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Select SaveFile_Live.es3...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_save_file)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        header_layout.addLayout(path_layout, stretch=4)

        # Currency Selection
        curr_layout = QHBoxLayout()
        curr_layout.setSpacing(5)
        curr_label = QLabel("Currency:")
        curr_label.setStyleSheet("font-weight: bold; color: #c8a24b;")
        self.curr_combo = QComboBox()
        self.curr_combo.addItems(list(SUPPORTED_CURRENCIES.keys()))
        self.curr_combo.setCurrentText(self.active_currency)
        self.curr_combo.currentTextChanged.connect(self.on_currency_changed)
        
        curr_layout.addWidget(curr_label)
        curr_layout.addWidget(self.curr_combo)
        header_layout.addLayout(curr_layout, stretch=1)

        # Sorting Selection
        sort_layout = QHBoxLayout()
        sort_layout.setSpacing(5)
        sort_label = QLabel("Sort By:")
        sort_label.setStyleSheet("font-weight: bold; color: #c8a24b;")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Quality",
            "Quantity",
            "Total Value",
            "Name",
            "Level"
        ])
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        header_layout.addLayout(sort_layout, stretch=1)

        # Controls Buttons
        self.toggle_view_btn = QPushButton("Grid View" if self.view_mode == "list" else "List View")
        self.toggle_view_btn.clicked.connect(self.toggle_view_mode)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: #0b0b0b; border-color: {COLOR_PRIMARY};")
        self.refresh_btn.clicked.connect(self.refresh_data)

        header_layout.addWidget(self.toggle_view_btn)
        header_layout.addWidget(self.refresh_btn)
        self.main_layout.addWidget(header_widget)

        # ----------------- OVERVIEW METRICS PANEL -----------------
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.card_value = self.create_metric_card("Total Value", "-")
        self.card_items = self.create_metric_card("Legendary+ Items", "-")
        self.card_pinned = self.create_metric_card("Top 3 Items Value", "-")
        self.card_change = self.create_metric_card("24h Change", "-")

        metrics_layout.addWidget(self.card_value)
        metrics_layout.addWidget(self.card_items)
        metrics_layout.addWidget(self.card_pinned)
        metrics_layout.addWidget(self.card_change)
        self.main_layout.addLayout(metrics_layout)

        # ----------------- TABS SYSTEM -----------------
        self.tabs = QTabWidget()
        
        # TAB 1: Inventory
        self.tab_inventory = QWidget()
        tab_inv_layout = QVBoxLayout(self.tab_inventory)
        tab_inv_layout.setContentsMargins(10, 10, 10, 10)
        tab_inv_layout.setSpacing(12)

        # ----------------- PINNED ITEMS SECTION -----------------
        self.pinned_frame = QFrame()
        self.pinned_frame.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; border-radius: 8px; background-color: {COLOR_FRAME};")
        self.pinned_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        pinned_layout = QVBoxLayout(self.pinned_frame)
        pinned_layout.setContentsMargins(12, 5, 12, 5)
        pinned_layout.setSpacing(5)

        pinned_title = QLabel("Top 3 Most Expensive Items")
        pinned_title.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY}; font-size: 14px; border: none; background: transparent;")
        pinned_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pinned_layout.addWidget(pinned_title)

        self.pinned_cards_layout = QHBoxLayout()
        self.pinned_cards_layout.setSpacing(10)
        pinned_layout.addLayout(self.pinned_cards_layout)
        tab_inv_layout.addWidget(self.pinned_frame, stretch=0)

        # ----------------- STACKED INVENTORY VIEWS -----------------
        self.view_stack = QStackedWidget(self)
        
        # View 1: List Table View
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setHorizontalHeaderLabels([
            "Icon", "Name", "Level", "Quality", "Unit Price", "Quantity", "Total Value"
        ])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setAlternatingRowColors(True)
        self.view_stack.addWidget(self.table_widget)

        # View 2: Scrollable Grid View
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: #0b0b0b; border: none;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(12)
        self.grid_scroll.setWidget(self.grid_container)
        self.view_stack.addWidget(self.grid_scroll)

        tab_inv_layout.addWidget(self.view_stack, stretch=1)
        self.tabs.addTab(self.tab_inventory, "Inventory")

        # TAB 2: History Chart
        self.tab_history = QWidget()
        tab_hist_layout = QVBoxLayout(self.tab_history)
        tab_hist_layout.setContentsMargins(10, 10, 10, 10)
        
        # ----------------- CHART MODULE -----------------
        self.chart_widget = HistoryChartWidget(self)
        self.chart_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tab_hist_layout.addWidget(self.chart_widget)
        self.tabs.addTab(self.tab_history, "History")

        self.main_layout.addWidget(self.tabs)

        # Set active stack view
        self.view_stack.setCurrentIndex(0 if self.view_mode == "list" else 1)

        # ----------------- STATUS FOOTER PANEL -----------------
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("color: #b8b8b8; font-size: 11px;")
        footer_layout.addWidget(self.status_label)
        self.main_layout.addLayout(footer_layout)

        # Apply central stylesheet
        self.apply_theme_styles()

    def create_metric_card(self, title: str, val: str) -> QFrame:
        """Helper to create standard summary value frames."""
        card = QFrame()
        card.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; border-radius: 6px; background-color: {COLOR_FRAME};")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #b8b8b8; font-size: 11px; border: none; background: transparent;")
        lbl_val = QLabel(val)
        lbl_val.setStyleSheet("color: #e8e8e8; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        
        card.setProperty("title_lbl", lbl_title)
        card.setProperty("value_lbl", lbl_val)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card

    def apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_TEXT};
                font-family: 'Segoe UI', sans-serif;
            }}
            QFrame#HeaderFrame {{
                border-bottom: 1px solid {COLOR_BORDER};
                padding-bottom: 5px;
            }}
            QLineEdit {{
                background-color: {COLOR_ENTRY_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 6px 10px;
                color: {COLOR_TEXT};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_PRIMARY};
            }}
            QPushButton {{
                background-color: {COLOR_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SEC_HOVER};
                border-color: {COLOR_PRIMARY};
            }}
            QComboBox {{
                background-color: {COLOR_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 5px 25px 5px 10px;
                color: {COLOR_TEXT};
            }}
            QComboBox:hover {{
                border-color: {COLOR_PRIMARY};
            }}
            QTableWidget {{
                background-color: {COLOR_FRAME};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                gridline-color: {COLOR_BORDER};
                alternate-background-color: #1a1a1a;
            }}
            QHeaderView::section {{
                background-color: #181818;
                color: {COLOR_PRIMARY};
                padding: 7px;
                border: none;
                border-bottom: 1px solid {COLOR_BORDER};
                font-weight: bold;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {COLOR_BG};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLOR_PRIMARY};
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                background: {COLOR_BG};
                border-radius: 6px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: {COLOR_FRAME};
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 16px;
                margin-right: 2px;
                font-weight: bold;
                color: {COLOR_MUTED};
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background: {COLOR_SECONDARY};
                color: {COLOR_PRIMARY};
                border-bottom: 2px solid {COLOR_PRIMARY};
            }}
        """)

    def browse_save_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SaveFile_Live.es3",
            os.path.dirname(self.save_file_path) if self.save_file_path else "",
            "ES3 Save Files (*.es3);;All Files (*)"
        )
        if path:
            self.save_file_path = os.path.normpath(path)
            self.path_edit.setText(self.save_file_path)
            self.save_config()
            self.refresh_data()

    def on_currency_changed(self, currency: str) -> None:
        self.active_currency = currency
        self.save_config()
        self.refresh_data()

    def toggle_view_mode(self) -> None:
        if self.view_mode == "list":
            self.view_mode = "grid"
            self.toggle_view_btn.setText("List View")
            self.view_stack.setCurrentIndex(1)
        else:
            self.view_mode = "list"
            self.toggle_view_btn.setText("Grid View")
            self.view_stack.setCurrentIndex(0)
        self.save_config()
        self.render_inventory()

    def on_sort_changed(self, text: str) -> None:
        self.render_inventory()

    def get_sorted_inventory(self) -> List[Dict[str, Any]]:
        sort_type = self.sort_combo.currentText()
        inv_copy = list(self.current_parsed_inventory)
        
        if sort_type == "Quality":
            # Best to worst
            inv_copy.sort(key=lambda x: GRADE_ORDER.get(x["grade"], 0), reverse=True)
        elif sort_type == "Quantity":
            # High to low
            inv_copy.sort(key=lambda x: x.get("quantity", 0), reverse=True)
        elif sort_type == "Total Value":
            # Total value high to low
            inv_copy.sort(key=lambda x: x.get("total_price_val", 0.0), reverse=True)
        elif sort_type == "Name":
            # Alphabetical A-Z
            inv_copy.sort(key=lambda x: x["name"].lower())
        elif sort_type == "Level":
            # High to low
            inv_copy.sort(key=lambda x: x.get("level", 1), reverse=True)
            
        return inv_copy

    def update_status(self, text: str) -> None:
        self.status_label.setText(f"Status: {text}")

    def refresh_data(self) -> None:
        """Parses the save file and starts fetching price updates from Steam Community Market."""
        if self.is_fetching:
            return

        if not self.save_file_path or not os.path.exists(self.save_file_path):
            self.update_status("Save file not found. Select a valid path.")
            return

        self.update_status("Parsing save file...")
        self.current_parsed_inventory = self.parser.parse_inventory(self.save_file_path)
        
        if not self.current_parsed_inventory:
            self.update_status("No legendary or above items found in save file.")
            self.render_inventory()
            self.update_overview(0.0)
            return

        # Extract item names to query prices
        item_names = [item["name"] for item in self.current_parsed_inventory]
        
        # Start background worker thread
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.curr_combo.setEnabled(False)
        
        self.worker = SteamPriceWorker(item_names, self.active_currency)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    @pyqtSlot(int, int, str, str)
    def on_worker_progress(self, current: int, total: int, item_name: str, price_str: str) -> None:
        self.resolved_prices[item_name] = price_str
        self.update_status(f"Fetching Steam prices ({current}/{total}): {item_name} -> {price_str}")

    @pyqtSlot(dict, bool)
    def on_worker_finished(self, prices: Dict[str, str], rate_limited: bool) -> None:
        self.is_fetching = False
        self.refresh_btn.setEnabled(True)
        self.curr_combo.setEnabled(True)
        self.resolved_prices.update(prices)
        if rate_limited:
            self.status_label.setStyleSheet("color: #fc9c0c; font-size: 11px;")
            self.update_status("Done (Steam rate-limit block detected! Using cached prices).")
        else:
            self.status_label.setStyleSheet("color: #b8b8b8; font-size: 11px;")
            self.update_status("Prices loaded successfully.")

        # Compute total inventory value in USD
        total_usd = 0.0
        currency_info = SUPPORTED_CURRENCIES.get(self.active_currency, {"fallback_rate": 1.0})
        exchange_rate = self.rate_mgr.rates.get(self.active_currency, currency_info["fallback_rate"])

        for item in self.current_parsed_inventory:
            price_str = self.resolved_prices.get(item["name"], "N/A")
            num_price = parse_price_string(price_str)
            item["unit_price_val"] = num_price
            item["total_price_val"] = num_price * item["quantity"]
            
            # Convert target currency value back to USD base for history tracking
            item_val_usd = (num_price * item["quantity"]) / exchange_rate
            total_usd += item_val_usd

        # Save valuation to history
        self.history_mgr.add_entry(total_usd)

        # Draw chart and refresh UI elements
        self.update_overview(total_usd)
        self.render_inventory()

    def update_overview(self, total_usd: float) -> None:
        """Updates summary metric cards and chart visualization."""
        curr_info = SUPPORTED_CURRENCIES.get(self.active_currency, {"symbol": "$", "fallback_rate": 1.0})
        rate = self.rate_mgr.rates.get(self.active_currency, curr_info["fallback_rate"])
        
        # 1. Total inventory value
        total_val_converted = total_usd * rate
        self.card_value.property("value_lbl").setText(f"{curr_info['symbol']}{total_val_converted:.2f}")

        # 2. Legendary+ Item count
        total_items = sum(item["quantity"] for item in self.current_parsed_inventory)
        self.card_items.property("value_lbl").setText(str(total_items))

        # 3. Value of Pinned Items
        # Sort current inventory descending by unit price to identify most expensive items
        sorted_inv = sorted(self.current_parsed_inventory, key=lambda x: x.get("unit_price_val", 0.0), reverse=True)
        top_3 = sorted_inv[:3]
        pinned_value = sum(item.get("total_price_val", 0.0) for item in top_3)
        self.card_pinned.property("value_lbl").setText(f"{curr_info['symbol']}{pinned_value:.2f}")

        # 4. 24h Change calculation
        diff_usd, pct_change = self.calculate_24h_change(total_usd)
        change_lbl = self.card_change.property("value_lbl")
        
        if pct_change > 0:
            change_lbl.setText(f"+{pct_change:.2f}%")
            change_lbl.setStyleSheet("color: #2ecc71; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        elif pct_change < 0:
            change_lbl.setText(f"{pct_change:.2f}%")
            change_lbl.setStyleSheet("color: #e74c3c; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        else:
            change_lbl.setText("0.00%")
            change_lbl.setStyleSheet("color: #b8b8b8; font-size: 20px; font-weight: bold; border: none; background: transparent;")

        # Update chart canvas
        self.chart_widget.set_data(self.history_mgr.get_entries(), curr_info["symbol"], rate)

    def calculate_24h_change(self, current_val_usd: float) -> Tuple[float, float]:
        """Returns (change_amount_usd, percentage_change)."""
        history = self.history_mgr.get_entries()
        if not history or len(history) < 2:
            return 0.0, 0.0
            
        now = time.time()
        target_ts = now - 86400.0  # 24 hours ago
        
        # Find entry closest to 24 hours ago
        closest_entry = history[0]
        min_diff = abs(closest_entry.get("timestamp", 0.0) - target_ts)
        
        for entry in history[:-1]:  # Exclude current newly added entry
            diff = abs(entry.get("timestamp", 0.0) - target_ts)
            if diff < min_diff:
                min_diff = diff
                closest_entry = entry
                
        val_past = closest_entry.get("total_value_usd", 0.0)
        if val_past <= 0.0:
            return 0.0, 0.0
            
        diff_usd = current_val_usd - val_past
        pct_change = (diff_usd / val_past) * 100.0
        return diff_usd, pct_change

    def get_item_pixmap(self, item_key: int, size: int = 40) -> QPixmap:
        """Loads and resizes an item sprite, downloading missing ones asynchronously."""
        path = self.sprite_loader.get_sprite_path(item_key)
        if path:
            pixmap = QPixmap(path)
        else:
            # Recreate placeholder
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor("#1d1d1d"))
            
            # Start background download thread if missing from cache
            s_key = str(item_key)
            sprite_name = self.sprite_loader.mapping.get(s_key)
            if sprite_name:
                dest_path = os.path.join(self.sprite_loader.sprites_dir, sprite_name)
                # Simple async download worker
                import urllib.request
                import threading
                def download():
                    try:
                        url = f"https://tbh.city/sprites/sharedassets0/{sprite_name}"
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = response.read()
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with open(dest_path, "wb") as f:
                            f.write(data)
                        # Redraw once loaded successfully
                        QTimer.singleShot(0, self.render_inventory)
                    except Exception:
                        pass
                threading.Thread(target=download, daemon=True).start()

        return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def get_top_3_pinned(self) -> List[Dict[str, Any]]:
        """Returns the top 3 items to pin. If prices exist, sorts by price, otherwise sorts by quality/level/qty."""
        has_prices = any(x.get("unit_price_val", 0.0) > 0.0 for x in self.current_parsed_inventory)
        if has_prices:
            # Sort by unit price descending, then quality descending, then level descending
            sorted_items = sorted(
                self.current_parsed_inventory,
                key=lambda x: (x.get("unit_price_val", 0.0), GRADE_ORDER.get(x["grade"], 0), x.get("level", 1)),
                reverse=True
            )
        else:
            # Sort by quality grade descending, then level descending, then quantity descending
            sorted_items = sorted(
                self.current_parsed_inventory,
                key=lambda x: (GRADE_ORDER.get(x["grade"], 0), x.get("level", 1), x.get("quantity", 0)),
                reverse=True
            )
        return sorted_items[:3]

    def render_inventory(self) -> None:
        """Refreshes pinned section and active inventory view (list or grid)."""
        curr_info = SUPPORTED_CURRENCIES.get(self.active_currency, {"symbol": "$"})
        
        # Select top 3 items for pinning
        top_3 = self.get_top_3_pinned()

        # 1. Update Pinned Items Section
        # Clear existing layout children
        while self.pinned_cards_layout.count():
            child = self.pinned_cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for item in top_3:
            card = self.create_pinned_item_card(item, curr_info["symbol"])
            self.pinned_cards_layout.addWidget(card)

        # If less than 3 pinned items, add stretch panels to occupy space evenly
        for _ in range(3 - len(top_3)):
            empty_panel = QFrame()
            empty_panel.setStyleSheet("border: 1px dashed #2f2f2f; background: transparent; border-radius: 6px;")
            lbl = QLabel("No Item")
            lbl.setStyleSheet("color: #7f8c8d; font-style: italic; border: none; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout = QVBoxLayout(empty_panel)
            empty_layout.addWidget(lbl)
            self.pinned_cards_layout.addWidget(empty_panel)

        # 2. Render main inventory view based on sorting selection
        sorted_inv = self.get_sorted_inventory()
        if self.view_mode == "list":
            self.render_list_view(sorted_inv, curr_info["symbol"])
        else:
            self.render_grid_view(sorted_inv, curr_info["symbol"])

    def create_pinned_item_card(self, item: Dict[str, Any], symbol: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(85)
        # Highlight card with gold border accent
        card.setStyleSheet(f"border: 1px solid {COLOR_PRIMARY}; border-radius: 6px; background-color: #181818;")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Icon Label
        img_lbl = QLabel()
        img_lbl.setPixmap(self.get_item_pixmap(item["item_key"], size=36))
        img_lbl.setFixedSize(36, 36)
        img_lbl.setStyleSheet("border: none; background: transparent;")
        
        # Info Vertical Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_lbl = QLabel(item["name"])
        name_lbl.setStyleSheet("font-weight: bold; color: #e8e8e8; font-size: 12px; border: none; background: transparent;")
        
        quality_color = GRADE_COLORS.get(item["grade"], COLOR_TEXT)
        details_text = f"Lvl {item['level']} | {item['grade'].capitalize()}"
        details_lbl = QLabel(details_text)
        details_lbl.setStyleSheet(f"color: {quality_color}; font-size: 10px; border: none; background: transparent;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(details_lbl)
        info_layout.addStretch()

        # Price Vertical Layout
        price_layout = QVBoxLayout()
        price_layout.setSpacing(2)
        
        unit_price = item.get("unit_price_val", 0.0)
        total_price = item.get("total_price_val", 0.0)
        qty = item["quantity"]

        total_lbl = QLabel(f"{symbol}{total_price:.2f}")
        total_lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY}; font-size: 13px; border: none; background: transparent;")
        total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        sub_lbl = QLabel(f"{qty} x {symbol}{unit_price:.2f}")
        sub_lbl.setStyleSheet("color: #b8b8b8; font-size: 9px; border: none; background: transparent;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        price_layout.addWidget(total_lbl)
        price_layout.addWidget(sub_lbl)
        price_layout.addStretch()

        layout.addWidget(img_lbl)
        layout.addLayout(info_layout, stretch=2)
        layout.addLayout(price_layout, stretch=1)
        return card

    def render_list_view(self, items: List[Dict[str, Any]], symbol: str) -> None:
        self.table_widget.setRowCount(0)
        self.table_widget.setRowCount(len(items))

        for row, item in enumerate(items):
            # 1. Icon Cell
            img_lbl = QLabel()
            img_lbl.setPixmap(self.get_item_pixmap(item["item_key"], size=28))
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setStyleSheet("background: transparent; border: none;")
            self.table_widget.setCellWidget(row, 0, img_lbl)

            # 2. Name Cell
            name_item = QTableWidgetItem(item["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_widget.setItem(row, 1, name_item)

            # 3. Level Cell
            level_item = QTableWidgetItem(str(item["level"]))
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table_widget.setItem(row, 2, level_item)

            # 4. Quality Cell
            quality_item = QTableWidgetItem(item["grade"].capitalize())
            quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            quality_item.setForeground(QColor(GRADE_COLORS.get(item["grade"], COLOR_TEXT)))
            self.table_widget.setItem(row, 3, quality_item)

            # 5. Unit Price Cell
            unit_price = item.get("unit_price_val", 0.0)
            unit_item = QTableWidgetItem(f"{symbol}{unit_price:.2f}")
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_widget.setItem(row, 4, unit_item)

            # 6. Quantity Cell
            qty_item = QTableWidgetItem(str(item["quantity"]))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table_widget.setItem(row, 5, qty_item)

            # 7. Total Price Cell
            total_price = item.get("total_price_val", 0.0)
            total_item = QTableWidgetItem(f"{symbol}{total_price:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setForeground(QColor(COLOR_PRIMARY))
            self.table_widget.setItem(row, 6, total_item)

    def render_grid_view(self, items: List[Dict[str, Any]], symbol: str) -> None:
        # Clear old items in grid layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        columns = 4  # Flow cards into 4 columns
        for idx, item in enumerate(items):
            card = self.create_grid_item_card(item, symbol)
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)

    def create_grid_item_card(self, item: Dict[str, Any], symbol: str) -> QFrame:
        card = QFrame()
        card.setFixedSize(220, 110)
        quality_color = GRADE_COLORS.get(item["grade"], COLOR_BORDER)
        
        # Grid Card with subtle left quality border highlight
        card.setStyleSheet(f"""
            border: 1px solid {COLOR_BORDER};
            border-left: 4px solid {quality_color};
            border-radius: 6px;
            background-color: {COLOR_FRAME};
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Upper row layout: Icon + text details
        row_upper = QHBoxLayout()
        row_upper.setSpacing(8)

        img_lbl = QLabel()
        img_lbl.setPixmap(self.get_item_pixmap(item["item_key"], size=32))
        img_lbl.setFixedSize(32, 32)
        img_lbl.setStyleSheet("border: none; background: transparent;")
        row_upper.addWidget(img_lbl)

        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(1)
        name_lbl = QLabel(item["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #e8e8e8; border: none; background: transparent;")
        name_lbl.setWordWrap(True)
        
        info_lbl = QLabel(f"Lvl {item['level']} | {item['grade'].capitalize()}")
        info_lbl.setStyleSheet(f"color: {quality_color}; font-size: 9px; border: none; background: transparent;")
        
        txt_layout.addWidget(name_lbl)
        txt_layout.addWidget(info_lbl)
        txt_layout.addStretch()
        row_upper.addLayout(txt_layout)
        row_upper.addStretch()

        # Lower row layout: Pricing information and badges
        row_lower = QHBoxLayout()
        qty_badge = QLabel(f"Qty: {item['quantity']}")
        qty_badge.setStyleSheet("color: #b8b8b8; font-size: 10px; border: none; background: transparent;")
        
        price_val = item.get("total_price_val", 0.0)
        price_lbl = QLabel(f"{symbol}{price_val:.2f}")
        price_lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY}; font-size: 12px; border: none; background: transparent;")
        
        row_lower.addWidget(qty_badge)
        row_lower.addStretch()
        row_lower.addWidget(price_lbl)

        layout.addLayout(row_upper)
        layout.addStretch()
        layout.addLayout(row_lower)
        return card
