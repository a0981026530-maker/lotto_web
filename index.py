from flask import Flask, render_template_string
import pandas as pd
import re

app = Flask(__name__)

# 固定讀取本地 history.txt（部署時會一起放進去）
TXT_PATH = "history.txt"

def load_segments(path):
    """讀取檔案並切成多段，忽略非 1–6 的符號"""
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
    """在多段數據中，統計 pattern 後出現的數字"""
    if not re.fullmatch(r"[1-6]+", pattern):
        return [0]*6, 0
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

@app.route('/')
def index():
    pattern = "1"  # 預設範例
    segments = load_segments(TXT_PATH)
    counts, total = find_next_digit_counts(segments, pattern)
    df = calc_table(counts, total)
    html_table = df.to_html(index=False)
    return render_template_string("""
        <h1>數字分析結果 (pattern: {{pattern}})</h1>
        {{table | safe}}
    """, table=html_table, pattern=pattern)

if __name__ == '__main__':
    app.run()
