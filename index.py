from flask import Flask, request, jsonify, render_template_string
import os
import re

app = Flask(__name__)

# 載入 history.txt
with open("history.txt", "r", encoding="utf-8") as f:
    raw = f.read()

# 分段處理
raw_segments = re.split(r"[【】#\n\r]+", raw)
segments = []
for seg in raw_segments:
    digits = [int(x) for x in seg if x in "123456"]
    if digits:
        segments.append(digits)

def find_next_digit_counts(segments, pattern):
    counts = [0] * 6
    L = len(pattern)
    for seg in segments:
        for i in range(len(seg) - L):
            if seg[i:i+L] == pattern:
                nxt = seg[i+L]
                counts[nxt-1] += 1
    return counts, sum(counts)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>詳細使用辦法找(Line:19931026a)</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 10px; }
        .highlight { font-size: 1.5em; font-weight: bold; color: red; }
        input { padding: 5px; margin: 5px 0; width: 100%; max-width: 300px; }
        button { padding: 5px 10px; margin-top: 5px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; }
        th, td { border: 1px solid #ccc; padding: 5px; text-align: center; }
        h2, h3 { margin-top: 15px; }
    </style>
</head>
<body>
    <h1>詳細使用辦法找(Line:19931026a)</h1>
    <input id="patternInput" placeholder="輸入前置數字 (如 12345)">
    <button onclick="search()">查詢</button>
    <button onclick="clearRecords()">清除紀錄</button>

    <div id="results"></div>
    <div id="compare"></div>
    <div id="sumTop3"></div>

<script>
let records = [];

async function search() {
    const pattern = document.getElementById("patternInput").value.trim();
    if (!pattern) return alert("請輸入數字");

    const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pattern })
    });
    const data = await res.json();
    if (!data.success) return alert(data.error);

    records.push(data);
    render();
}

function clearRecords() {
    records = [];
    document.getElementById("results").innerHTML = "";
    document.getElementById("compare").innerHTML = "";
    document.getElementById("sumTop3").innerHTML = "";
}

function render() {
    let html = "";
    records.forEach((rec, idx) => {
        html += `<h2>第 ${idx+1} 次查詢 (${rec.pattern.join("")})</h2>`;
        html += "<table><tr><th>數字</th><th>次數</th></tr>";
        rec.results.forEach(r => {
            html += `<tr><td>${r.num}</td><td>${r.count}</td></tr>`;
        });
        html += "</table>";
    });
    document.getElementById("results").innerHTML = html;

    if (records.length === 2) {
        renderCompareTable();
        clearRecords(); // 自動清除紀錄
    }
}

function renderCompareTable() {
    const r1 = records[0].results;
    const r2 = records[1].results;
    const compare = [];

    for (let i = 0; i < 6; i++) {
        const num = i+1;
        const c1 = r1.find(r => r.num === num).count;
        const c2 = r2.find(r => r.num === num).count;
        compare.push({ num, c1, c2 });
    }

    let html = "<h2>共同數字對比表</h2><table><tr><th>數字</th><th>查詢1</th><th>查詢2</th></tr>";
    compare.forEach(r => {
        html += `<tr><td>${r.num}</td><td>${r.c1}</td><td>${r.c2}</td></tr>`;
    });
    html += "</table>";
    document.getElementById("compare").innerHTML = html;

    // === 加總後的統計 ===
    const sumCounts = {};
    compare.forEach(r => { sumCounts[r.num] = r.c1 + r.c2; });

    const sorted = Object.entries(sumCounts).sort((a,b) => b[1]-a[1]);
    const top3 = sorted.slice(0,3);
    const top3Text = top3.map(([num, cnt]) => `${num} (${cnt}次)`).join(", ");

    // 計算單雙大小
    let odd = 0, even = 0, small = 0, big = 0;
    for (const [numStr, cnt] of Object.entries(sumCounts)) {
        const num = parseInt(numStr);
        if ([1,3,5].includes(num)) odd += cnt;
        if ([2,4,6].includes(num)) even += cnt;
        if ([1,2,3].includes(num)) small += cnt;
        if ([4,5,6].includes(num)) big += cnt;
    }

    // 差異文字
    const diffOddEven = odd > even 
        ? `👉 單比雙多 ${odd - even} 次` 
        : even > odd 
            ? `👉 雙比單多 ${even - odd} 次` 
            : "👉 單雙一樣多";

    const diffBigSmall = big > small
        ? `👉 大比小多 ${big - small} 次`
        : small > big
            ? `👉 小比大多 ${small - big} 次`
            : "👉 大小一樣多";

    document.getElementById("sumTop3").innerHTML = `
        <h2>加總後的前三名</h2>
        <p class="highlight">${top3Text}</p>
        <h3>單雙大小統計</h3>
        <p>單 ${odd}，雙 ${even}</p>
        <p>${diffOddEven}</p>
        <p>大 ${big}，小 ${small}</p>
        <p>${diffBigSmall}</p>
    `;
}
</script>
</body>
</html>
    """)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json()
    pattern_str = data.get("pattern", "")
    if not re.fullmatch(r"[1-6]+", pattern_str):
        return jsonify({"success": False, "error": "pattern 只能包含 1–6"})

    pattern = [int(c) for c in pattern_str]
    counts, total = find_next_digit_counts(segments, pattern)
    results = [{"num": i+1, "count": counts[i]} for i in range(6)]
    return jsonify({"success": True, "pattern": pattern, "results": results})

if __name__ == "__main__":
    app.run(debug=True)