import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import sqlite3
import requests
import json
import threading
import time
import re
import datetime

# --- 配置區 ---
OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
DB_NAME = "novel_agent_v5.db"  # 更新為 v5 以支援時光倒流的快照欄位

class NovelAIAgent:
    def __init__(self, root):
        self.root = root
        self.root.title("龍小貓 AI 爆肝創作系統 (V5 時光倒流與風格守護版)")
        self.root.geometry("1400x850")
        self.is_running = False
        self.current_novel_id = None
        
        # 抓取本地模型
        self.available_models = self.fetch_ollama_models()
        self.current_model = self.available_models[0] if self.available_models else "gemma3:12b"
        
        self.conn = self.init_db()
        self.setup_gui()
        self.load_novels_to_combobox()

    def fetch_ollama_models(self):
        """自動抓取本地 Ollama 安裝的所有模型"""
        try:
            res = requests.get(OLLAMA_TAGS_URL, timeout=3)
            if res.status_code == 200:
                models = [m['name'] for m in res.json().get('models', [])]
                return models if models else ["gemma3:12b"]
        except Exception as e:
            print(f"無法連線至 Ollama: {e}")
            return ["連線失敗, 請確認 Ollama 已啟動"]

    def init_db(self):
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS novels 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      name TEXT, 
                      setting TEXT, 
                      setting_record TEXT, 
                      event_record TEXT, 
                      foreshadow_record TEXT,
                      last_chap_summary TEXT,
                      global_summary TEXT,
                      saved_context TEXT)''')
        # chapters 新增了五個快照欄位
        c.execute('''CREATE TABLE IF NOT EXISTS chapters 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      novel_id INTEGER, 
                      chapter_num INTEGER, 
                      title TEXT, 
                      content TEXT,
                      setting_record TEXT,
                      event_record TEXT,
                      foreshadow_record TEXT,
                      last_chap_summary TEXT,
                      global_summary TEXT)''')
        conn.commit()
        return conn

    def setup_gui(self):
        # 頂部：小說與模型切換區
        top_frame = tk.Frame(self.root, pady=5, padx=10, bg="#ecf0f1")
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="當前小說：", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.novel_combo = ttk.Combobox(top_frame, state="readonly", width=25, font=("Arial", 10))
        self.novel_combo.pack(side=tk.LEFT, padx=5)
        self.novel_combo.bind("<<ComboboxSelected>>", self.on_novel_selected)
        
        tk.Button(top_frame, text="➕ 建立新書", command=self.create_new_novel, bg="#3498db", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

        # 模型選單
        tk.Label(top_frame, text="🧠 AI 模型：", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(20, 0))
        self.model_combo = ttk.Combobox(top_frame, values=self.available_models, state="readonly", width=20, font=("Arial", 10))
        self.model_combo.pack(side=tk.LEFT, padx=5)
        if self.available_models:
            self.model_combo.current(0)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)

        # 主容器：三欄式
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.main_pane.pack(fill=tk.BOTH, expand=1)

        # 1. 左側：AI 工作日誌
        self.work_frame = tk.Frame(self.main_pane)
        tk.Label(self.work_frame, text="🤖 系統狀態與日誌", font=("Arial", 10, "bold")).pack(pady=5)
        self.log_area = scrolledtext.ScrolledText(self.work_frame, wrap=tk.WORD, width=35, bg="#2c3e50", fg="#ecf0f1", font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.work_frame)

        # 2. 中間：章節選單與重寫按鈕
        self.list_frame = tk.Frame(self.main_pane)
        tk.Label(self.list_frame, text="📜 章節清單", font=("Arial", 10, "bold")).pack(pady=5)
        self.chapter_listbox = tk.Listbox(self.list_frame, width=30, font=("Microsoft JhengHei", 10))
        self.chapter_listbox.pack(fill=tk.BOTH, expand=1)
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        self.rewrite_btn = tk.Button(self.list_frame, text="⏪ 從選定章節開始重寫", command=self.rollback_to_chapter, bg="#e67e22", fg="white", font=("Arial", 10, "bold"))
        self.rewrite_btn.pack(fill=tk.X, pady=5)
        self.main_pane.add(self.list_frame)

        # 3. 右側：文章閱讀區
        self.read_frame = tk.Frame(self.main_pane)
        tk.Label(self.read_frame, text="📖 閱讀區 (繁體中文)", font=("Arial", 10, "bold")).pack(pady=5)
        self.read_area = scrolledtext.ScrolledText(self.read_frame, wrap=tk.WORD, width=80, font=("Microsoft JhengHei", 12), spacing3=10)
        self.read_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.read_frame)

        # 底部控制
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ 開始自動創作", command=self.start_thread, bg="#27ae60", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.start_btn.pack(side=tk.LEFT, padx=20)
        
        self.stop_btn = tk.Button(btn_frame, text="⏸ 暫停創作", command=self.stop_ai, bg="#c0392b", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(btn_frame, text="狀態：待命中心", fg="blue", font=("Arial", 11, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=20)

    # --- UI 輔助方法 ---
    def update_status(self, text, color="blue"):
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    def gui_log(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        def append_log():
            self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_area.see(tk.END)
        self.root.after(0, append_log)

    def gui_refresh_combobox(self, novels_list, set_index=0):
        def refresh():
            self.novel_combo['values'] = novels_list
            if novels_list:
                self.novel_combo.current(set_index)
        self.root.after(0, refresh)

    # --- 建立新小說視窗 (含風格標籤) ---
    def create_new_novel(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("📖 建立新小說")
        dialog.geometry("650x550")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="小說書名：", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 11), width=60)
        name_entry.pack(padx=20, fill=tk.X)

        tk.Label(dialog, text="🏷️ 風格標籤 (可複選，提示 AI 創作走向)：", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        tag_frame = tk.Frame(dialog)
        tag_frame.pack(padx=20, fill=tk.X)
        
        AVAILABLE_TAGS = [
            "系統流", "穿越重生", "凡人流", "無敵流", "苟道流", 
            "黑暗文", "搞笑吐槽", "群像劇", "殺伐果斷", "種田發展",
            "智鬥布局", "單女主", "無女主", "克蘇魯", "輕鬆日常"
        ]
        
        tag_vars = {}
        row, col = 0, 0
        for tag in AVAILABLE_TAGS:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(tag_frame, text=tag, variable=var, font=("Arial", 10))
            chk.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            tag_vars[tag] = var
            col += 1
            if col > 4:
                col = 0
                row += 1

        tk.Label(dialog, text="初始設定 (背景、主角性格、金手指機制等)：", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        setting_text = scrolledtext.ScrolledText(dialog, font=("Microsoft JhengHei", 11), height=10, wrap=tk.WORD)
        setting_text.pack(padx=20, fill=tk.BOTH, expand=True)

        def on_confirm():
            name = name_entry.get().strip()
            raw_setting = setting_text.get("1.0", tk.END).strip()
            
            if not name or not raw_setting:
                messagebox.showwarning("警告", "書名與設定皆不可為空！", parent=dialog)
                return
            
            selected_tags = [tag for tag, var in tag_vars.items() if var.get()]
            tags_str = "、".join(selected_tags) if selected_tags else "一般網文"
            final_setting = f"【作品風格走向】：{tags_str}\n\n【詳細世界觀與設定】：\n{raw_setting}"
            
            c = self.conn.cursor()
            c.execute("""INSERT INTO novels 
                         (name, setting, setting_record, event_record, foreshadow_record, last_chap_summary, global_summary, saved_context) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                      (name, final_setting, "暫無設定紀錄", "暫無事件紀錄", "暫無伏筆紀錄", "暫無上一章摘要", "暫無全局彙整", ""))
            self.conn.commit()
            
            self.gui_log(f"🎉 成功建立新書：《{name}》(標籤：{tags_str})")
            self.load_novels_to_combobox()
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="✔ 確定建立", command=on_confirm, bg="#27ae60", fg="white", font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy, bg="#7f8c8d", fg="white", font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=10)

    # --- 小說與模型管理邏輯 ---
    def load_novels_to_combobox(self):
        c = self.conn.cursor()
        c.execute("SELECT id, name FROM novels ORDER BY id DESC")
        novels = c.fetchall()
        val_list = [f"{n[0]} - {n[1]}" for n in novels]
        self.gui_refresh_combobox(val_list)
        if val_list:
            self.root.after(100, lambda: self.on_novel_selected(None))

    def on_novel_selected(self, event):
        selection = self.novel_combo.get()
        if not selection: return
        self.current_novel_id = int(selection.split(" - ")[0])
        self.gui_log(f"📂 切換至小說：{selection.split(' - ')[1]}")
        self.refresh_chapter_list()

    def on_model_selected(self, event):
        self.current_model = self.model_combo.get()
        self.gui_log(f"🧠 已切換 AI 模型為：{self.current_model}")

    def refresh_chapter_list(self):
        self.chapter_listbox.delete(0, tk.END)
        if not self.current_novel_id: return
        c = self.conn.cursor()
        c.execute("SELECT chapter_num, title FROM chapters WHERE novel_id = ? ORDER BY chapter_num ASC", (self.current_novel_id,))
        for row in c.fetchall():
            self.chapter_listbox.insert(tk.END, f"第 {row[0]} 章：{row[1]}")
        self.chapter_listbox.yview(tk.END)

    def on_chapter_select(self, event):
        selection = self.chapter_listbox.curselection()
        if not selection: return
        index = selection[0]
        chapter_text = self.chapter_listbox.get(index)
        chapter_num = re.search(r'第 (\d+) 章', chapter_text).group(1)
        
        c = self.conn.cursor()
        c.execute("SELECT title, content FROM chapters WHERE novel_id = ? AND chapter_num = ?", (self.current_novel_id, chapter_num))
        row = c.fetchone()
        if row:
            self.read_area.delete(1.0, tk.END)
            self.read_area.insert(tk.END, f"【{row[0]}】\n\n{row[1]}")

    # --- 時光倒流 (重寫) 邏輯 ---
    def rollback_to_chapter(self):
        if self.is_running:
            messagebox.showwarning("警告", "請先暫停 AI 創作，再進行重寫操作！")
            return

        selection = self.chapter_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "請在左側清單點選你要從哪一章開始重寫！")
            return

        index = selection[0]
        chapter_text = self.chapter_listbox.get(index)
        target_chap = int(re.search(r'第 (\d+) 章', chapter_text).group(1))

        if not messagebox.askyesno("嚴重警告", f"確定要從 第 {target_chap} 章 開始重寫嗎？\n這將會【永久刪除】第 {target_chap} 章(含)之後的所有章節與記憶快照！"):
            return

        c = self.conn.cursor()

        # 1. 恢復全局記憶狀態
        if target_chap == 1:
            c.execute("""UPDATE novels SET 
                         setting_record='暫無設定紀錄', event_record='暫無事件紀錄', 
                         foreshadow_record='暫無伏筆紀錄', last_chap_summary='暫無上一章摘要', 
                         global_summary='暫無全局彙整' WHERE id=?""", (self.current_novel_id,))
        else:
            # 讀取目標章節的「上一章」記憶快照
            c.execute("""SELECT setting_record, event_record, foreshadow_record, last_chap_summary, global_summary 
                         FROM chapters WHERE novel_id=? AND chapter_num=?""", (self.current_novel_id, target_chap - 1))
            row = c.fetchone()
            if row:
                c.execute("""UPDATE novels SET 
                             setting_record=?, event_record=?, foreshadow_record=?, 
                             last_chap_summary=?, global_summary=? WHERE id=?""", 
                          (*row, self.current_novel_id))

        # 2. 刪除該章及後續所有章節
        c.execute("DELETE FROM chapters WHERE novel_id=? AND chapter_num>=?", (self.current_novel_id, target_chap))
        self.conn.commit()

        self.gui_log(f"⏪ 時光倒流成功！已刪除第 {target_chap} 章之後的內容，記憶已回溯，準備從頭覆寫。")
        self.refresh_chapter_list()
        self.read_area.delete(1.0, tk.END)

    # --- AI 溝通模組 ---
    def call_ai_with_retry(self, stage, system_p, user_p, retries=3, use_json=False):
        full_system_p = system_p + "\n【重要指令】：請務必使用繁體中文 (Traditional Chinese) 回覆，嚴禁簡體字。"
        payload = {
            "model": self.current_model, # 使用使用者選定的模型
            "messages": [{"role": "system", "content": full_system_p}, {"role": "user", "content": user_p}],
            "temperature": 0.7
        }
        if use_json: payload["response_format"] = {"type": "json_object"}

        for attempt in range(retries):
            if not self.is_running: return ""
            self.gui_log(f"🧠 {stage} (模型:{self.current_model} | 嘗試 {attempt+1}/{retries})...")
            try:
                res = requests.post(OLLAMA_URL, json=payload, timeout=600).json()
                return res['choices'][0]['message']['content'].strip()
            except Exception as e:
                self.gui_log(f"❌ {stage} 超時或失敗: {e}")
                if attempt < retries - 1:
                    self.gui_log("⏳ 等待 5 秒後重試...")
                    time.sleep(5)
        return ""

    def extract_json(self, text):
        try:
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            return json.loads(match.group(1)) if match else None
        except: return None

    # --- 執行緒控制與核心工作迴圈 ---
    def start_thread(self):
        if not self.current_novel_id:
            messagebox.showwarning("警告", "請先選擇或建立一本小說！")
            return
        if self.is_running: return
        self.is_running = True
        self.novel_combo.config(state="disabled") 
        self.update_status("狀態：爆肝創作中...", "red")
        threading.Thread(target=self.work_loop, daemon=True).start()

    def stop_ai(self):
        self.is_running = False
        self.update_status("狀態：已發送停止指令 (待本回合結束)", "orange")
        self.root.after(0, lambda: self.novel_combo.config(state="readonly"))

    def work_loop(self):
        c = self.conn.cursor()
        novel_id = self.current_novel_id

        while self.is_running:
            # --- 準備階段：讀取資料庫狀態 ---
            c.execute("""SELECT setting, setting_record, event_record, foreshadow_record, 
                                last_chap_summary, global_summary, saved_context 
                         FROM novels WHERE id=?""", (novel_id,))
            setting, setting_record, event_record, foreshadow_record, last_chap_summary, global_summary, saved_context = c.fetchone()
            
            c.execute("SELECT MAX(chapter_num) FROM chapters WHERE novel_id=?", (novel_id,))
            max_chap = c.fetchone()[0]
            next_chap = (max_chap or 0) + 1

            self.gui_log(f"\n=======================")
            self.gui_log(f"📝 開始執行循環：準備創作第 {next_chap} 章")
            
            # 動態提取風格標籤
            style_match = re.search(r'【作品風格走向】：(.*?)\n', setting)
            current_style = style_match.group(1) if style_match else "一般網文"

            # ==========================================
            # 循環過程 1. 初始資料 + 三維資訊 + 上一章摘要 -> 寫下一章
            # ==========================================
            if next_chap == 1:
                self.gui_log("🌟 檢測為第一章，使用初始資料進行開局創作...")
                context = f"【初始設定】：\n{setting}\n\n請根據以上設定，撰寫第一章正文。"
            else:
                self.gui_log("📖 結合前一章三維資訊與摘要，進行延續創作...")
                context = (
                    f"【初始設定】：\n{setting}\n\n"
                    f"【目前世界觀與全局狀態 (三維資訊)】：\n{global_summary}\n\n"
                    f"【上一章詳細摘要】：\n{last_chap_summary}\n\n"
                    f"請緊密銜接上一章的劇情，撰寫第 {next_chap} 章正文。"
                )
            
            # 儲存 Context 供除錯用
            c.execute("UPDATE novels SET saved_context = ? WHERE id = ?", (context, novel_id))
            self.conn.commit()

            writer_sys_prompt = (
                f"你是一位頂級的網路小說家。\n"
                f"【最高指令】：本作品的核心風格為『{current_style}』！\n"
                f"你的遣詞造句、情境描寫與劇情節奏，都必須死死咬住這個風格，絕對不能寫成平庸無聊的流水帳。"
            )
            content = self.call_ai_with_retry(f"第{next_chap}章正文", writer_sys_prompt, context)
            if not content:
                self.gui_log("⚠️ 寫作多次失敗，為保護進度，自動暫停運行。")
                self.stop_ai()
                break

            # --- 附加步驟：給 AI 命名標題 (防呆純文字版) ---
            title_sys = "你是一個小說編輯。請根據內文為這章下一個吸引人的標題。請只輸出標題文字，不要加書名號、不要加上'第X章'、不要任何其他廢話。"
            title_res = self.call_ai_with_retry("標題命名", title_sys, f"內文：{content[:1500]}")
            clean_title = title_res.strip() if title_res else "無題"
            full_title = f"第{next_chap}章 {clean_title}"

            # --- 初步存檔 (標題與內文) ---
            c.execute("INSERT INTO chapters (novel_id, chapter_num, title, content) VALUES (?, ?, ?, ?)", 
                      (novel_id, next_chap, full_title, content))
            self.conn.commit()
            self.root.after(0, self.refresh_chapter_list) 
            self.gui_log(f"📦 正文存檔成功：《{full_title}》")

            # ==========================================
            # 循環過程 2. 剛剛寫的章節 -> 給 AI 彙整成三維資訊
            # ==========================================
            self.gui_log("🌍 讀取最新章節，提煉並更新三維資訊...")
            
            combo_sys = (
                f"你是一位專業的劇情統籌編輯。這部小說的核心風格是：【{current_style}】。\n"
                "請根據【舊有三維資訊】與【剛寫好的最新章節】，更新並彙整出最新的三維資訊。\n"
                "【第一次更新說明】：如果是第一章，舊有資訊會是空的，請直接根據正文建立起初始的三維狀態。\n"
                "【最高指令】：請你嚴格按照以下四個標題依序輸出，保留體現風格的關鍵細節，不要有任何多餘的廢話：\n"
                "### 【設定更新】\n"
                "(寫入角色狀態、修為、裝備、世界觀等)\n"
                "### 【事件更新】\n"
                "(寫入重大事件推進與戰鬥結果)\n"
                "### 【伏筆更新】\n"
                "(保留未解伏筆，刪除已解開的)\n"
                "### 【全局彙整】\n"
                "(將上述三點融合成一段通順的全局劇情總覽，這將作為下一章的核心引導)"
            )
            
            combo_user = (
                f"【舊有設定】：\n{setting_record}\n\n"
                f"【舊有事件】：\n{event_record}\n\n"
                f"【舊有伏筆】：\n{foreshadow_record}\n\n"
                f"【剛寫好的最新章節正文】：\n{content}\n\n"
                "請開始更新三維資訊："
            )

            memory_res = self.call_ai_with_retry("更新三維資訊", combo_sys, combo_user)
            
            new_setting, new_event, new_foreshadow, new_global_summary = setting_record, event_record, foreshadow_record, global_summary
            update_success = False

            if memory_res:
                try:
                    part1 = memory_res.split("### 【事件更新】")
                    new_setting = part1[0].replace("### 【設定更新】", "").strip()
                    part2 = part1[1].split("### 【伏筆更新】")
                    new_event = part2[0].strip()
                    part3 = part2[1].split("### 【全局彙整】")
                    new_foreshadow = part3[0].strip()
                    new_global_summary = part3[1].strip()
                    update_success = True
                    self.gui_log("✅ 三維資訊更新成功！")
                except Exception as e:
                    self.gui_log(f"⚠️ 三維資訊格式解析失敗，將保留舊有資訊。")

            # ==========================================
            # 循環過程 3. 剛剛寫的章節 -> AI 彙整成單章詳細摘要
            # ==========================================
            self.gui_log("🧠 讀取最新章節，生成單章詳細摘要...")
            single_sum_sys = (
                f"你是一位極其細心的紀錄員。這部小說的風格是【{current_style}】。\n"
                "請將這章內容濃縮為『單章詳細摘要』。除了記錄發生的事件外，"
                "請務必保留『人物的決策、情緒反應與伏筆細節』，這將直接提供給下一章的作者作為上下文銜接。"
            )
            new_last_chap_summary = self.call_ai_with_retry("單章摘要生成", single_sum_sys, f"剛寫好的章節內容：\n{content}")

            # --- 存檔三維資訊與摘要 (同步存入快照) ---
            if new_last_chap_summary and update_success:
                c.execute("""UPDATE novels SET 
                             last_chap_summary = ?, setting_record = ?, event_record = ?, 
                             foreshadow_record = ?, global_summary = ?
                             WHERE id = ?""", 
                          (new_last_chap_summary, new_setting, new_event, new_foreshadow, new_global_summary, novel_id))
                
                c.execute("""UPDATE chapters SET 
                             setting_record = ?, event_record = ?, foreshadow_record = ?, 
                             last_chap_summary = ?, global_summary = ?
                             WHERE novel_id = ? AND chapter_num = ?""", 
                          (new_setting, new_event, new_foreshadow, new_last_chap_summary, new_global_summary, novel_id, next_chap))
                self.conn.commit()
                self.gui_log("✅ 記憶快照建立完成。")

            # ==========================================
            # 循環過程 4. 休息 10 秒
            # ==========================================
            self.gui_log("⏳ 單章循環結束，準備進入下一個循環。")
            if not self.is_running:
                break
                
            for i in range(10, 0, -1):
                if not self.is_running: 
                    break 
                self.update_status(f"狀態：機器散熱休息中... 剩餘 {i} 秒", "green")
                time.sleep(1)
            
            # ==========================================
            # 循環過程 5. 回到循環過程(1.) (While 迴圈自動處理)
            # ==========================================
            if self.is_running:
                self.update_status("狀態：爆肝創作中...", "red")

        self.gui_log("🛑 系統已安全暫停。")
        self.update_status("狀態：待命中心", "blue")
        self.root.after(0, lambda: self.novel_combo.config(state="readonly"))

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelAIAgent(root)
    root.mainloop()
