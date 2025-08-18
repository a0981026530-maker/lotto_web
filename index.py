from flask import Flask, request, jsonify, render_template_string
import re

app = Flask(__name__)

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
    counts = [0]*6
    for seg in segments:
        for i in range(len(seg)-L):
            if seg[i:i+L] == pat:
                nxt = seg[i+L]
                counts[nxt-1]+=1
    return counts, sum(counts)

# ===== HTML 模板 =====
HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>數字分析工具</title>
  <style>
    body { font-family: Arial; padding: 15px; font-size: 18px; }
    input, button { font-size: 20px; padding: 8px; margin: 5px 0; }
    table { border-collapse: collapse; margin: 10px 0; width: 100%%; font-size: 18px; }
    th, td { border: 1px solid #333; padding: 6px; text-align: center; }
    .highlight { font-weight: bold; font-size: 20px; color: blue; }
    .diff-box { border:2px solid red; padding:8px; margin:6px 0; font-weight:bold; font-size:18px; }
  </style>
</head>
<body>
  <h1>數字分析工具</h1>
  <input id="pattern" placeholder="輸入 4/5/6 碼">
  <button onclick="analyze()">查詢</button>
  <div id="summary"></div>
  <div id="compare"></div>
  <div id="result"></div>

<script>
let records = [];

async function analyze(){
  const pattern = document.getElementById("pattern").value.trim();
  if(!/^[1-6]+$/.test(pattern)){
    alert("只能輸入 1-6 的數字");
    return;
  }
  const res = await fetch("/analyze",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pattern})
  });
  const data = await res.json();

  // 單次結果 (只有臨時顯示)
  document.getElementById("result").innerHTML = `
    <h2>${pattern} 查詢結果</h2>
    <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
    ${data.rows.map(r=>`<tr><td>${r.num}</td><td>${r.cnt}</td><td>${r.prob}</td></tr>`).join("")}
    </table>
  `;

  // 累積
  records.push(data);

  // 三次後 → 顯示加總並清掉單次結果
  if(records.length === 3){
    renderCompareTable();
    document.getElementById("result").innerHTML = ""; // 清除單次結果
    records = []; // 重置
  }
}

function renderCompareTable(){
  let sumCounts = [0,0,0,0,0,0];
  records.forEach(r=>{
    r.counts.forEach((c,i)=>sumCounts[i]+=c);
  });
  let total = sumCounts.reduce((a,b)=>a+b,0);
  let arr = sumCounts.map((c,i)=>({num:i+1, cnt:c, prob: total? (c/total):0}));
  arr.sort((a,b)=>b.cnt-a.cnt);

  const top3 = arr.slice(0,3);
  let top3Text = top3.map(o=>`${o.num} (${o.cnt}次)`).join(", ");

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

  // 加總結果放最上面
  document.getElementById("summary").innerHTML = `
    <h2>加總結果摘要</h2>
    <p class="highlight">前三名：${top3Text}</p>
    <div class="diff-box">單 ${odd}，雙 ${even} → ${diffOddEven}</div>
    <div class="diff-box">大 ${big}，小 ${small} → ${diffBigSmall}</div>
  `;

  // 對比表放下面
  document.getElementById("compare").innerHTML = `
    <h2>三組對比結果 (6碼+5碼+4碼)</h2>
    <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
    ${arr.map(o=>`<tr><td>${o.num}</td><td>${o.cnt}</td><td>${(o.prob*100).toFixed(0)}%</td></tr>`).join("")}
    </table>
  `;
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/analyze", methods=["POST"])
def analyze_api():
    pattern = request.json.get("pattern","")
    if not re.fullmatch(r"[1-6]+", pattern):
        return jsonify({"error":"pattern invalid"})
    counts, total = find_next_digit_counts(segments, pattern)
    rows=[]
    for i,c in enumerate(counts,1):
        prob = f"{(c/total*100):.0f}%%" if total else "0%%"
        rows.append({"num":i,"cnt":c,"prob":prob})
    return jsonify({"rows":rows,"counts":counts})
    
if __name__ == "__main__":
    app.run(debug=True)