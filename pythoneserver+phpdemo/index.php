<?php
// 連接我們後台建立的同一個資料庫
$db_file = __DIR__ . '/novel_agent_v5.db';
try {
    $pdo = new PDO("sqlite:" . $db_file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$pdo->exec('PRAGMA journal_mode = wal;'); // 開啟 WAL 模式 (讀寫並行)
    $pdo->exec('PRAGMA busy_timeout = 5000;'); // 如果真的遇到鎖，最多等待 5 秒而不是直接報錯

} catch (Exception $e) {
    die("資料庫連線失敗，請確認後台是否已正確建立資料庫！");
}

// 路由判斷 (書架 -> 書籍詳情 -> 閱讀頁面)
$book_id = isset($_GET['book']) ? (int)$_GET['book'] : 0;
$chapter_num = isset($_GET['chapter']) ? (int)$_GET['chapter'] : 0;

$view = 'home';
if ($book_id > 0 && $chapter_num > 0) {
    $view = 'read';
} elseif ($book_id > 0) {
    $view = 'detail';
}
?>
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>龍小貓的幻夢書閣</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* 日間模式變數 */
            --bg-color: #fdfbf7;
            --text-color: #2c3e50;
            --read-bg: #f4ecd8; /* 護眼紙張色 */
            --nav-bg: rgba(255, 255, 255, 0.9);
            --card-bg: #ffffff;
            --primary: #8e44ad;
        }
        body.dark-mode {
            /* 夜間模式變數 */
            --bg-color: #121212;
            --text-color: #e0e0e0;
            --read-bg: #1e1e1e;
            --nav-bg: rgba(18, 18, 18, 0.95);
            --card-bg: #2c2c2c;
            --primary: #bb86fc;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Noto Sans TC', sans-serif;
            transition: background-color 0.3s, color 0.3s;
            padding-top: 60px; /* 給固定導覽列留空間 */
        }
        /* 導覽列 (毛玻璃效果) */
        .navbar-custom {
            background-color: var(--nav-bg);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        .navbar-brand { font-weight: 700; color: var(--primary) !important; letter-spacing: 1px; }
        
        /* 書籍卡片設計 (無圖片也能很華麗) */
        .book-card {
            background-color: var(--card-bg);
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            height: 100%;
        }
        .book-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        .book-cover-mock {
            height: 200px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px 12px 0 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5rem;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            padding: 20px;
            text-align: center;
        }
        
        /* 閱讀區設計 */
        .read-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: var(--read-bg);
            padding: 40px 30px;
            border-radius: 8px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.03);
            min-height: 80vh;
        }
        .read-title {
            font-family: 'Noto Serif TC', serif;
            font-size: 2rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 30px;
            color: var(--primary);
        }
        .read-content {
            font-family: 'Noto Serif TC', serif;
            font-size: 1.2rem; /* 預設大小，可透過JS調整 */
            line-height: 2;
            text-align: justify;
            white-space: pre-wrap; /* 保留換行 */
        }
        
        /* 浮動控制工具列 (右下角) */
        .tools-fab {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 1000;
        }
        .tool-btn {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            border: none;
            background-color: var(--primary);
            color: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .tool-btn:hover { transform: scale(1.1); }
        
        /* 章節目錄按鈕 */
        .chapter-btn {
            display: block;
            padding: 12px 15px;
            margin-bottom: 8px;
            background: var(--card-bg);
            border: 1px solid rgba(0,0,0,0.05);
            border-radius: 8px;
            color: var(--text-color);
            text-decoration: none;
            transition: all 0.2s;
        }
        .chapter-btn:hover {
            background: var(--primary);
            color: white;
            transform: translateX(5px);
        }
        
        /* 手機版優化 */
        @media (max-width: 768px) {
            .read-container { padding: 20px 15px; }
            .read-title { font-size: 1.5rem; }
            .read-content { font-size: 1.1rem; }
        }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg fixed-top navbar-custom">
    <div class="container">
        <a class="navbar-brand" href="index.php">📖 幻夢書閣</a>
        <div class="d-flex">
            <?php if ($view !== 'home'): ?>
                <a href="index.php" class="btn btn-outline-secondary btn-sm me-2">回首頁</a>
            <?php endif; ?>
            <?php if ($view === 'read'): ?>
                <a href="index.php?book=<?= $book_id ?>" class="btn btn-outline-secondary btn-sm">回目錄</a>
            <?php endif; ?>
        </div>
    </div>
</nav>

<div class="container my-4">

<?php if ($view === 'home'): ?>
    <div class="row text-center mb-5 mt-3">
        <div class="col-12">
            <h2 class="fw-bold" style="color: var(--primary);">探索 AI 創作的無限宇宙</h2>
            <p class="text-muted">點擊書籍封面，進入閱讀世界</p>
        </div>
    </div>
    
    <div class="row row-cols-1 row-cols-md-3 row-cols-lg-4 g-4">
        <?php
        // 取得所有書籍，並順便抓取最新章節數
        $novels = $pdo->query("SELECT n.id, n.name, n.setting, (SELECT MAX(chapter_num) FROM chapters WHERE novel_id = n.id) as max_chap FROM novels n ORDER BY n.id DESC")->fetchAll();
        
        if (empty($novels)): ?>
            <div class="col-12 text-center text-muted py-5">
                <h4>目前書架空空如也</h4>
                <p>請前往後台 (admin.php) 建立新書並開始 AI 爆肝創作！</p>
            </div>
        <?php else: 
            // 隨機漸層色系給書本封面
            $gradients = [
                'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
                'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)',
                'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
                'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)'
            ];
            foreach ($novels as $index => $book): 
                $bg = $gradients[$index % count($gradients)];
                // 擷取設定中的風格標籤
                preg_match('/【作品風格.*?】：(.*?)\n/s', $book['setting'], $matches);
                $tags = isset($matches[1]) ? htmlspecialchars($matches[1]) : '奇幻文學';
                $total_chaps = $book['max_chap'] ? $book['max_chap'] : 0;
        ?>
            <div class="col">
                <div class="book-card" onclick="location.href='index.php?book=<?= $book['id'] ?>'">
                    <div class="book-cover-mock" style="background: <?= $bg ?>;">
                        <?= htmlspecialchars($book['name']) ?>
                    </div>
                    <div class="card-body p-3">
                        <h5 class="card-title fw-bold text-truncate" title="<?= htmlspecialchars($book['name']) ?>">
                            <?= htmlspecialchars($book['name']) ?>
                        </h5>
                        <p class="card-text text-muted small mb-1">🏷️ <?= $tags ?></p>
                        <p class="card-text text-muted small">📜 共 <?= $total_chaps ?> 章</p>
                    </div>
                </div>
            </div>
        <?php endforeach; endif; ?>
    </div>

<?php elseif ($view === 'detail'): ?>
    <?php
    $stmt = $pdo->prepare("SELECT * FROM novels WHERE id = ?");
    $stmt->execute([$book_id]);
    $book = $stmt->fetch();
    
    if (!$book) die("找不到該書籍。");
    
    $stmt = $pdo->prepare("SELECT chapter_num, title FROM chapters WHERE novel_id = ? ORDER BY chapter_num ASC");
    $stmt->execute([$book_id]);
    $chapters = $stmt->fetchAll();
    
    // 整理設定文字作為簡介
    $intro = htmlspecialchars(str_replace('【詳細世界觀與設定】：', '', $book['setting']));
    ?>
    <div class="row justify-content-center mt-3">
        <div class="col-lg-8">
            <div class="p-4 mb-4" style="background: var(--card-bg); border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                <h2 class="fw-bold" style="color: var(--primary);"><?= htmlspecialchars($book['name']) ?></h2>
                <hr>
                <h5 class="fw-bold">作品簡介：</h5>
                <p class="text-muted" style="white-space: pre-wrap; line-height: 1.8;"><?= $intro ?></p>
                
                <?php if($chapters): ?>
                    <div class="mt-4">
                        <a href="index.php?book=<?= $book_id ?>&chapter=1" class="btn btn-primary px-4 py-2 fw-bold" style="background-color: var(--primary); border:none;">開始閱讀 第一章</a>
                    </div>
                <?php endif; ?>
            </div>

            <h4 class="fw-bold mt-5 mb-3">📜 章節目錄</h4>
            <div class="chapter-list">
                <?php if (empty($chapters)): ?>
                    <p class="text-muted">AI 正在努力撰寫中，請稍候...</p>
                <?php else: ?>
                    <?php foreach ($chapters as $ch): ?>
                        <a href="index.php?book=<?= $book_id ?>&chapter=<?= $ch['chapter_num'] ?>" class="chapter-btn d-flex justify-content-between">
                            <span>第 <?= $ch['chapter_num'] ?> 章</span>
                            <span><?= htmlspecialchars($ch['title']) ?></span>
                        </a>
                    <?php endforeach; ?>
                <?php endif; ?>
            </div>
        </div>
    </div>

<?php elseif ($view === 'read'): ?>
    <?php
    $stmt = $pdo->prepare("SELECT * FROM chapters WHERE novel_id = ? AND chapter_num = ?");
    $stmt->execute([$book_id, $chapter_num]);
    $chapter = $stmt->fetch();
    
    if (!$chapter) die("<div class='text-center mt-5'><h3>章節不存在或 AI 還在寫！</h3><a href='index.php?book=$book_id' class='btn btn-primary mt-3'>回目錄</a></div>");
    
    // 取得最大章節數以判斷是否有「下一章」
    $stmt = $pdo->prepare("SELECT MAX(chapter_num) FROM chapters WHERE novel_id = ?");
    $stmt->execute([$book_id]);
    $max_chap = $stmt->fetchColumn();
    ?>
    
<div class="tools-fab">
        <button id="langBtn" class="tool-btn" onclick="toggleLanguage()" title="切換繁/簡體">繁</button>
        
        <button class="tool-btn" onclick="toggleTheme()" title="切換日/夜模式">🌙</button>
        <button class="tool-btn" onclick="changeFontSize(2)" title="放大字體">A+</button>
        <button class="tool-btn" onclick="changeFontSize(-2)" title="縮小字體">A-</button>
    </div>

    <div class="read-container mt-3">
        <h1 class="read-title"><?= htmlspecialchars($chapter['title']) ?></h1>
        
        <div class="read-content" id="textContent"><?= htmlspecialchars($chapter['content']) ?></div>
        
        <hr class="my-5" style="opacity: 0.1;">
        
        <div class="d-flex justify-content-between align-items-center">
            <?php if ($chapter_num > 1): ?>
                <a href="index.php?book=<?= $book_id ?>&chapter=<?= $chapter_num - 1 ?>" class="btn btn-outline-secondary px-4 py-2">上一章</a>
            <?php else: ?>
                <button class="btn btn-outline-secondary px-4 py-2" disabled>已是第一章</button>
            <?php endif; ?>
            
            <a href="index.php?book=<?= $book_id ?>" class="text-muted text-decoration-none">返回目錄</a>
            
            <?php if ($chapter_num < $max_chap): ?>
                <a href="index.php?book=<?= $book_id ?>&chapter=<?= $chapter_num + 1 ?>" class="btn btn-primary px-4 py-2" style="background-color: var(--primary); border:none;">下一章</a>
            <?php else: ?>
                <button class="btn btn-outline-secondary px-4 py-2" disabled>作者爆肝中</button>
            <?php endif; ?>
        </div>
    </div>
<?php endif; ?>

</div>
<script src="https://cdn.jsdelivr.net/npm/opencc-js@1.0.5/dist/umd/full.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // 紀錄字體大小與主題狀態 (使用 localStorage 讓重整後記憶)
    let currentFontSize = parseInt(localStorage.getItem('readFontSize')) || 18; // 預設 18px
    let isDarkMode = localStorage.getItem('darkMode') === 'true';
    
    // --- 新增：繁簡轉換變數 ---
    let currentLang = localStorage.getItem('readLang') || 'tw'; 
    let converterTW2CN = null;
    let converterCN2TW = null;

    // 初始化設定
    window.onload = () => {
        applyTheme();
        if (document.getElementById('textContent')) {
            document.getElementById('textContent').style.fontSize = currentFontSize + 'px';
        }
        initLanguage(); // 啟動繁簡轉換機制
    };

    // --- 新增：繁簡轉換核心邏輯 ---
    function initLanguage() {
        // 確保 OpenCC 已經從 CDN 載入完畢
        if (typeof OpenCC === 'undefined') {
            setTimeout(initLanguage, 100);
            return;
        }
        
        // 建立轉換器 (台灣繁體 -> 大陸簡體 / 大陸簡體 -> 台灣繁體)
        converterTW2CN = OpenCC.Converter({ from: 'tw', to: 'cn' });
        converterCN2TW = OpenCC.Converter({ from: 'cn', to: 'tw' });
        
        const langBtn = document.getElementById('langBtn');
        if (currentLang === 'cn') {
            if (langBtn) langBtn.innerText = '簡';
            convertTo('cn');
        } else {
            if (langBtn) langBtn.innerText = '繁';
        }
    }

    function toggleLanguage() {
        if (!converterTW2CN || !converterCN2TW) return; // 避免 CDN 尚未載入時按鈕報錯
        
        const langBtn = document.getElementById('langBtn');
        if (currentLang === 'tw') {
            currentLang = 'cn';
            convertTo('cn');
            if (langBtn) langBtn.innerText = '簡';
        } else {
            currentLang = 'tw';
            convertTo('tw');
            if (langBtn) langBtn.innerText = '繁';
        }
        localStorage.setItem('readLang', currentLang); // 記憶讀者選擇
    }

    function convertTo(targetLang) {
        const converter = targetLang === 'cn' ? converterTW2CN : converterCN2TW;
        
        // 使用 TreeWalker 安全地只轉換「文字節點」，絕對不破壞 HTML 標籤結構
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        const nodesToConvert = [];
        let node;
        
        while (node = walker.nextNode()) {
            const parent = node.parentElement;
            // 避開腳本(script)、樣式(style) 標籤
            if (parent && parent.tagName !== 'SCRIPT' && parent.tagName !== 'STYLE' && node.nodeValue.trim() !== '') {
                nodesToConvert.push(node);
            }
        }
        
        // 執行替換
        nodesToConvert.forEach(n => {
            n.nodeValue = converter(n.nodeValue);
        });
    }

    // --- 原有邏輯：調整字體大小 ---
    function changeFontSize(delta) {
        const content = document.getElementById('textContent');
        if (!content) return;
        
        currentFontSize += delta;
        if(currentFontSize < 14) currentFontSize = 14;
        if(currentFontSize > 32) currentFontSize = 32;
        
        content.style.fontSize = currentFontSize + 'px';
        localStorage.setItem('readFontSize', currentFontSize);
    }

    // --- 原有邏輯：切換日夜模式 ---
    function toggleTheme() {
        isDarkMode = !isDarkMode;
        localStorage.setItem('darkMode', isDarkMode);
        applyTheme();
    }

    function applyTheme() {
        const body = document.body;
        // 抓取月亮/太陽按鈕 (因為現在加入繁簡按鈕，月亮變成第二個，所以改用 nth-child)
        const themeBtn = document.querySelector('.tools-fab button:nth-child(2)'); 
        
        if (isDarkMode) {
            body.classList.add('dark-mode');
            if(themeBtn) themeBtn.innerHTML = '☀️';
        } else {
            body.classList.remove('dark-mode');
            if(themeBtn) themeBtn.innerHTML = '🌙';
        }
    }
</script>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>