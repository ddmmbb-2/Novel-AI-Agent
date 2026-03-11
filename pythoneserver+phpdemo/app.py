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
WEB_API_URL = "https://替換成你網站實際的 api.php 網址.php" 
WEB_API_KEY = "替換成你的KEY 然後記得網站也要一樣"

class NovelAIAgent:
    def __init__(self, root):
        self.root = root
        self.root.title("龍小貓 AI 爆肝創作系統 (V5 雲端同步旗艦版)")
        self.root.geometry("1400x850")
        self.is_running = False
        self.current_novel_id = None
        
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

        self.work_frame = tk.Frame(self.main_pane)
        tk.Label(self.work_frame, text="🤖 系統狀態與日誌", font=("Arial", 10, "bold")).pack(pady=5)
        self.log_area = scrolledtext.ScrolledText(self.work_frame, wrap=tk.WORD, width=35, bg="#2c3e50", fg="#ecf0f1", font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.work_frame)

        self.list_frame = tk.Frame(self.main_pane)
        tk.Label(self.list_frame, text="📜 章節清單", font=("Arial", 10, "bold")).pack(pady=5)
        self.chapter_listbox = tk.Listbox(self.list_frame, width=30, font=("Microsoft JhengHei", 10))
        self.chapter_listbox.pack(fill=tk.BOTH, expand=1)
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        self.rewrite_btn = tk.Button(self.list_frame, text="⏪ 從選定章節開始重寫", command=self.rollback_to_chapter, bg="#e67e22", fg="white", font=("Arial", 10, "bold"))
        self.rewrite_btn.pack(fill=tk.X, pady=5)
        self.main_pane.add(self.list_frame)

        self.read_frame = tk.Frame(self.main_pane)
        tk.Label(self.read_frame, text="📖 閱讀區 (繁體中文)", font=("Arial", 10, "bold")).pack(pady=5)
        self.read_area = scrolledtext.ScrolledText(self.read_frame, wrap=tk.WORD, width=80, font=("Microsoft JhengHei", 12), spacing3=10)
        self.read_area.pack(fill=tk.BOTH, expand=1)
        self.main_pane.add(self.read_frame)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ 開始自動創作", command=self.start_thread, bg="#27ae60", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.start_btn.pack(side=tk.LEFT, padx=20)
        
        self.stop_btn = tk.Button(btn_frame, text="⏸ 暫停創作", command=self.stop_ai, bg="#c0392b", fg="white", font=("Arial", 11, "bold"), padx=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 🌟 新增：手動同步舊書按鈕
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
        chapter_num = re.search(r'第 (\d+) 章', chapter_text).group(1)
        
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

    # 🌟 新增：手動打包同步所有舊章節 🌟
    def sync_all_old_chapters(self):
        if not self.current_novel_id:
            messagebox.showwarning("警告", "請先在上方選擇一本你要同步的小說！")
            return
        if self.is_running:
            messagebox.showwarning("警告", "請先暫停 AI 創作，再進行手動同步操作！")
            return

        if not messagebox.askyesno("同步確認", "確定要將這本小說的【所有舊章節】重新上傳到網站嗎？\n(已存在的章節網站會自動略過)"):
            return

        # 使用獨立執行緒避免畫面卡住
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
            
            # 稍微停頓一下，避免瞬間發出太多請求把網站塞爆
            time.sleep(0.5)

        self.gui_log(f"✅ 舊書同步完成！共成功確認/上傳 {success_count} 章。")
        self.update_status("狀態：待命中心", "blue")

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
            c.execute("""SELECT name, setting, setting_record, event_record, foreshadow_record, 
                                last_chap_summary, global_summary, saved_context 
                         FROM novels WHERE id=?""", (novel_id,))
            novel_name, setting, setting_record, event_record, foreshadow_record, last_chap_summary, global_summary, saved_context = c.fetchone()
            
            c.execute("SELECT MAX(chapter_num) FROM chapters WHERE novel_id=?", (novel_id,))
            max_chap = c.fetchone()[0]
            next_chap = (max_chap or 0) + 1

            self.gui_log(f"\n=======================")
            self.gui_log(f"📝 開始執行循環：準備創作第 {next_chap} 章")
            
            style_match = re.search(r'【作品風格走向】：(.*?)\n', setting)
            current_style = style_match.group(1) if style_match else "一般網文"

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
            
            c.execute("UPDATE novels SET saved_context = ? WHERE id = ?", (context, novel_id))
            self.conn.commit()

            # ================= 寫作流程改造開始 =================

            # 步驟 1：【上文 A -> 產生本章劇情綱要】
            self.gui_log("📝 [步驟 1] 構思本章劇情綱要...")
            outline_sys_prompt = (
                f"你是一位專業的小說企劃。這部小說的核心風格是『{current_style}』。\n"
                f"請根據提供的上下文，為即將撰寫的第 {next_chap} 章設計出精彩且結構完整的「劇情綱要」。\n"
                f"請條理分明地列出本章的起承轉合，以及重要角色的互動重點。"
            )
            outline_content = self.call_ai_with_retry(f"第{next_chap}章綱要", outline_sys_prompt, context)
            if not outline_content:
                self.gui_log("⚠️ 劇情綱要生成失敗，自動暫停。")
                self.stop_ai()
                break

            # 步驟 2：【上文 A + 劇情綱要 -> 寫出初稿】
            self.gui_log("✍️ [步驟 2] 根據綱要撰寫本章初稿...")
            writer_sys_prompt = (
                f"你是一位頂級的網路小說家。\n"
                f"【最高指令】：本作品的核心風格為『{current_style}』！\n"
                f"你的遣詞造句、情境描寫與劇情節奏，都必須死死咬住這個風格，絕對不能寫成平庸無聊的流水帳。"
            )
            # 將上文 (context) 與剛剛生成的綱要 (outline_content) 結合
            draft_prompt = f"{context}\n\n【本章劇情綱要】：\n{outline_content}\n\n請嚴格遵守上述設定與劇情綱要，撰寫第 {next_chap} 章的完整初稿正文。"
            
            draft_content = self.call_ai_with_retry(f"第{next_chap}章初稿", writer_sys_prompt, draft_prompt)
            if not draft_content:
                self.gui_log("⚠️ 初稿寫作失敗，為保護進度，自動暫停運行。")
                self.stop_ai()
                break

            # 步驟 3：【無上文 A，僅針對初稿 -> 進行優化潤飾】
            self.gui_log("✨ [步驟 3] 進行文筆深度優化與潤飾...")
            polish_sys_prompt = (
                f"你是一位頂級的小說編輯與潤色專家。這部小說的風格是『{current_style}』。\n"
                f"請將以下的小說初稿進行深度優化與潤飾，提升文筆流暢度、加強動作神態與環境渲染。\n"
                f"【嚴格規定】：\n"
                f"1. 絕對不可改變原本的劇情走向、事件結果與人物對話核心意思。\n"
                f"2. 請直接輸出潤飾後的完整小說正文，不要加上任何評論或廢話。"
            )
            # 這裡只傳入初稿內容，不再包含上文 A
            content = self.call_ai_with_retry(f"第{next_chap}章潤飾", polish_sys_prompt, f"【需要潤飾的初稿】：\n{draft_content}")
            if not content:
                self.gui_log("⚠️ 潤飾失敗，為保護進度，自動暫停運行。")
                self.stop_ai()
                break

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

            self.gui_log("🌍 讀取最新章節，提煉並更新核心記憶庫 (狀態/事件/伏筆)...")
            
            combo_sys = (
                f"你是一位頂級的劇情統籌編輯。這部小說的風格是：【{current_style}】。\n"
                "你的任務是根據【舊有記憶】與【最新一章正文】，更新並整理出最精準的「最新記憶狀態」。\n"
                "【核心原則：去蕪存菁】：\n"
                "1. 保留尚未解決的重要資訊（如長期目標、未解謎團）。\n"
                "2. 保留舊資訊但需依時間線排列清楚,可以簡化舊資訊但不能刪除（如敵人死亡、任務完成、伏筆解開，請將其標註清楚）。\n"
                "3. 加入最新章節帶來的新變化。\n"
                "【最高指令】：嚴格使用指定的 XML 標籤包覆內容，不要輸出標籤以外的廢話。\n\n"
                "請按以下格式輸出：\n"
                "<SETTING>\n這裡填寫：\n- 主角當前狀態 (詳細修為/等級/心境/受傷狀況)\n- 核心裝備與重要財產清單\n- 友軍與重要配角名單及當前位置\n- 世界觀或地圖環境變動\n</SETTING>\n"
                "<EVENT>\n這裡填寫：\n- 目前正在進行的主要任務或目標\n- 近期發生的重大事件與戰鬥結果\n- 當前遭遇的困境或敵對勢力動向\n</EVENT>\n"
                "<FORESHADOW>\n這裡填寫：\n- 尚未解開的謎團\n- 刻意留下的懸念與未來的衝突點\n</FORESHADOW>\n"
                "<SUMMARY>\n這裡填寫：\n- 將上述資訊融合成一段約 300 字的「全局劇情總覽」。\n- 這段文字將作為 AI 寫下一章時的最高指導原則，必須精煉、連貫且具備劇情推進的方向性。\n</SUMMARY>"
            )
            
            combo_user = (
                f"【舊有設定與狀態】：\n{setting_record}\n\n"
                f"【舊有事件與任務】：\n{event_record}\n\n"
                f"【舊有伏筆與懸念】：\n{foreshadow_record}\n\n"
                f"====================\n"
                f"【剛寫好的最新章節正文】：\n{content}\n"
                f"====================\n"
                "請根據以上資訊，仔細比對並輸出更新後的 <SETTING>、<EVENT>、<FORESHADOW> 與 <SUMMARY>。"
            )

            memory_res = self.call_ai_with_retry("更新核心記憶庫", combo_sys, combo_user)
            
            new_setting, new_event, new_foreshadow, new_global_summary = setting_record, event_record, foreshadow_record, global_summary
            update_success = False

            if memory_res:
                try:
                    # 使用正則表達式 (Regex) 安全提取標籤內的內容，無視 AI 輸出的多餘換行或廢話
                    setting_match = re.search(r'<SETTING>(.*?)</SETTING>', memory_res, re.DOTALL | re.IGNORECASE)
                    event_match = re.search(r'<EVENT>(.*?)</EVENT>', memory_res, re.DOTALL | re.IGNORECASE)
                    foreshadow_match = re.search(r'<FORESHADOW>(.*?)</FORESHADOW>', memory_res, re.DOTALL | re.IGNORECASE)
                    summary_match = re.search(r'<SUMMARY>(.*?)</SUMMARY>', memory_res, re.DOTALL | re.IGNORECASE)

                    if setting_match and event_match and foreshadow_match and summary_match:
                        new_setting = setting_match.group(1).strip()
                        new_event = event_match.group(1).strip()
                        new_foreshadow = foreshadow_match.group(1).strip()
                        new_global_summary = summary_match.group(1).strip()
                        update_success = True
                        self.gui_log("✅ 核心記憶庫 (設定/事件/伏筆/總覽) 更新成功！格式完美。")
                    else:
                        self.gui_log("⚠️ AI 未依格式輸出完整標籤，將保留舊有資訊以防記憶損壞。")
                        self.gui_log(f"🕵️ Debug 輸出預覽: {memory_res[:150]}...")
                except Exception as e:
                    self.gui_log(f"⚠️ 核心記憶庫解析異常: {e}，啟動安全防護，保留舊有資訊。")

            self.gui_log("🧠 讀取最新章節，生成單章詳細摘要...")
            single_sum_sys = (
                f"你是一位極其細心的紀錄員。這部小說的風格是【{current_style}】。\n"
                "請將這章內容濃縮為『單章詳細摘要』。除了記錄發生的事件外，"
                "請務必保留『人物的決策、情緒反應與伏筆細節』，這將直接提供給下一章的作者作為上下文銜接。"
            )
            new_last_chap_summary = self.call_ai_with_retry("單章摘要生成", single_sum_sys, f"剛寫好的章節內容：\n{content}")

            if new_last_chap_summary:
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
                
                if update_success:
                    self.gui_log("✅ 最新記憶快照已完美覆蓋。")
                else:
                    self.gui_log("⚠️ 已使用舊記憶作為本章的保底快照，確保時光倒流不斷鏈。")

            self.gui_log("⏳ 單章循環結束，準備進入下一個循環。")
            if not self.is_running:
                break
                
            for i in range(10, 0, -1):
                if not self.is_running: 
                    break 
                self.update_status(f"狀態：機器散熱休息中... 剩餘 {i} 秒", "green")
                time.sleep(1)
            
            if self.is_running:
                self.update_status("狀態：爆肝創作中...", "red")

        self.gui_log("🛑 系統已安全暫停。")
        self.update_status("狀態：待命中心", "blue")
        self.root.after(0, lambda: self.novel_combo.config(state="readonly"))

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelAIAgent(root)
    root.mainloop()