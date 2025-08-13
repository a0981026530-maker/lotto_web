from flask import Flask, request, render_template_string
import requests
import re
import pandas as pd

app = Flask(__name__)

# 你的 GitHub raw 檔案網址（固定讀最新 history.txt）
HISTORY_URL = "https://raw.githubusercontent.com/a0981026530-maker/lotto_web/main/history.txt"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>數字分析工具</title>
</head>
<body>
    <h1>數字分析工具</h1>
    <form method="get">
        <label>輸入前置數字 (例如 5碼後、4碼後)：</label>
        <input type="text" name="pattern" required>
        <button type="submit">查詢</button>
    </form>

    {% if results %}
        <h2>數字分析結果 (pattern: {{ pattern }})</h2>
        <table border="1" cellpadding="5">
            <tr><th>數字</th><th>次數</th><th>機率</th></tr>
            {% for num, cnt, pct in results %}
                <tr>
                    <td>{{ num }}</td>
                    <td>{{ cnt }}</td>
                    <td>{{ pct }}</td>
                </tr>
            {% endfor %}
        </table>
    {% elif pattern %}
        <p style="color:red;">❌ 找不到該組合</p>
    {% endif %}
</body>
</html>
"""

def load_segments():
    """從 GitHub 讀取並分段處理數據"""
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
    """統計 pattern 後出現的數字"""
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
    """回傳排序好的表格資料"""
    rows = []
    for d in range(1, 7):
        cnt = counts[d-1]
        prob = f"{(cnt / total * 100):.2f}%" if total else "0.00%"
        rows.append((d, cnt, prob))
    df = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    return df.sort_values(by="次數", ascending=False).values.tolist()

@app.route("/", methods=["GET"])
def index():
    pattern = request.args.get("pattern", "").strip()
    results = None
    if pattern:
        segments = load_segments()
        counts, total = find_next_digit_counts(segments, pattern)
        if total > 0:
            results = calc_table(counts, total)
    return render_template_string(HTML_TEMPLATE, results=results, pattern=pattern)

if __name__ == "__main__":
    app.run(debug=True)