# Task Bar Hero - Inventory Value

A sleek, premium PyQt6 desktop companion application for the game **Task Bar Hero**. This application decrypts your game save file in real-time, fetches item prices from the Steam Community Market, and tracks/charts your overall inventory net worth progression over time.


---

## 🚀 How to Use

You can run the application in two ways:

### Option A: Standalone Executable ([TaskBarHero-InventoryValue.exe](dist/TaskBarHero-InventoryValue.exe))
No Python installation is required for this option.
1. Navigate to the [dist/](dist) directory inside this repository.
2. Run [TaskBarHero-InventoryValue.exe](dist/TaskBarHero-InventoryValue.exe).
   - *Note: Ensure the executable remains in the project directory (or that `items.json`, `id_to_sprite.json`, and the `cache_sprites/` folder are located in the same directory as the executable so it can load item databases and sprites).*

### Option B: Run from Source via Batch Script (`start.bat`)
Requires Python to be installed on your machine.
1. Clone the repository and navigate into the folder:
   ```bash
   git clone https://github.com/MathAmorim/TBH-InventoryValue.git
   cd TBH-InventoryValue
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the application by double-clicking **`start.bat`** (or run `python main.py` in your terminal).

---

## 📂 Configuration

Once the app is open:
1. Click the **Browse** button in the header and select your game's active save file: `SaveFile_Live.es3`.
   - **Typical Windows Path**: `C:\Users\<username>\AppData\LocalLow\TesseractStudio\TaskbarHero\SaveFile_Live.es3`
2. Select your preferred currency (USD, BRL, EUR, etc.) from the dropdown.

---

## 📂 File Architecture

- `main.py`: Application entry point setting up palettes and dark themes.
- `main_window.py`: Core GUI layout containing tabs, headers, currency selectors, list/grid rendering, and sorting logic.
- `custom_chart.py`: A custom `QPainter`-drawn interactive history chart.
- `save_parser.py`: Decrypts and parses the `.es3` encrypted save format.
- `steam_market.py`: Safe, rate-limiting-aware sequential market price aggregator with currency conversion.
- `history_manager.py`: Manages persistent valuation historical logs in `history.json`.
- `requirements.txt`: Python package dependencies.
- `start.bat`: Windows batch file to quickly run the python source code.

---

## ⚖️ License

This project is open-source and available under the MIT License.