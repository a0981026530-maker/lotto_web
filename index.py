from flask import Flask, request, jsonify, render_template_string
import re

app = Flask(__name__)

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

segments = load_segments()

def find_next_digit_counts(segments, pattern):
    pat = [int(c) for c in pattern]
    L = len(pat)
    counts = [0] * 6
    for seg in segments:
        for i in range(len(seg) - L):
            if seg[i:i+L] == pat:
                counts[seg[i+L]-1] += 1
    return counts, sum(counts)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>數字分析工具</title>
<style>
body { font-family: Arial, sans-serif; padding: 10px; font-size: 20px; }
input, button { padding: 10px; font-size: 20px; margin: 5px 0; }
h1 { font-size: 28px; }
h2 { font-size: 24px; margin-top: 20px; }
h3 { font-size: 22px; margin: 10px 0; }
table { border-collapse: collapse; margin: 10px 0; width: 100%; max-width: 300px; font-size: 18px; }
th, td { border: 2px solid #333; padding: 8px; text-align: center; }
.highlight { font-weight: bold; font-size: 22px; color: blue; }
.diff-box { border: 3px solid red; padding: 8px; margin: 10px 0; font-weight: bold; font-size: 20px; }
#tables { display: flex; gap: 15px; flex-wrap: wrap; }
#tables > div { flex: 1; min-width: 250px; }
</style>
</head>
<body>
<h1>數字分析工具</h1>
<input id="pattern" placeholder="輸入數字，例如123456">
<button onclick="analyze()">查詢</button>

<div id="summary"></div>
<div id="compare"></div>
<div id="tables"></div>

<script>
let records = [];
let roundTables = [];

async function analyze(){
  const pattern = document.getElementById("pattern").value.trim();
  if(!/^[1-6]+$/.test(pattern)){
    alert("只能輸入 1-6 的數字");
    return;
  }

  if(records.length === 3){
    records = [];
    roundTables = [];
    document.getElementById("summary").innerHTML = "";
    document.getElementById("compare").innerHTML = "";
    document.getElementById("tables").innerHTML = "";
  }

  const res = await fetch("/analyze",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pattern})
  });
  const data = await res.json();

  records.push(data);

  let tblHtml = `
    <div>
      <h3>${pattern} 查詢結果</h3>
      <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
      ${data.rows.map(r=>`<tr><td>${r.num}</td><td>${r.cnt}</td><td>${r.prob}</td></tr>`).join("")}
      </table>
    </div>
  `;
  roundTables.push(tblHtml);
  document.getElementById("tables").innerHTML = roundTables.join("");

  if(records.length === 3){
    renderCompareTable();
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

  document.getElementById("summary").innerHTML = `
    <h2>加總結果摘要</h2>
    <p class="highlight">前三名：${top3Text}</p>
    <div class="diff-box">單 ${odd}，雙 ${even} → ${diffOddEven}</div>
    <div class="diff-box">大 ${big}，小 ${small} → ${diffBigSmall}</div>
  `;

  document.getElementById("compare").innerHTML = `
    <h2>三組加總對比表</h2>
    <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
    ${arr.map(o=>`<tr><td>${o.num}</td><td>${o.cnt}</td><td>${(o.prob*100).toFixed(0)}%</td></tr>`).join("")}
    </table>
  `;
}
</script>
</body>
</html>
    """)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    pattern = data.get("pattern","")
    counts, total = find_next_digit_counts(segments, pattern)
    rows = []
    for i,c in enumerate(counts):
        prob = f"{(c/total*100):.0f}%" if total else "0%"
        rows.append({"num":i+1, "cnt":c, "prob":prob})
    return jsonify({"counts":counts, "rows":rows})

if __name__ == "__main__":
    app.run(debug=True)