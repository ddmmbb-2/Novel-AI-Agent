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
DB_NAME = "novel_agent_v5.db"  

# 🌐 網站同步設定 🌐
# 替換成你網站實際的 api.php 網址
WEB_API_URL = " 替換成你網站實際的 api.php 網址" 
WEB_API_KEY = "dragoncat_super_secret_key_2024"

class NovelAIAgent:
    def __init__(self, root):
        self.root = root
        self.root.title("龍小貓 AI 半自動創作系統 (使用者指定劇本版)")
        self.root.geometry("1400x850")
        self.is_running = False
        self.current_novel_id = None
        self.current_reading_chapter_num = None
        
        self.available_models = self.fetch_ollama_models()
        self.current_model = self.available_models[0] if self.available_models else "gemma3:12b"
        
        self.conn = self.init_db()
        self.setup_gui()
        self.load_novels_to_combobox()

    def fetch_ollama_models(self):
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
                      name TEXT, setting TEXT, setting_record TEXT, event_record TEXT, 
                      foreshadow_record TEXT, last_chap_summary TEXT, global_summary TEXT, saved_context TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS chapters 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, novel_id INTEGER, chapter_num INTEGER, 
                      title TEXT, content TEXT, setting_record TEXT, event_record TEXT, 
                      foreshadow_record TEXT, last_chap_summary TEXT, global_summary TEXT)''')
        conn.commit()
        return conn

    def setup_gui(self):
        top_frame = tk.Frame(self.root, pady=5, padx=10, bg="#ecf0f1")
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="當前小說：", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.novel_combo = ttk.Combobox(top_frame, state="readonly", width=25, font=("Arial", 10))
        self.novel_combo.pack(side=tk.LEFT, padx=5)
        self.novel_combo.bind("<<ComboboxSelected>>", self.on_novel_selected)
        
        tk.Button(top_frame, text="➕ 建立新書", command=self.create_new_novel, bg="#3498db", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

        tk.Label(top_frame, text="🧠 AI 模型：", bg="#ecf0f1", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(20, 0))
        self.model_combo = ttk.Combobox(top_frame, values=self.available_models, state="readonly", width=20, font=("Arial", 10))
        self.model_combo.pack(side=tk.LEFT, padx=5)
        if self.available_models:
            self.model_combo.current(0)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)

        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.main_pane.pack(fill=tk.BOTH, expand=1)

        # 1. 系統狀態與日誌
        self.work_frame = tk.Frame(self.main_pane)
        tk.Label(self.work_frame, text="🤖 系統狀態與日誌", font=("Arial", 10, "bold")).pack(pady=5)
        self.log_area = scrolledtext.ScrolledText(self.work_frame, wrap=tk.WORD, width=25, bg="#2c3e50", fg="#ecf0f1", font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.work_frame)

        # 2. 章節清單
        self.list_frame = tk.Frame(self.main_pane)
        tk.Label(self.list_frame, text="📜 章節清單", font=("Arial", 10, "bold")).pack(pady=5)
        self.chapter_listbox = tk.Listbox(self.list_frame, width=20, font=("Microsoft JhengHei", 10))
        self.chapter_listbox.pack(fill=tk.BOTH, expand=1)
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        self.rewrite_btn = tk.Button(self.list_frame, text="⏪ 從選定章節開始重寫", command=self.rollback_to_chapter, bg="#e67e22", fg="white", font=("Arial", 10, "bold"))
        self.rewrite_btn.pack(fill=tk.X, pady=5)
        self.main_pane.add(self.list_frame)

        # 3. 新增：劇本(綱要)輸入區
        self.outline_frame = tk.Frame(self.main_pane)
        tk.Label(self.outline_frame, text="✍️ 本章劇情綱要 (請在此輸入)", font=("Arial", 10, "bold"), fg="#d35400").pack(pady=5)
        self.outline_area = scrolledtext.ScrolledText(self.outline_frame, wrap=tk.WORD, width=35, font=("Microsoft JhengHei", 12), bg="#fdf5e6")
        self.outline_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.outline_frame)

        # 4. 閱讀區
        self.read_frame = tk.Frame(self.main_pane)
        tk.Label(self.read_frame, text="📖 閱讀區 (繁體中文)", font=("Arial", 10, "bold")).pack(pady=5)
        self.read_area = scrolledtext.ScrolledText(self.read_frame, wrap=tk.WORD, width=40, font=("Microsoft JhengHei", 12), spacing3=10)
        self.read_area.pack(fill=tk.BOTH, expand=1)
        
        # 💡 新增：儲存並同步按鈕
        self.save_edit_btn = tk.Button(self.read_frame, text="💾 儲存修改並重新同步至網站", command=self.save_and_sync_edit, bg="#f39c12", fg="white", font=("Arial", 10, "bold"))
        self.save_edit_btn.pack(fill=tk.X, pady=5)

        self.main_pane.add(self.read_frame)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ 根據綱要撰寫本章", command=self.start_generate_chapter, bg="#27ae60", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.start_btn.pack(side=tk.LEFT, padx=20)
        
        self.stop_btn = tk.Button(btn_frame, text="🛑 中斷當前創作", command=self.stop_ai, bg="#c0392b", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.sync_btn = tk.Button(btn_frame, text="☁️ 同步舊書到網站", command=self.sync_all_old_chapters, bg="#8e44ad", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.sync_btn.pack(side=tk.LEFT, padx=20)

        self.status_label = tk.Label(btn_frame, text="狀態：待命中心", fg="blue", font=("Arial", 11, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=20)

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
        chapter_num = int(re.search(r'第 (\d+) 章', chapter_text).group(1)) # 轉成整數
        
        self.current_reading_chapter_num = chapter_num # 💡 新增：記錄下來給儲存按鈕用
        
        c = self.conn.cursor()
        c.execute("SELECT title, content FROM chapters WHERE novel_id = ? AND chapter_num = ?", (self.current_novel_id, chapter_num))
        row = c.fetchone()
        if row:
            self.read_area.delete(1.0, tk.END)
            self.read_area.insert(tk.END, f"【{row[0]}】\n\n{row[1]}")

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
        if target_chap == 1:
            c.execute("""UPDATE novels SET 
                         setting_record='暫無設定紀錄', event_record='暫無事件紀錄', 
                         foreshadow_record='暫無伏筆紀錄', last_chap_summary='暫無上一章摘要', 
                         global_summary='暫無全局彙整' WHERE id=?""", (self.current_novel_id,))
        else:
            c.execute("""SELECT setting_record, event_record, foreshadow_record, last_chap_summary, global_summary 
                         FROM chapters WHERE novel_id=? AND chapter_num=?""", (self.current_novel_id, target_chap - 1))
            row = c.fetchone()
            if row:
                c.execute("""UPDATE novels SET 
                             setting_record=?, event_record=?, foreshadow_record=?, 
                             last_chap_summary=?, global_summary=? WHERE id=?""", 
                          (*row, self.current_novel_id))

        c.execute("DELETE FROM chapters WHERE novel_id=? AND chapter_num>=?", (self.current_novel_id, target_chap))
        self.conn.commit()

        self.gui_log(f"⏪ 時光倒流成功！準備從頭覆寫。 (注意：網站端的舊章節需手動清理)")
        self.refresh_chapter_list()
        self.read_area.delete(1.0, tk.END)

    def save_and_sync_edit(self):
        # 防呆檢查
        if not self.current_novel_id or not self.current_reading_chapter_num:
            messagebox.showwarning("警告", "請先在左側選擇一個章節進行閱讀與修改！")
            return

        if self.is_running:
            messagebox.showwarning("警告", "AI 正在創作中，請暫停後再執行此操作！")
            return

        # 取得文字框內的全部內容
        raw_text = self.read_area.get("1.0", tk.END).strip()
        if not raw_text:
            return

        # 解析標題與內文 (因為我們顯示時有加上【標題】)
        match = re.match(r'【(.*?)】\n+(.*)', raw_text, re.DOTALL)
        if match:
            title = match.group(1).strip()
            content = match.group(2).strip()
        else:
            # 如果使用者不小心把【】刪掉了，就給個保底標題
            title = f"第{self.current_reading_chapter_num}章"
            content = raw_text

        if not messagebox.askyesno("確認儲存", f"確定要儲存【第 {self.current_reading_chapter_num} 章】的修改，並重新同步到網站嗎？"):
            return

        # 1. 更新本地資料庫
        c = self.conn.cursor()
        c.execute("UPDATE chapters SET title=?, content=? WHERE novel_id=? AND chapter_num=?",
                  (title, content, self.current_novel_id, self.current_reading_chapter_num))
        self.conn.commit()

        # 2. 獲取網站同步所需的資訊
        c.execute("SELECT name, setting, global_summary FROM novels WHERE id=?", (self.current_novel_id,))
        novel = c.fetchone()
        if novel:
            novel_name, setting, global_summary = novel
            self.gui_log(f"📝 已儲存【第 {self.current_reading_chapter_num} 章】的本地修改，準備上傳...")
            
            # 3. 開啟執行緒呼叫同步函數 (避免畫面卡住)
            threading.Thread(target=self.sync_to_website, args=(novel_name, setting, self.current_reading_chapter_num, title, content, global_summary), daemon=True).start()
            
            self.refresh_chapter_list() # 更新左側清單 (以防使用者改了標題)
            messagebox.showinfo("成功", "本地修改已儲存，並開始同步至網站！")







    def call_ai_with_retry(self, stage, system_p, user_p, retries=3):
        full_system_p = system_p + "\n【重要指令】：請務必使用繁體中文 (Traditional Chinese) 回覆，嚴禁簡體字。"
        payload = {
            "model": self.current_model,
            "messages": [{"role": "system", "content": full_system_p}, {"role": "user", "content": user_p}],
            "temperature": 0.7
        }

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

    # 🌐 網站同步模組 (單章) 🌐
    def sync_to_website(self, novel_name, setting, chapter_num, title, content, global_summary):
        payload = {
            "api_key": WEB_API_KEY,
            "action": "sync_chapter",
            "novel_name": novel_name,
            "setting": setting,
            "chapter_num": chapter_num,
            "title": title,
            "content": content,
            "global_summary": global_summary
        }
        try:
            res = requests.post(WEB_API_URL, json=payload, timeout=15)
            if res.status_code == 200 and res.json().get("success"):
                self.gui_log("🚀 同步上傳成功！讀者已經可以在網站上看到最新章節。")
            else:
                self.gui_log(f"⚠️ 同步失敗，伺服器回應: {res.text}")
        except Exception as e:
            self.gui_log(f"⚠️ 無法連線至網站 API: {e} (但本地已安全存檔)")

    # 🌟 手動打包同步所有舊章節 🌟
    def sync_all_old_chapters(self):
        if not self.current_novel_id:
            messagebox.showwarning("警告", "請先在上方選擇一本你要同步的小說！")
            return
        if self.is_running:
            messagebox.showwarning("警告", "請先暫停 AI 創作，再進行手動同步操作！")
            return

        if not messagebox.askyesno("同步確認", "確定要將這本小說的【所有舊章節】重新上傳到網站嗎？\n(已存在的章節網站會自動略過)"):
            return

        threading.Thread(target=self._run_sync_all, daemon=True).start()

    def _run_sync_all(self):
        self.update_status("狀態：正在上傳舊書至網站...", "purple")
        self.gui_log("☁️ 開始打包舊章節，準備批次上傳...")
        
        c = self.conn.cursor()
        c.execute("SELECT name, setting, global_summary FROM novels WHERE id=?", (self.current_novel_id,))
        novel = c.fetchone()
        if not novel: return
        novel_name, setting, global_summary = novel

        c.execute("SELECT chapter_num, title, content FROM chapters WHERE novel_id=? ORDER BY chapter_num ASC", (self.current_novel_id,))
        chapters = c.fetchall()

        if not chapters:
            self.gui_log("⚠️ 這本書目前還沒有任何章節可以上傳。")
            self.update_status("狀態：待命中心", "blue")
            return

        success_count = 0
        for chap in chapters:
            chap_num, title, content = chap
            self.gui_log(f"⬆️ 正在上傳：第 {chap_num} 章...")
            
            payload = {
                "api_key": WEB_API_KEY,
                "action": "sync_chapter",
                "novel_name": novel_name,
                "setting": setting,
                "chapter_num": chap_num,
                "title": title,
                "content": content,
                "global_summary": global_summary
            }
            try:
                res = requests.post(WEB_API_URL, json=payload, timeout=15)
                if res.status_code == 200 and res.json().get("success"):
                    success_count += 1
            except Exception as e:
                self.gui_log(f"⚠️ 第 {chap_num} 章上傳失敗: {e}")
            
            time.sleep(0.5)

        self.gui_log(f"✅ 舊書同步完成！共成功確認/上傳 {success_count} 章。")
        self.update_status("狀態：待命中心", "blue")

    def start_generate_chapter(self):
        if not self.current_novel_id:
            messagebox.showwarning("警告", "請先選擇或建立一本小說！")
            return
        
        user_outline = self.outline_area.get("1.0", tk.END).strip()
        if not user_outline:
            messagebox.showwarning("警告", "請先在中間的區塊輸入【本章劇情綱要】！\nAI 需要您的指示才能創作。")
            return

        if self.is_running: 
            return
            
        self.is_running = True
        self.novel_combo.config(state="disabled") 
        self.update_status("狀態：根據您的綱要爆肝創作中...", "red")
        threading.Thread(target=self.generate_chapter_worker, args=(user_outline,), daemon=True).start()

    def stop_ai(self):
        if self.is_running:
            self.is_running = False
            self.update_status("狀態：已發送中斷指令 (待當前請求結束)", "orange")
            self.root.after(0, lambda: self.novel_combo.config(state="readonly"))

    def generate_chapter_worker(self, user_outline):
        try:
            c = self.conn.cursor()
            novel_id = self.current_novel_id

            # --- 準備階段：讀取資料庫狀態 ---
            c.execute("""SELECT name, setting, setting_record, event_record, foreshadow_record, 
                                last_chap_summary, global_summary, saved_context 
                         FROM novels WHERE id=?""", (novel_id,))
            novel_name, setting, setting_record, event_record, foreshadow_record, last_chap_summary, global_summary, saved_context = c.fetchone()
            
            c.execute("SELECT MAX(chapter_num) FROM chapters WHERE novel_id=?", (novel_id,))
            max_chap = c.fetchone()[0]
            next_chap = (max_chap or 0) + 1

            last_chapter_content = ""
            if max_chap and max_chap > 0:
                c.execute("SELECT content FROM chapters WHERE novel_id=? AND chapter_num=?", (novel_id, max_chap))
                row = c.fetchone()
                if row and row[0]:
                    # 💡 修改 1：原本 1500 字太多了！改成只抓最後 400 字。
                    # 只留最後幾個段落用來「接續語氣與動作」，避免 AI 看到太多舊文忍不住照抄。
                    last_chapter_content = row[0][-400:] 

            self.gui_log(f"\n=======================")
            self.gui_log(f"📝 開始執行：準備根據您的綱要創作第 {next_chap} 章")
            
            style_match = re.search(r'【作品風格走向】：(.*?)\n', setting)
            current_style = style_match.group(1) if style_match else "一般網文"

            # 步驟 1 已經由使用者提供 (user_outline)
            self.gui_log("📝 [步驟 1] 已接收使用者指定的劇情綱要。")
            outline_content = user_outline

            if next_chap == 1:
                self.gui_log("🌟 檢測為第一章，使用初始資料進行開局創作...")
                context = f"【初始設定】：\n{setting}\n"
                draft_prompt = f"{context}\n\n【本章劇情綱要(由作者指定)】：\n{outline_content}\n\n請依照上述設定與劇情綱要，撰寫第 {next_chap} 章的完整初稿正文，並再次提醒：不要輸出任何段落小標題。"
            else:
                self.gui_log("📖 結合前一章末段原文與三維資訊，進行無縫延續創作...")
                # 💡 修改 2：強化 Prompt 語氣，嚴格禁止 AI 鬼打牆重複上一章
                context = (
                    f"【初始設定】：\n{setting}\n\n"
                    f"【目前世界觀與全局狀態】：\n{global_summary}\n\n"
                    f"【上一章劇情摘要 (僅供了解背景，絕對不可重寫這段)】：\n{last_chap_summary}\n\n"
                    f"====================\n"
                    f"【上一章結尾原文 (請緊密接續這段話往下寫新劇情，不要重複)】：\n"
                    f"...(前略)...\n{last_chapter_content}\n"
                    f"====================\n"
                )
                
                draft_prompt = (
                    f"{context}\n"
                    f"【本章劇情綱要 (請務必按照此綱要發展劇情)】：\n{outline_content}\n\n"
                    f"【寫作指令】：\n"
                    f"不要輸出任何段落小標題或多餘廢話。"
                )
            
            c.execute("UPDATE novels SET saved_context = ? WHERE id = ?", (context, novel_id))
            self.conn.commit()

            # 步驟 2：【上文 A + 使用者綱要 -> 寫出初稿】
            self.gui_log("✍️ [步驟 2] 根據您的綱要撰寫本章初稿...")
            
            # 💡 修改 3：系統指令 (System Prompt) 同步加強
            writer_sys_prompt = (
                f"你是一位頂級的網路小說家。\n"
                f"【最高指令】：本作品的核心風格為『{current_style}』！\n"
                f"你的遣詞造句、情境描寫與劇情節奏，要貼近這個風格。\n"
                f"【排版與寫作警告】：\n"
                f"1. 這是一篇正式的小說正文，不是企劃書！**絕對不可**在內文中出現「起」、「承」、「轉」、「合」等結構性小標題。\n"
                f"2. 必須直接推進新劇情，嚴禁水字數或重複舊章節的劇情！"
            )
            
            draft_content = self.call_ai_with_retry(f"第{next_chap}章初稿", writer_sys_prompt, draft_prompt)
            if not draft_content:
                self.gui_log("⚠️ 初稿寫作失敗或被中斷。")
                return
                
            # 💡 新增這行：把初稿直接當作最終正文內容，讓後面的程式可以順利接手！
            content = draft_content

            # ================= 寫作流程改造結束 =================

            title_sys = "你是一個小說編輯。請根據內文為這章下一個吸引人的標題。請只輸出標題文字，不要加書名號、不要加上'第X章'、不要任何其他廢話。"
            title_res = self.call_ai_with_retry("標題命名", title_sys, f"內文：{content[:1500]}")
            clean_title = title_res.strip() if title_res else "無題"
            full_title = f"第{next_chap}章 {clean_title}"

            c.execute("""INSERT INTO chapters 
                         (novel_id, chapter_num, title, content,
                          setting_record, event_record, foreshadow_record, last_chap_summary, global_summary) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                      (novel_id, next_chap, full_title, content,
                       setting_record, event_record, foreshadow_record, last_chap_summary, global_summary))
            self.conn.commit()
            self.root.after(0, self.refresh_chapter_list) 
            self.gui_log(f"📦 正文與保底快照存檔成功：《{full_title}》")

            # 🌐 在本地存檔成功後，立刻觸發上傳到網站！ 🌐
            self.gui_log("🌐 正在將最新章節同步上傳至網站...")
            self.sync_to_website(novel_name, setting, next_chap, full_title, content, global_summary)

            # ================= 核心記憶庫拆分更新開始 =================
            self.gui_log("🌍 讀取最新章節，分別更新核心記憶庫 (設定/事件/伏筆)...")

            # 1. 獨立更新【設定狀態】
            self.gui_log("🔍 [1/3] 更新設定狀態...")
            setting_sys = (
                f"你是一位頂級的劇情統籌編輯。這部小說的風格是：【{current_style}】。\n"
                "請根據【舊有設定】與【最新一章正文】，更新主角狀態、修為、裝備、友軍位置與世界觀變動。\n"
                "請直接輸出更新後的內容，不要加上任何評論或 XML 標籤。"
            )
            setting_user = f"【舊有設定】：\n{setting_record}\n\n【最新一章正文】：\n{content}\n\n請輸出更新後的設定："
            new_setting = self.call_ai_with_retry("更新設定", setting_sys, setting_user) 
            new_setting = new_setting.strip() if new_setting else setting_record

            # 2. 獨立更新【事件紀錄】
            self.gui_log("🔍 [2/3] 更新事件紀錄...")
            event_sys = (
                f"你是一位頂級的劇情統籌編輯。這部小說的風格是：【{current_style}】。\n"
                "請根據【舊有事件】與【最新一章正文】，更新主要任務、重大事件與戰鬥結果。\n"
                "請保留舊資訊並依時間線排列，已完成的任務請標註。直接輸出內容，不要加上任何評論或 XML 標籤。"
            )
            event_user = f"【舊有事件】：\n{event_record}\n\n【最新一章正文】：\n{content}\n\n請輸出更新後的事件："
            new_event = self.call_ai_with_retry("更新事件", event_sys, event_user)
            new_event = new_event.strip() if new_event else event_record

            # 3. 獨立更新【伏筆紀錄】
            self.gui_log("🔍 [3/3] 更新伏筆紀錄...")
            foreshadow_sys = (
                f"你是一位頂級的劇情統籌編輯。這部小說的風格是：【{current_style}】。\n"
                "請根據【舊有伏筆】與【最新一章正文】，更新尚未解開的謎團與懸念。\n"
                "若伏筆在最新章已解開，請刪除或標註已解開。直接輸出內容，不要加上任何評論或 XML 標籤。"
            )
            foreshadow_user = f"【舊有伏筆】：\n{foreshadow_record}\n\n【最新一章正文】：\n{content}\n\n請輸出更新後的伏筆："
            new_foreshadow = self.call_ai_with_retry("更新伏筆", foreshadow_sys, foreshadow_user)
            new_foreshadow = new_foreshadow.strip() if new_foreshadow else foreshadow_record

            # 4. 生成【全局劇情總覽】
            self.gui_log("📝 統整最新資訊，生成全局劇情總覽...")
            summary_sys = (
                f"你是一位頂級的劇情統籌編輯。這部小說的風格是：【{current_style}】。\n"
                "請將以下最新的設定、事件與伏筆資訊，融合成一段約 300 字的「全局劇情總覽」。\n"
                "這段文字將作為 AI 寫下一章時的最高指導原則，必須精煉、連貫且具備劇情推進的方向性。直接輸出內容即可。"
            )
            summary_user = f"【最新設定】：\n{new_setting}\n\n【最新事件】：\n{new_event}\n\n【最新伏筆】：\n{new_foreshadow}\n\n請輸出全局總覽："
            new_global_summary = self.call_ai_with_retry("更新總覽", summary_sys, summary_user)
            new_global_summary = new_global_summary.strip() if new_global_summary else global_summary

            # 5. 生成【單章詳細摘要】
            self.gui_log("🧠 生成單章詳細摘要...")
            single_sum_sys = (
                f"你是一位極其細心的紀錄員。這部小說的風格是【{current_style}】。\n"
                "請將這章內容濃縮為『單章詳細摘要』。請保留人物的決策、情緒反應與伏筆細節，這將提供給下一章作上下文銜接。"
            )
            new_last_chap_summary = self.call_ai_with_retry("單章摘要", single_sum_sys, f"剛寫好的章節內容：\n{content}")
            new_last_chap_summary = new_last_chap_summary.strip() if new_last_chap_summary else last_chap_summary

            # ================= 存入原先資料庫的位置 =================
            self.gui_log("💾 將拆分處理好的記憶，分別存入原對應的資料庫欄位...")
            
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
            self.gui_log("✅ 核心記憶庫已完美更新並存檔！")
            
            # 清空使用者的劇本輸入框，為下一章做準備
            self.root.after(0, lambda: self.outline_area.delete("1.0", tk.END))
            self.gui_log(f"🎉 第 {next_chap} 章流程完全結束，等待您輸入下一章的綱要。")

        finally:
            self.is_running = False
            self.update_status("狀態：待命中心 (請輸入下一章綱要)", "blue")
            self.root.after(0, lambda: self.novel_combo.config(state="readonly"))





if __name__ == "__main__":
    root = tk.Tk()
    app = NovelAIAgent(root)
    root.mainloop()
