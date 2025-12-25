from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import re, math

app = Flask(__name__)
app.secret_key = "mysecretkey"

# ---------------- 帳號密碼 ----------------
USERS = {
    "a0981026530": "Aa0981026530",
    "user1": "pass1",
    "user2": "pass2"
}

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
    counts = [0]*6
    for seg in segments:
        for i in range(len(seg)-L):
            if seg[i:i+L] == pat:
                counts[seg[i+L]-1] += 1
    return counts, sum(counts)

# ---------------- ③ 模式可信度 ----------------
def pattern_confidence(counts):
    total = sum(counts)
    if total == 0:
        return 0
    expected = total / 6
    z_max = 0
    for c in counts:
        z = (c - expected) / math.sqrt(expected) if expected > 0 else 0
        z_max = max(z_max, abs(z))
    confidence = min(100, max(0, round(z_max * 25)))
    return confidence

# ---------------- 回測驗證 ----------------
def backtest(segments, pattern, window=200):
    hits = 0
    total = 0
    pat = [int(c) for c in pattern]
    L = len(pat)

    for i in range(window, len(segments)-1):
        hist = segments[:i]
        counts,_ = find_next_digit_counts(hist, pattern)
        if sum(counts) == 0:
            continue

        arr = list(enumerate(counts, start=1))
        arr.sort(key=lambda x:x[1], reverse=True)
        top3 = [n for n,_ in arr[:3]]

        actual = segments[i][0]
        total += 1
        if actual in top3:
            hits += 1

    return round(hits / total * 100) if total else 0

# ---------------- 登入 ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        if u in USERS and USERS[u] == p:
            session["user"] = u
            return redirect(url_for("index"))
        return "<h2>登入失敗，請加 line:19931026a</h2>"
    return render_template_string("""
    <h2>登入</h2>
    <form method="post">
      <input name="username" placeholder="帳號"><br>
      <input name="password" type="password" placeholder="密碼"><br>
      <button>登入</button>
    </form>
    """)

# ---------------- 主頁 ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template_string("""
<!DOCTYPE html>
<html>
<meta charset="utf-8">
<body style="font-size:20px">
<h2>分析工具（強化版）</h2>
<input id="pattern" placeholder="輸入 4~6 碼">
<button onclick="go()">查詢</button>

<div id="out"></div>
<div id="intersection"></div>

<script>
let records = [];

async function go(){
  const raw = document.getElementById("pattern").value.trim();
  if(!/^[1-6]{4,6}$/.test(raw)){ alert("只能輸入 1~6"); return; }

  let pats = raw.length==6?[raw,raw.slice(1),raw.slice(2)]:
             raw.length==5?[raw,raw.slice(1)]:[raw];

  if(records.length + pats.length > 3){ records=[]; }

  for(let p of pats){
    const r = await fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({pattern:p})});
    const d = await r.json();
    records.push(d);
  }

  render();
}

function render(){
  let html="";
  records.forEach(r=>{
    html+=`<h3>${r.pattern}</h3>
    信賴度：<b>${r.confidence}</b>　
    回測命中率：<b>${r.backtest}%</b>
    <table border=1>
    <tr><th>數字</th><th>次數</th></tr>
    ${r.counts.map((c,i)=>`<tr><td>${i+1}</td><td>${c}</td></tr>`).join("")}
    </table>`;
  });
  document.getElementById("out").innerHTML = html;

  let score = [0,0,0,0,0,0];
  records.forEach(r=>{
    let arr = r.counts.map((c,i)=>({n:i+1,c}));
    arr.sort((a,b)=>b.c-a.c);
    arr.slice(0,3).forEach(o=>score[o.n-1]++);
  });

  document.getElementById("intersection").innerHTML =
    "<h3>交集分析</h3>"+score.map((s,i)=>`<p>${i+1}：${s} 次</p>`).join("");
}
</script>
</body>
</html>
""")

# ---------------- 分析 API ----------------
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    pattern = data.get("pattern","")
    counts,_ = find_next_digit_counts(segments, pattern)
    return jsonify({
        "pattern": pattern,
        "counts": counts,
        "confidence": pattern_confidence(counts),
        "backtest": backtest(segments, pattern)
    })

@app.route("/logout")
def logout():
    session.pop("user",None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)