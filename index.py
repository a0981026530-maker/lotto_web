from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------------- 帳號密碼設定 ----------------
USERS = {
    "a0981026530": "Aa0981026530",
    "user1": "pass1",
    "user2": "pass2"
}

# 每個帳號允許綁定的裝置數量
DEVICE_LIMITS = {
    "a0981026530": 9999,  # 不限裝置
    "user1": 1,
    "user2": 1
}

# 裝置綁定紀錄 { "username": set([...user_agents...]) }
DEVICE_BIND = {}

# ---------------- 輔助函數 ----------------
def load_segments():
    with open("history.txt", "r", encoding="utf-8") as f:
        raw = f.read()
    raw_segments = re.split(r"[【】#\n\r]+", raw)
    segments = []
    for seg in raw_segments:
        digits = [int(x) for x in seg if x in "123456"]
        if digits:
            segments.append(digits)
    return segments

def find_next_digit_counts(segments, pattern):
    if not re.fullmatch(r"[1-6]+", pattern):
        return [0]*6, 0
    pat = [int(c) for c in pattern]
    L = len(pat)
    counts = [0]*6
    for seg in segments:
        for i in range(len(seg)-L):
            if seg[i:i+L] == pat:
                counts[seg[i+L]-1] += 1
    return counts, sum(counts)

# ---------------- 登入驗證 ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_agent = request.headers.get("User-Agent", "unknown")

        if username in USERS and USERS[username] == password:
            # 如果不限裝置，直接登入
            if DEVICE_LIMITS.get(username, 1) >= 9999:
                session["username"] = username
                return redirect(url_for("index"))

            # 檢查裝置綁定數量
            if username not in DEVICE_BIND:
                DEVICE_BIND[username] = {user_agent}
            else:
                if user_agent not in DEVICE_BIND[username]:
                    if len(DEVICE_BIND[username]) >= DEVICE_LIMITS.get(username, 1):
                        return "登入失敗：此帳號已綁定裝置，不能再登入"
                    DEVICE_BIND[username].add(user_agent)

            session["username"] = username
            return redirect(url_for("index"))
        else:
            return "帳號或密碼錯誤"

    return '''
        <form method="post">
            <h2>如需購買請加line:19931026a，一個月只要500元</h2>
            帳號: <input type="text" name="username"><br>
            密碼: <input type="password" name="password"><br>
            <input type="submit" value="登入">
        </form>
    '''

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# ---------------- 主頁 ----------------
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template_string(PAGE_HTML)

# ---------------- 查詢 API ----------------
@app.route("/api/search", methods=["POST"])
def search():
    if "username" not in session:
        return jsonify({"error": "未登入"})

    data = request.get_json()
    patterns = data.get("patterns", [])

    segments = load_segments()

    results = {}
    combined_counts = [0]*6
    combined_total = 0

    for p in patterns:
        counts, total = find_next_digit_counts(segments, p)
        results[p] = {"counts": counts, "total": total}
        combined_counts = [c1+c2 for c1, c2 in zip(combined_counts, counts)]
        combined_total += total

    # 加總後的前三名
    top3 = sorted(
        [(i+1, c) for i, c in enumerate(combined_counts)],
        key=lambda x: x[1], reverse=True
    )[:3]

    # 單雙大小
    odd_cnt = combined_counts[0] + combined_counts[2] + combined_counts[4]
    even_cnt = combined_counts[1] + combined_counts[3] + combined_counts[5]
    small_cnt = combined_counts[0] + combined_counts[1] + combined_counts[2]
    big_cnt = combined_counts[3] + combined_counts[4] + combined_counts[5]

    summary = {
        "top3": top3,
        "odd": odd_cnt, "even": even_cnt,
        "small": small_cnt, "big": big_cnt
    }

    return jsonify({"results": results, "summary": summary})

# ---------------- HTML ----------------
PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>數字分析工具</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; font-size: 22px; }
        h2 { margin-top: 0; }
        .results { margin-top: 20px; }
        .summary { border: 2px solid black; padding: 10px; margin-bottom: 20px; }
        .highlight { font-weight: bold; color: red; font-size: 26px; }
    </style>
</head>
<body>
    <h2>數字分析工具</h2>
    <form id="searchForm">
        輸入6碼: <input type="text" id="pattern6"><br><br>
        輸入5碼: <input type="text" id="pattern5"><br><br>
        輸入4碼: <input type="text" id="pattern4"><br><br>
        <button type="submit">查詢</button>
    </form>

    <div id="summary" class="summary"></div>
    <div class="results" id="results"></div>

    <p><a href="/logout">登出</a></p>

    <script>
        document.getElementById("searchForm").addEventListener("submit", async function(e) {
            e.preventDefault();
            let p6 = document.getElementById("pattern6").value.trim();
            let p5 = document.getElementById("pattern5").value.trim();
            let p4 = document.getElementById("pattern4").value.trim();

            let patterns = [];
            if (p6) patterns.push(p6);
            if (p5) patterns.push(p5);
            if (p4) patterns.push(p4);

            if (patterns.length === 0) {
                alert("請至少輸入一組數字");
                return;
            }

            let res = await fetch("/api/search", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({patterns: patterns})
            });
            let data = await res.json();

            let summaryDiv = document.getElementById("summary");
            let html = "<h3>加總結果</h3>";
            html += "<p>前三名: " + data.summary.top3.map(x => `<span class='highlight'>${x[0]} (${x[1]})</span>`).join(" , ") + "</p>";
            html += `<p>單: <span class='highlight'>${data.summary.odd}</span> , 雙: <span class='highlight'>${data.summary.even}</span></p>`;
            html += `<p>大: <span class='highlight'>${data.summary.big}</span> , 小: <span class='highlight'>${data.summary.small}</span></p>`;
            summaryDiv.innerHTML = html;

            // 顯示各組查詢結果
            let resultsDiv = document.getElementById("results");
            resultsDiv.innerHTML = "";
            for (let p in data.results) {
                let r = data.results[p];
                let row = `<div><b>${p}</b> → 次數: ${r.counts.join(", ")} (總計: ${r.total})</div>`;
                resultsDiv.innerHTML += row;
            }

            // 查詢完後清除輸入框
            document.getElementById("pattern6").value = "";
            document.getElementById("pattern5").value = "";
            document.getElementById("pattern4").value = "";
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)