<?php
// 設置時區
date_default_timezone_set('Asia/Taipei');

// 定義 SQLite 資料庫檔案路徑
$db_file = __DIR__ . '/novel_agent_v5.db';

try {
    // 建立資料庫連線
    $pdo = new PDO("sqlite:" . $db_file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // 🌟 核心防護：開啟 WAL 模式，讓讀者看書(讀取)與 Python上傳(寫入)可以同時進行，不會鎖死！
    $pdo->exec('PRAGMA journal_mode = wal;');
    $pdo->exec('PRAGMA busy_timeout = 5000;');

    // 初始化小說總表 (確保雲端有接收資料的容器)
    $pdo->exec("CREATE TABLE IF NOT EXISTS novels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        setting TEXT,
        setting_record TEXT,
        event_record TEXT,
        foreshadow_record TEXT,
        last_chap_summary TEXT,
        global_summary TEXT,
        saved_context TEXT
    )");

    // 初始化章節內容表
    $pdo->exec("CREATE TABLE IF NOT EXISTS chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        novel_id INTEGER,
        chapter_num INTEGER,
        title TEXT,
        content TEXT,
        setting_record TEXT,
        event_record TEXT,
        foreshadow_record TEXT,
        last_chap_summary TEXT,
        global_summary TEXT
    )");

} catch (PDOException $e) {
    // 萬一伺服器權限設定有問題，會清楚顯示錯誤，而不是白畫面
    die("資料庫連線或初始化失敗: " . $e->getMessage());
}
?>