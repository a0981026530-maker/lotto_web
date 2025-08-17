from flask import Flask, request, render_template_string, jsonify
import requests
import re
import pandas as pd

app = Flask(__name__)

HISTORY_URL = "https://raw.githubusercontent.com/a0981026530-maker/lotto_web/main/history.txt"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>詳細使用方法用Line加入19931026a</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family: Arial, sans-serif; padding: 10px; font-size: 18px; }
input, button { font-size: 18px; padding: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 18px; margin-top: 10px; }
th, td { border: 1px solid #333; padding: 8px; text-align: center; }
.table-container { overflow-x: auto; margin-bottom: 30px; }
.history-block { margin-bottom: 40px; }
h2 { margin-top: 20px; }
.highlight { font-weight: bold; color: red; font-size: 1.2em; }
</style>
</head>
<body>
<h1>詳細使用方法用Line加入19931026a</h1>
<form id="searchForm">
    <label>輸入前置數字：</label>
    <input type="text" id="pattern" required>
    <button type="submit">查詢</button>
</form>

<div id="compareTable"></div>
<div id="sumTop3"></div>
<div id="results"></div>

<script>
function renderHistory() {
    const history = JSON.parse(localStorage.getItem("searchHistory") || "[]");
    const container = document.getElementById("results");
    container.innerHTML = "";
    history.forEach(entry => {
        const block = document.createElement("div");
        block.className = "history-block";
        block.innerHTML = `
            <h2>Pattern: ${entry.pattern}</h2>
            <div class="table-container">
                <table>
                    <tr><th>數字</th><th>次數</th><th>機率</th></tr>
                    ${entry.results.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}
                </table>
            </div>
        `;
        container.appendChild(block);
    });
    renderCompareTable();
}

function renderCompareTable() {
    const history = JSON.parse(localStorage.getItem("searchHistory") || "[]");
    if (history.length < 2) {
        document.getElementById("compareTable").innerHTML = "";
        document.getElementById("sumTop3").innerHTML = "";
        return;
    }

    const first = history[0];
    const second = history[1];
    let rows = "";
    let sumCounts = {};

    for (let num = 1; num <= 6; num++) {
        const firstCount = first.results.find(r => r[0] === num)?.[1] || 0;
        const secondCount = second.results.find(r => r[0] === num)?.[1] || 0;
        rows += `<tr><td>${num}</td><td>${firstCount}</td><td>${secondCount}</td></tr>`;
        sumCounts[num] = firstCount + secondCount;
    }

    document.getElementById("compareTable").innerHTML = `
        <h2>最近兩次查詢對比</h2>
        <div class="table-container">
            <table>
                <tr><th>數字</th><th>${first.pattern} 次數</th><th>${second.pattern} 次數</th></tr>
                ${rows}
            </table>
        </div>
    `;

    // 加總後排序前三名
    const sorted = Object.entries(sumCounts).sort((a,b) => b[1] - a[1]).slice(0,3);
    const top3Text = sorted.map(item => `${item[0]} (${item[1]}次)`).join(", ");

    // 計算單雙大小
    let odd = 0, even = 0, small = 0, big = 0;
    for (const [numStr, cnt] of Object.entries(sumCounts)) {
        const num = parseInt(numStr);
        if ([1,3,5].includes(num)) odd += cnt;
        if ([2,4,6].includes(num)) even += cnt;
        if ([1,2,3].includes(num)) small += cnt;
        if ([4,5,6].includes(num)) big += cnt;
    }

    document.getElementById("sumTop3").innerHTML = `
        <h2>加總後的前三名</h2>
        <p class="highlight">${top3Text}</p>
        <h3>單雙大小統計</h3>
        <p>單: <span class="highlight">${odd}</span> 次，雙: <span class="highlight">${even}</span> 次</p>
        <p>小: <span class="highlight">${small}</span> 次，大: <span class="highlight">${big}</span> 次</p>
    `;
}

document.getElementById("searchForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const pattern = document.getElementById("pattern").value.trim();
    if (!pattern) return;

    if (pattern.length === 5) {
        localStorage.clear();
    }

    const res = await fetch(`/api/search?pattern=${pattern}`);
    const data = await res.json();
    if (data.success) {
        let history = JSON.parse(localStorage.getItem("searchHistory") || "[]");
        history.unshift({ pattern: pattern, results: data.results });
        localStorage.setItem("searchHistory", JSON.stringify(history));
        renderHistory();
    } else {
        alert("❌ 找不到該組合");
    }
});

renderHistory();
</script>
</body>
</html>
"""

def load_segments():
    r = requests.get(HISTORY_URL)
    r.raise_for_status()
    raw = r.text
    raw_segments = re.split(r"[【】#\n\r]+", raw)
    segments = []
    for seg in raw_segments:
        digits = [int(x) for x in seg if x in "123456"]
        if digits:
            segments.append(digits)
    return segments

def find_next_digit_counts(segments, pattern):
    if not re.fullmatch(r"[1-6]+", pattern):
        return None, 0
    pat = [int(c) for c in pattern]
    L = len(pat)
    counts = [0] * 6
    for seg in segments:
        for i in range(len(seg) - L):
            if seg[i:i+L] == pat:
                nxt = seg[i+L]
                counts[nxt-1] += 1
    return counts, sum(counts)

def calc_table(counts, total):
    rows = []
    for d in range(1, 7):
        cnt = counts[d-1]
        prob = f"{(cnt / total * 100):.2f}%" if total else "0.00%"
        rows.append([d, cnt, prob])
    df = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    return df.sort_values(by="次數", ascending=False).values.tolist()

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/search")
def api_search():
    pattern = request.args.get("pattern", "").strip()
    if not pattern:
        return jsonify({"success": False})
    segments = load_segments()
    counts, total = find_next_digit_counts(segments, pattern)
    if total > 0:
        results = calc_table(counts, total)
        return jsonify({"success": True, "results": results})
    else:
        return jsonify({"success": False})

if __name__ == "__main__":
    app.run(debug=True)