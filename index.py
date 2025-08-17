from flask import Flask, render_template_string, request, jsonify
import re

app = Flask(__name__)

# 讀取數據
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

segments = load_segments(TXT_PATH)

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

# HTML 模板
TEMPLATE = """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>數字分析工具</title>
<style>
  body { font-family: Arial, sans-serif; margin:20px; font-size:20px; }
  input { font-size:20px; padding:5px; }
  button { font-size:20px; padding:5px 10px; }
  table { border-collapse: collapse; margin-top:15px; width:100%; font-size:20px; }
  th, td { border:1px solid #333; padding:6px; text-align:center; }
  .highlight { font-weight:bold; font-size:24px; color:blue; }
  .diff-box { border:2px solid red; padding:8px; margin:5px 0; font-weight:bold; font-size:22px; }
</style>
</head>
<body>
  <h1>數字分析工具</h1>
  <p>請輸入 6碼 → 5碼 → 4碼，完成後會自動顯示結果。</p>
  <input id="patternInput" placeholder="輸入號碼">
  <button onclick="analyze()">查詢</button>
  
  <div id="summary"></div>
  <div id="compare"></div>

<script>
let records = [];

function analyze(){
  const pattern = document.getElementById("patternInput").value.trim();
  if(!pattern) return;

  fetch("/analyze", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pattern:pattern})
  })
  .then(r=>r.json())
  .then(data=>{
    records.push(data);
    if(records.length===3){
      renderCompareTable();
    }
  });
  document.getElementById("patternInput").value="";
}

function renderCompareTable(){
  let sumCounts = [0,0,0,0,0,0];
  records.forEach(r=>{
    r.counts.forEach((c,i)=>sumCounts[i]+=c);
  });
  let total = sumCounts.reduce((a,b)=>a+b,0);
  let arr = sumCounts.map((c,i)=>({num:i+1, cnt:c, prob: total? (c/total):0}));
  arr.sort((a,b)=>b.cnt-a.cnt);

  // 前三名
  const top3 = arr.slice(0,3);
  let top3Text = top3.map(o=>`${o.num} (${o.cnt}次)`).join(", ");

  // 單雙大小
  let odd=0,even=0,small=0,big=0;
  sumCounts.forEach((c,i)=>{
    const num=i+1;
    if ([1,3,5].includes(num)) odd+=c;
    if ([2,4,6].includes(num)) even+=c;
    if ([1,2,3].includes(num)) small+=c;
    if ([4,5,6].includes(num)) big+=c;
  });
  const diffOddEven = odd>even?`單比雙多 ${odd-even} 次`:even>odd?`雙比單多 ${even-odd} 次`:"單雙一樣多";
  const diffBigSmall = big>small?`大比小多 ${big-small} 次`:small>big?`小比大多 ${small-big} 次`:"大小一樣多";

  // 摘要放最上面
  document.getElementById("summary").innerHTML = `
    <h2>加總結果摘要</h2>
    <p class="highlight">前三名：${top3Text}</p>
    <div class="diff-box">單 ${odd}，雙 ${even} → ${diffOddEven}</div>
    <div class="diff-box">大 ${big}，小 ${small} → ${diffBigSmall}</div>
  `;

  // 對比表（覆蓋，不累積）
  document.getElementById("compare").innerHTML = `
    <h2>三組對比結果 (6碼+5碼+4碼)</h2>
    <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
    ${arr.map(o=>`<tr><td>${o.num}</td><td>${o.cnt}</td><td>${(o.prob*100).toFixed(0)}%</td></tr>`).join("")}
    </table>
  `;

  // ⭐ 自動清空，準備下一輪
  records = [];
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(TEMPLATE)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    pattern = data.get("pattern","")
    counts, total = find_next_digit_counts(segments, pattern)
    return jsonify({"pattern":pattern,"counts":counts,"total":total})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)