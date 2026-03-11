# Novel-AI-Agent (V5 雲端同步旗艦版)

### 自動小說創作與雲端發佈系統 / Autonomous AI Novel Writing & Cloud Sync System

Novel-AI-Agent 是一個結合 **長期記憶機制、AI 自動寫作、章節回溯**，以及 **自動化網頁同步** 的全方位小說創作生態系統。

本系統不僅能透過本地大型語言模型（LLM）與 **Ollama** 連接進行自動創作，更整合了 PHP/MySQL 雲端發佈機制，讓 AI 生成的內容能即時同步至讀者前端網頁。

Novel-AI-Agent is a comprehensive **AI storytelling ecosystem** featuring long-term memory, automatic generation, and **instant cloud synchronization** to a web-based reader.

---

# 🌐 Online Showcase / 成果展示

**立即體驗 AI 創作與 Web 閱讀效果：** 👉 **[https://novel.ddmmbb.org/](https://novel.ddmmbb.org/)**

*(此網頁為本系統之配套前端，展示 AI 如何在長期記憶輔助下，維持劇情連貫性並即時同步至雲端供讀者閱讀。)*

---

# ✨ V5 新增功能 / New Features

### ☁️ 雲端自動化同步 (Cloud Sync)

* **即時發佈**：AI 每完成一章的潤飾與摘要，便會自動透過 API 將內容推送到網站伺服器。
* **舊書打包**：支援一鍵將本地資料庫的舊章節「批次同步」至雲端，輕鬆遷移創作進度。
* **雲端時光倒流**：當本地執行章節回溯（Rollback）時，雲端亦會同步清理「舊未來」章節，確保讀者進度與創作進度一致。

### 📖 專業 Web 閱讀器 (Advanced Web Reader)

* **極致閱讀體驗**：內建護眼模式（日/夜切換）、可調字體大小與響應式設計（手機平板完美適配）。
* **即時繁簡轉換**：整合 **OpenCC** 技術，讀者可一鍵切換繁體或簡體中文，且不破壞 HTML 結構。
* **高效能架構**：採用 SQLite **WAL (Write-Ahead Logging)** 模式，確保 Python 寫入與讀者讀取不互鎖。

---

# 🧠 核心技術 / Core Mechanics

### 🧬 三維長期記憶系統

* **設定紀錄 (Setting Record)** – 追蹤角色修為、裝備、地圖變動。
* **事件紀錄 (Event Record)** – 紀錄重大戰役、任務目標與困境。
* **伏筆紀錄 (Foreshadow Record)** – 管理尚未解開的謎團與未來衝突點。

### ✍️ 三階寫作工作流

1. **劇情綱要生成**：根據風格標籤與上下文，由 AI 企劃規劃本章起承轉合。
2. **正文初稿撰寫**：AI 作家依據綱要進行萬字級演繹，死守作品風格。
3. **編輯深度潤飾**：由編輯 Agent 進行文筆優化、環境渲染，提升閱讀質感。

---

# ⚙ Requirements / 需求

### 🖥 創作端 (Local)

* **Python 3.9+**
* **Ollama** (建議模型：`gemma3:12b`, `qwen2.5:14b`)
* **必備套件**：`tkinter`, `requests`, `sqlite3`

### 🌐 伺服器端 (Cloud)

* **PHP 7.4+**
* **SQLite 支援** (用於雲端快取與發佈)
* **OpenCC-JS** (已整合至前端)

---

# 🚀 快速上手 / Quick Start

1️⃣ **部署雲端 API**

* 將 `api.php`, `config.php`, `index.php` 上傳至您的伺服器。
* 在 `config.php` 與 `api.php` 中設定您的 `WEB_API_KEY`。

2️⃣ **設定本地創作程式**

* 修改 `app.py` 中的 `WEB_API_URL` 與 `WEB_API_KEY`，使其與雲端一致。

3️⃣ **開始創作**

```bash
python app.py

```

* 建立新書 ➔ 選擇模型 ➔ 點擊 **"▶ 開始自動創作"**，您的作品將會即時出現在網頁上！

---

# 🔮 未來計畫 / Future Plans

* [x] **全功能 Web UI**：已實現 (V5 旗艦版整合)。
* [ ] **多 Agent 協作模式**：引入專門的「邏輯稽查 Agent」負責抓漏。
* [ ] **圖片生成整合**：自動為每一章生成對應的插畫並同步至網站。
* [ ] **讀者互動系統**：讓讀者的留言能影響下一個循環的 AI 創作走向。

---

# ❤️ Author & License

Created as an experiment in **AI autonomous storytelling and cloud-native publishing**.
Distributed under the **MIT License**.

---

