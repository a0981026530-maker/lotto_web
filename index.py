from flask import Flask, request, render_template_string
import pandas as pd
import re
import os

app = Flask(__name__)

# 讀取本地 history.txt（放在同資料夾）
TXT_PATH = os.path.join(os.path.dirname(__file__), "history.txt")

def load_segments_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    segments = []
    raw_segments = re.split(r"[【】#\n\r]+", raw)
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
        prob = cnt / total if total else 0
        rows.append([d, cnt, f"{prob:.0%}"])
    df = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    return df.sort_values(by="次數", ascending=False).reset_index(drop=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>數字分析工具</title>
</head>
<body>
    <h1>數字分析工具（雲端版）</h1>
    <form method="post">
        <p>輸入前置數字（1-6）：<input type="text" name="pattern" required></p>
        <p><input type="submit" value="分析"></p>
    </form>
    {% if result %}
        <h2>分析結果（依次數排序）</h2>
        <table border="1" cellpadding="5">
            <tr><th>數字</th><th>次數</th><th>機率</th></tr>
            {% for row in result %}
                <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td></tr>
            {% endfor %}
        </table>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        pattern = request.form.get("pattern", "").strip()
        segments = load_segments_from_file(TXT_PATH)
        counts, total = find_next_digit_counts(segments, pattern)
        if total > 0:
            df = calc_table(counts, total)
            result = df.values.tolist()
    return render_template_string(HTML_TEMPLATE, result=result)

# Vercel 會用 handler 來啟動
def handler(event, context):
    return app(event, context)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
