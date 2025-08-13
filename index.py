from flask import Flask, request, render_template_string
import requests
from collections import Counter

app = Flask(__name__)

# 你的 history.txt raw 連結
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
        <label>輸入 Pattern 數字：</label>
        <input type="number" name="pattern" required>
        <button type="submit">查詢</button>
    </form>

    {% if results %}
        <h2>數字分析結果 (pattern: {{ pattern }})</h2>
        <table border="1" cellpadding="5">
            <tr><th>數字</th><th>次數</th><th>機率</th></tr>
            {% for num, count, pct in results %}
                <tr>
                    <td>{{ num }}</td>
                    <td>{{ count }}</td>
                    <td>{{ pct }}%</td>
                </tr>
            {% endfor %}
        </table>
    {% endif %}
</body>
</html>
"""

def load_history():
    """從 GitHub 讀取 history.txt"""
    r = requests.get(HISTORY_URL)
    r.raise_for_status()
    return r.text.splitlines()

def analyze_numbers(data, pattern_length):
    """分析數字出現次數"""
    numbers = []
    for line in data:
        for i in range(len(line) - pattern_length + 1):
            numbers.append(line[i:i+pattern_length])

    counter = Counter(numbers)
    total = sum(counter.values())

    results = [(num, cnt, round(cnt / total * 100, 2)) for num, cnt in counter.most_common()]
    return results

@app.route("/", methods=["GET"])
def index():
    pattern = request.args.get("pattern", type=int)
    results = None

    if pattern:
        history_data = load_history()
        results = analyze_numbers(history_data, pattern)

    return render_template_string(HTML_TEMPLATE, results=results, pattern=pattern)

if __name__ == "__main__":
    app.run(debug=True)
