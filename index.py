from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import re
import math

app = Flask(__name__)
app.secret_key = "mysecretkey"  # 換成你自己的隨機字串，保護 Session

# ---------------- 帳號密碼設定 ----------------
USERS = {
    "a0981026530": "Aa0981026530",
    "user1": "pass1",
    "user2": "pass2"
}

DEVICE_LIMITS = {
    "a0981026530": 9999,
    "user1": 1,
    "user2": 1
}
DEVICE_BIND = {}

# ---------------- 讀取歷史資料 ----------------
def load_segments(path="history.txt"):
    segments = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raw = ""
    raw_segments = re.split(r"[【】#\n\r]+", raw)
    for seg in raw_segments:
        digits = [int(x) for x in seg if x in "123456"]
        if digits:
            segments.append(digits)
    return segments

segments = load_segments()

# ---------------- 基礎統計 ----------------
def find_next_digit_counts(segments, pattern):
    pat = [int(c) for c in pattern]
    L = len(pat)
    counts = [0] * 6
    for seg in segments:
        for i in range(len(seg) - L):
            if seg[i:i+L] == pat:
                counts[seg[i+L]-1] += 1
    return counts, sum(counts)

# =================【新增功能開始】=================

# ③ 模式可信度分數（不影響原邏輯）
def pattern_confidence(counts):
    total = sum(counts)
    if total == 0:
        return 0
    expected = total / 6
    z_max = 0
    for c in counts:
        z = (c - expected) / math.sqrt(expected) if expected > 0 else 0
        z_max = max(z_max, abs(z))
    return min(100, max(0, round(z_max * 25)))

# 回測驗證命中率
def backtest_hit_rate(segments, pattern, window=200):
    hits = 0
    total = 0
    pat = [int(c) for c in pattern]
    L = len(pat)

    for i in range(window, len(segments)-1):
        hist = segments[:i]
        counts, _ = find_next_digit_counts(hist, pattern)
        if sum(counts) == 0:
            continue

        arr = list(enumerate(counts, start=1))
        arr.sort(key=lambda x: x[1], reverse=True)
        top3 = [n for n,_ in arr[:3]]

        actual_next = segments[i][0]
        total += 1
        if actual_next in top3:
            hits += 1

    return round(hits / total * 100) if total else 0

# =================【新增功能結束】=================

# ====== 登入頁面 ======
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            return render_template_string("""
            <h2>登入失敗，請加line:19931026a，購買</h2>
            <a href="/login">再試一次</a>
            """)
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>登入</title>
        <style>
            body { font-family: Arial; padding: 20px; font-size: 20px; }
            input, button { padding: 10px; font-size: 20px; margin: 5px 0; }
        </style>
    </head>
    <body>
        <h2>參考數據下注，單月只要999</h2>
        <form method="POST">
            <input name="username" placeholder="帳號"><br>
            <input name="password" placeholder="密碼" type="password"><br>
            <button type="submit">登入</button>
        </form>
    </body>
    </html>
    """)

# ====== 主頁 ======
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>分析系統</title>
<style>
body { font-family: Arial; font-size: 20px; padding: 10px; }
input, button { padding: 10px; font-size: 20px; margin: 5px 0; }
table { border-collapse: collapse; }
th, td { border: 2px solid #333; padding: 6px; text-align: center; }
.highlight { font-weight: bold; color: blue; }
</style>
</head>
<body>

<h2>分析系統</h2>
<p>使用者：{{user}}</p>
<a href="/logout">登出</a><br><br>

<input id="pattern" placeholder="輸入 4~6 碼">
<button onclick="analyze()">查詢</button>

<div id="summary"></div>
<div id="tables"></div>

<script>
let records = [];

async function analyze(){
  const raw = document.getElementById("pattern").value.trim();
  if(!/^[1-6]+$/.test(raw)){
    alert("只能輸入 1-6");
    return;
  }

  let patterns = raw.length==6?[raw,raw.slice(1),raw.slice(2)]:
                 raw.length==5?[raw,raw.slice(1)]:[raw];

  if(records.length + patterns.length > 3){
    records = [];
    document.getElementById("tables").innerHTML = "";
  }

  for(const p of patterns){
    const r = await fetch("/analyze",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({pattern:p})
    });
    const d = await r.json();
    records.push(d);

    document.getElementById("tables").innerHTML += `
      <h3>${p} 查詢結果</h3>
      <p>模式可信度：<b>${d.confidence}</b>　回測命中率：<b>${d.backtest}</b></p>
      <table>
      <tr><th>數字</th><th>次數</th><th>機率</th></tr>
      ${d.rows.map(r=>`<tr><td>${r.num}</td><td>${r.cnt}</td><td>${r.prob}</td></tr>`).join("")}
      </table>
    `;
  }
}
</script>
</body>
</html>
""", user=session["user"])

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    pattern = data.get("pattern","")
    counts, total = find_next_digit_counts(segments, pattern)

    rows = []
    for i,c in enumerate(counts):
        prob = f"{(c/total*100):.0f}%" if total else "0%"
        rows.append({"num":i+1, "cnt":c, "prob":prob})

    return jsonify({
        "counts": counts,
        "rows": rows,
        "confidence": pattern_confidence(counts),
        "backtest": f"{backtest_hit_rate(segments, pattern)}%"
    })

if __name__ == "__main__":
    app.run(debug=True)