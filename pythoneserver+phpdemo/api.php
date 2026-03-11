<?php
// api.php
require 'config.php';
header('Content-Type: application/json');

$API_KEY = "替換成你的KEY 然後記得網站也要一樣"; 

$data = json_decode(file_get_contents('php://input'), true);

if (!$data || !isset($data['api_key']) || $data['api_key'] !== $API_KEY) {
    http_response_code(403);
    echo json_encode(["success" => false, "msg" => "拒絕存取：無效的 API KEY"]);
    exit;
}

try {
    $action = $data['action'];

    if ($action === 'sync_chapter') {
        $novel_name = $data['novel_name'];
        $setting = $data['setting'];
        
        // 1. 檢查小說是否存在
        $stmt = $pdo->prepare("SELECT id FROM novels WHERE name = ?");
        $stmt->execute([$novel_name]);
        $novel_id = $stmt->fetchColumn();

        if (!$novel_id) {
            $stmt = $pdo->prepare("INSERT INTO novels (name, setting, global_summary) VALUES (?, ?, ?)");
            $stmt->execute([$novel_name, $setting, $data['global_summary']]);
            $novel_id = $pdo->lastInsertId();
        } else {
            $stmt = $pdo->prepare("UPDATE novels SET global_summary = ? WHERE id = ?");
            $stmt->execute([$data['global_summary'], $novel_id]);
        }

        // 2. 檢查該章節是否已經上傳過，有的話覆蓋，沒有的話新增
        $stmt = $pdo->prepare("SELECT id FROM chapters WHERE novel_id = ? AND chapter_num = ?");
        $stmt->execute([$novel_id, $data['chapter_num']]);
        if ($stmt->fetchColumn()) {
            $stmt = $pdo->prepare("UPDATE chapters SET title = ?, content = ? WHERE novel_id = ? AND chapter_num = ?");
            $stmt->execute([$data['title'], $data['content'], $novel_id, $data['chapter_num']]);
        } else {
            $stmt = $pdo->prepare("INSERT INTO chapters (novel_id, chapter_num, title, content) VALUES (?, ?, ?, ?)");
            $stmt->execute([$novel_id, $data['chapter_num'], $data['title'], $data['content']]);
        }

        echo json_encode(["success" => true, "msg" => "章節同步成功", "novel_id" => $novel_id]);

    } 
    // 🌟 這裡是新增的「雲端時光倒流」功能 🌟
    elseif ($action === 'rollback_chapters') {
        $novel_name = $data['novel_name'];
        $target_chap = $data['chapter_num'];

        $stmt = $pdo->prepare("SELECT id FROM novels WHERE name = ?");
        $stmt->execute([$novel_name]);
        $novel_id = $stmt->fetchColumn();

        if ($novel_id) {
            // 刪除網站上，該章節(含)之後的所有舊未來章節
            $stmt = $pdo->prepare("DELETE FROM chapters WHERE novel_id = ? AND chapter_num >= ?");
            $stmt->execute([$novel_id, $target_chap]);
            echo json_encode(["success" => true, "msg" => "雲端時光倒流成功，已清除舊未來章節"]);
        } else {
            echo json_encode(["success" => false, "msg" => "雲端找不到該小說"]);
        }
    } else {
        echo json_encode(["success" => false, "msg" => "未知的動作"]);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "msg" => $e->getMessage()]);
}
?>