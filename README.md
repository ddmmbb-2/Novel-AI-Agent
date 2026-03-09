
# Novel-AI-Agent  
### 自動小說創作 AI 系統 / Autonomous AI Novel Writing System

Novel-AI-Agent 是一個結合 **長期記憶機制、AI 自動寫作與章節回溯功能** 的小說創作系統。  
系統透過本地大型語言模型（LLM）與 **Ollama** 進行連接，能夠自動生成章節、追蹤劇情與伏筆，並維持整體故事的一致性。

Novel-AI-Agent is an **AI-powered novel writing system** featuring long-term story memory, automatic chapter generation, and rollback capabilities.  
It connects to **local LLMs via Ollama**, allowing continuous story generation while maintaining narrative consistency.

---

# ✨ Features / 主要功能

### 📖 自動章節生成  
AI 會根據小說設定與前文內容自動創作新的章節。

Automatic chapter generation based on the story setting and previous chapters.

---

### 🧠 長期故事記憶系統  
系統會維護三種核心記憶：

- **設定紀錄 (Setting Record)** – 世界觀、角色狀態、物品、能力  
- **事件紀錄 (Event Record)** – 重要劇情發展  
- **伏筆紀錄 (Foreshadow Record)** – 尚未解開的劇情線索  

The system maintains three memory layers:

- **Setting Memory**
- **Event Timeline**
- **Foreshadow Tracking**

---

### ⏪ 時光倒流 (章節回溯)
可以從任意章節重新開始創作，系統會自動回復當時的故事記憶狀態。

Allows rolling back to any chapter and restoring the story memory snapshot.

---

### 🎭 風格控制
在建立小說時可以選擇作品風格，例如：

- 系統流
- 苟道流
- 輕鬆日常
- 搞笑吐槽
- 凡人流
- 克蘇魯

The system supports style tags such as:

- System progression
- Survival / cautious cultivation
- Comedy
- Slice-of-life
- Dark fantasy

---

### 🖥 GUI 創作介面
提供圖形化介面，可：

- 管理小說
- 查看章節
- 即時查看 AI 工作日誌
- 控制創作流程

A graphical interface for managing novels and monitoring AI generation.

---

# 🧩 System Architecture / 系統架構



Story Setting
↓
Chapter Generation
↓
Chapter Summary
↓
Memory Update

* Setting Record
* Event Record
* Foreshadow Record

↓
Global Story Summary
↓
Next Chapter Generation



The system continuously updates story memory to maintain narrative coherence.

---

# ⚙ Requirements / 需求

Python 3.9+

Required packages:



tkinter
requests
sqlite3



Local LLM via **Ollama**

Example models:



qwen2.5:14b
gemma3:12b
llama3



---

# 🚀 How to Run / 執行方式

1️⃣ 安裝 Ollama 並下載模型



ollama pull qwen2.5:14b



2️⃣ 啟動 Ollama



ollama serve



3️⃣ 執行程式



python novel_agent.py



---

# 📂 Database

系統使用 SQLite 保存：



novel_agent_v5.db



資料包含：

- novels (小說資料)
- chapters (章節與記憶快照)

---

# 🔮 Future Plans / 未來計畫

- 劇情規劃 Agent (Story Planner)
- 角色記憶系統
- 多模型協作生成
- RAG 劇情檢索
- Web UI

---

# 📜 License

MIT License

---

# ❤️ Author

Created as an experiment in **AI autonomous storytelling and long-memory narrative systems**.


