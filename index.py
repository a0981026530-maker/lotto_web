from flask import Flask, render_template, request, session, redirect, url_for
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = "supersecret"

# 帳號密碼 (可以多組)
USERS = {
    "a0981026530": "123456",
    "user1": "111111",
    "user2": "222222",
}

# 裝置綁定 (每帳號最多1裝置，a0981026530不限)
DEVICE_BINDINGS = {}

# 載入數據
def load_segments(path="history.txt"):
    segments = []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    raw_segments = re.split(r"[【】#\n\r]+", raw)
    for seg in raw_segments:
        digits = [int(x) for x in seg if x in "123456"]
        if digits:
            segments.append(digits)
    return segments

history_segments = load_segments()

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
        rows.append([d, cnt, f"{prob:.0%}"])
    df = pd.DataFrame(rows, columns=["數字", "次數", "機率"])
    return df.sort_values(by="次數", ascending=False).reset_index(drop=True)

def analyze(pattern):
    results = {}
    for L in [len(pattern), len(pattern)-1, len(pattern)-2]:
        if L >= 3:
            sub_pat = pattern[-L:]
            counts, total = find_next_digit_counts(history_segments, sub_pat)
            df = calc_table(counts, total)
            results[f"{L}碼"] = df
    # 加總
    combined = sum([results[k]["次數"] for k in results], axis=0)
    combined_rows = []
    for d in range(1,7):
        cnt = combined[d-1]
        combined_rows.append([d, cnt])
    df_sum = pd.DataFrame(combined_rows, columns=["數字", "總次數"]).sort_values(by="總次數", ascending=False)
    return results, df_sum

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in USERS and USERS[username] == password:
            if username != "a0981026530":
                if username in DEVICE_BINDINGS and DEVICE_BINDINGS[username] != request.remote_addr:
                    return "此帳號已綁定其他裝置，無法登入"
                DEVICE_BINDINGS[username] = request.remote_addr
            session["user"] = username
            return redirect(url_for("index"))
        else:
            return "帳號或密碼錯誤"
    return render_template("login.html")

@app.route("/index", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    result_tables, sum_table = None, None
    if request.method == "POST":
        pattern = request.form["pattern"].strip()
        if re.fullmatch(r"[1-6]{5}", pattern):
            result_tables, sum_table = analyze(pattern)
    return render_template("index.html", result_tables=result_tables, sum_table=sum_table)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
