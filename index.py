from flask import Flask, request, session, redirect, url_for, jsonify
import re
import pandas as pd

app = Flask(__name__)
app.secret_key = "your_secret_key_123"  # 請自己換成隨機字串

# 多使用者帳號密碼管理
USERS = {
    "a0981026530": "Aa0981026530",
    "a0981026531": "Aa0978543515a",
    "a0981026532": "Aa0978543515ab"
}

# ======= 輔助函數 =======
TXT_PATH = "history.txt"

def load_segments(path):
    segments = []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    raw_segments = re.split(r"[【】#\n\r]+", raw)
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
                nxt = seg[i+L]
                counts[nxt-1] += 1
    return counts, sum(counts)

def make_table(title, counts, total):
    rows = []
    for d in range(1, 7):
        cnt = counts[d-1]
        prob = cnt / total if total else 0
        rows.append([d, cnt, f"{prob:.0%}"])
    df = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    df = df.sort_values(by="次數", ascending=False).reset_index(drop=True)
    return f"<h3>{title}</h3>" + df.to_html(index=False)

def count_bs_oe(counts):
    odd = counts[0] + counts[2] + counts[4]
    even = counts[1] + counts[3] + counts[5]
    small = counts[0] + counts[1] + counts[2]
    big = counts[3] + counts[4] + counts[5]
    return odd, even, small, big

# ======= 登入系統 =======
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return "<h3>帳號或密碼錯誤</h3><a href='/login'>再試一次</a>"
    return """
    <h2>請登入</h2>
    <form method="post">
        帳號: <input name="username"><br>
        密碼: <input type="password" name="password"><br>
        <button type="submit">登入</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======= 主頁 =======
@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return f"""
    <h1>數字分析工具</h1>
    <p>✅ 歡迎 {session['username']}</p>
    <form id="queryForm">
        <input type="text" id="pattern6" placeholder="輸入6碼">
        <input type="text" id="pattern5" placeholder="輸入5碼">
        <input type="text" id="pattern4" placeholder="輸入4碼">
        <button type="submit">查詢</button>
    </form>
    <div id="result"></div>
    <a href='/logout'>登出</a>
    <script>
    document.getElementById("queryForm").onsubmit = async function(e) {{
        e.preventDefault();
        let p6 = document.getElementById("pattern6").value;
        let p5 = document.getElementById("pattern5").value;
        let p4 = document.getElementById("pattern4").value;
        let res = await fetch("/analyze", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{p6, p5, p4}})
        }});
        let data = await res.json();
        document.getElementById("result").innerHTML = data.html;
    }}
    </script>
    """

# ======= 分析 API =======
@app.route("/analyze", methods=["POST"])
def analyze():
    if not session.get("logged_in"):
        return jsonify({"html": "<p>請先登入</p>"})

    data = request.json
    p6, p5, p4 = data.get("p6", ""), data.get("p5", ""), data.get("p4", "")
    segments = load_segments(TXT_PATH)

    html_parts, total_counts = [], [0]*6

    for title, pat in [("6碼結果", p6), ("5碼結果", p5), ("4碼結果", p4)]:
        if pat:
            counts, total = find_next_digit_counts(segments, pat)
            total_counts = [a+b for a,b in zip(total_counts, counts)]
            html_parts.append(make_table(title, counts, total))

    # 總結表 (放最上面)
    odd, even, small, big = count_bs_oe(total_counts)
    rows = []
    for d in range(1, 7):
        cnt = total_counts[d-1]
        prob = cnt / sum(total_counts) if sum(total_counts) else 0
        rows.append([d, cnt, f"{prob:.0%}"])
    df_total = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    df_total = df_total.sort_values(by="次數", ascending=False).reset_index(drop=True)

    summary_html = "<h2>總結</h2>" + df_total.to_html(index=False)
    summary_html += f"<p>單: {odd} 雙: {even} 大: {big} 小: {small}</p>"

    return jsonify({"html": summary_html + "".join(html_parts)})

if __name__ == "__main__":
    app.run(debug=True)