from flask import Flask, request, jsonify
import re
import pandas as pd

app = Flask(__name__)

TXT_PATH = "history.txt"

def load_segments():
    segments = []
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    raw_segments = re.split(r"[【】#\n\r]+", raw)
    for seg in raw_segments:
        digits = [int(x) for x in seg if x in "123456"]
        if digits:
            segments.append(digits)
    return segments

def find_next_digit_counts(segments, pattern):
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
        prob = cnt / total if total else 0
        rows.append({"數字": d, "次數": cnt, "機率": f"{prob:.0%}"})
    df = pd.DataFrame(rows).sort_values(by="次數", ascending=False).reset_index(drop=True)
    return df.to_dict(orient="records")

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>數字分析工具</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin-top: 10px; }
            th, td { border: 1px solid #ccc; padding: 5px; text-align: center; }
            .top1 { background-color: #ff9999; font-weight: bold; }
            .top2 { background-color: #99ff99; font-weight: bold; }
            .top3 { background-color: #9999ff; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>數字分析工具</h1>
        <input id="pattern" placeholder="輸入前置數字">
        <button onclick="search()">查詢</button>
        <div id="results"></div>
        <div id="commonNumbers"></div>
        <div id="sumTop3"></div>
        <div id="sumOddEvenBigSmall"></div>

        <script>
            let historyData = [];

            function search() {
                const pattern = document.getElementById("pattern").value.trim();
                if (!/^[1-6]+$/.test(pattern)) {
                    alert("只能輸入 1-6 數字");
                    return;
                }
                if (pattern.length === 5) {
                    historyData = [];
                    document.getElementById("commonNumbers").innerHTML = "";
                    document.getElementById("sumTop3").innerHTML = "";
                    document.getElementById("sumOddEvenBigSmall").innerHTML = "";
                }

                fetch("/search", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({pattern})
                })
                .then(r => r.json())
                .then(data => {
                    historyData.push({pattern: pattern, table: data});
                    renderResults();
                    if (historyData.length === 2) {
                        renderCommonNumbers();
                        renderSumTop3();
                        renderSumOddEvenBigSmall();
                    }
                });
            }

            function renderResults() {
                let html = "";
                historyData.forEach((item, idx) => {
                    html += `<h3>${idx+1}：${item.pattern}</h3>`;
                    html += "<table><tr><th>數字</th><th>次數</th><th>機率</th></tr>";
                    item.table.forEach((row, rIdx) => {
                        let cls = rIdx===0 ? "top1" : rIdx===1 ? "top2" : rIdx===2 ? "top3" : "";
                        html += `<tr class="${cls}"><td>${row["數字"]}</td><td>${row["次數"]}</td><td>${row["機率"]}</td></tr>`;
                    });
                    html += "</table>";
                });
                document.getElementById("results").innerHTML = html;
            }

            function renderCommonNumbers() {
                const first = historyData[0].table;
                const second = historyData[1].table;
                let common = [];

                first.forEach(f => {
                    const match = second.find(s => s["數字"] === f["數字"]);
                    if (match) {
                        common.push({
                            "數字": f["數字"],
                            "5碼次數": f["次數"],
                            "4碼次數": match["次數"]
                        });
                    }
                });

                if (common.length > 0) {
                    let html = "<h3>共同數字表</h3><table><tr><th>數字</th><th>5碼次數</th><th>4碼次數</th></tr>";
                    common.forEach(c => {
                        html += `<tr><td>${c["數字"]}</td><td>${c["5碼次數"]}</td><td>${c["4碼次數"]}</td></tr>`;
                    });
                    html += "</table>";
                    document.getElementById("commonNumbers").innerHTML = html;
                }
            }

            function renderSumTop3() {
                const sumMap = {};
                historyData.forEach(h => {
                    h.table.forEach(r => {
                        if (!sumMap[r["數字"]]) sumMap[r["數字"]] = 0;
                        sumMap[r["數字"]] += r["次數"];
                    });
                });

                const sumArr = Object.entries(sumMap).map(([num, cnt]) => ({
                    "數字": parseInt(num),
                    "總次數": cnt
                }));

                sumArr.sort((a,b) => b["總次數"] - a["總次數"]);

                let html = "<h3>加總前三名</h3><table><tr><th>數字</th><th>總次數</th></tr>";
                sumArr.forEach((row, idx) => {
                    let cls = idx===0 ? "top1" : idx===1 ? "top2" : idx===2 ? "top3" : "";
                    html += `<tr class="${cls}"><td>${row["數字"]}</td><td>${row["總次數"]}</td></tr>`;
                });
                html += "</table>";
                document.getElementById("sumTop3").innerHTML = html;
            }

            function renderSumOddEvenBigSmall() {
                const sumMap = {};
                historyData.forEach(h => {
                    h.table.forEach(r => {
                        if (!sumMap[r["數字"]]) sumMap[r["數字"]] = 0;
                        sumMap[r["數字"]] += r["次數"];
                    });
                });

                let odd = 0, even = 0, small = 0, big = 0;
                Object.entries(sumMap).forEach(([num, cnt]) => {
                    num = parseInt(num);
                    if ([1,3,5].includes(num)) odd += cnt;
                    if ([2,4,6].includes(num)) even += cnt;
                    if ([1,2,3].includes(num)) small += cnt;
                    if ([4,5,6].includes(num)) big += cnt;
                });

                let html = "<h3>加總單雙大小</h3><table><tr><th>類型</th><th>總次數</th></tr>";
                html += `<tr><td>單</td><td>${odd}</td></tr>`;
                html += `<tr><td>雙</td><td>${even}</td></tr>`;
                html += `<tr><td>小</td><td>${small}</td></tr>`;
                html += `<tr><td>大</td><td>${big}</td></tr>`;
                html += "</table>";

                document.getElementById("sumOddEvenBigSmall").innerHTML = html;
            }
        </script>
    </body>
    </html>
    """

@app.route("/search", methods=["POST"])
def search():
    pattern = request.json.get("pattern", "").strip()
    if not re.fullmatch(r"[1-6]+", pattern):
        return jsonify([])
    segments = load_segments()
    counts, total = find_next_digit_counts(segments, pattern)
    table = calc_table(counts, total)
    return jsonify(table)

if __name__ == "__main__":
    app.run(debug=True)