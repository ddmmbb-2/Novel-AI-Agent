# Novel-AI-Agent

### 自動小說創作 AI 系統 / Autonomous AI Novel Writing System

Novel-AI-Agent 是一個結合 **長期記憶機制、AI 自動寫作與章節回溯功能** 的小說創作系統。

系統透過本地大型語言模型（LLM）與 **Ollama** 進行連接，能夠自動生成章節、追蹤劇情與伏筆，並維持整體故事的一致性。

Novel-AI-Agent is an **AI-powered novel writing system** featuring long-term story memory, automatic chapter generation, and rollback capabilities.

---

# 🌐 Online Showcase / 成果展示

**現在就查看 AI 創作的實際成果：** 👉 **[https://novel.ddmmbb.org/](https://novel.ddmmbb.org/)**

*(此網頁展示由本系統自動生成的完整小說作品，您可以從中觀察 AI 如何在長期記憶機制的輔助下，維持劇情連貫性與角色設定。)*

---

# ✨ Features / 主要功能

### 📖 自動章節生成

AI 會根據小說設定與前文內容自動創作新的章節。
Automatic chapter generation based on the story setting and previous chapters.

---

### 🧠 長期故事記憶系統

系統會維護三種核心記憶，確保長篇創作不跑題、不吃書：

* **設定紀錄 (Setting Record)** – 世界觀、角色狀態、物品、能力
* **事件紀錄 (Event Record)** – 重要劇情發展
* **伏筆紀錄 (Foreshadow Record)** – 尚未解開的劇情線索

The system maintains three memory layers: **Setting**, **Event**, and **Foreshadowing**.

---

### ⏪ 時光倒流 (章節回溯)

可以從任意章節重新開始創作，系統會自動回復當時的故事記憶狀態，方便進行劇情分歧測試。
Allows rolling back to any chapter and restoring the story memory snapshot.

---

### 🎭 風格控制

在建立小說時可以選擇多種作品風格，例如：

* **系統流、苟道流、凡人流**
* **輕鬆日常、搞笑吐槽**
* **克蘇魯、玄幻冒險**

---

### 🖥 GUI 創作介面

提供圖形化介面，讓您可以：

* 管理多部小說作品
* 即時查看 AI 生成日誌
* 調整劇情走向與記憶快照

---

# 🧩 System Architecture / 系統架構

```text
Story Setting ➔ Chapter Generation ➔ Chapter Summary ➔ Memory Update
                                                            │
    ┌───────────────────────────────────────────────────────┘
    ▼
Global Story Summary (Setting / Event / Foreshadow) ➔ Next Chapter...

```

---

# ⚙ Requirements / 需求

* **Python 3.9+**
* **Required Packages:** `tkinter`, `requests`, `sqlite3`
* **Backend:** Local LLM via **Ollama**
* **Recommended Models:** `qwen2.5:14b`, `gemma3:12b`, `llama3`

---

# 🚀 How to Run / 執行方式

1️⃣ **安裝 Ollama 並下載模型**

```bash
ollama pull qwen2.5:14b

```

2️⃣ **啟動 Ollama**

```bash
ollama serve

```

3️⃣ **執行程式**

```bash
python novel_agent.py

```

---

# 📂 Database / 資料庫儲存

系統使用 SQLite (`novel_agent_v5.db`) 保存所有創作歷程：

* **novels**: 小說基礎資訊與設定。
* **chapters**: 章節內容與對應的記憶快照（Snapshot）。

---

# 🔮 Future Plans / 未來計畫

* [ ] **劇情規劃 Agent (Story Planner)**：自動產出大綱與細綱。
* [ ] **角色記憶系統強化**：更深層的角色性格演繹。
* [ ] **多模型協作**：不同模型負責創作與審稿。
* [ ] **全功能 Web UI**：將目前的成果展示網頁進化為完整的線上創作平台。

---

# 📜 License

MIT License

---

# ❤️ Author

Created as an experiment in **AI autonomous storytelling and long-memory narrative systems**.

