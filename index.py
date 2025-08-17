from flask import Flask, request, jsonify, render_template_string
import re
import os

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
                counts[nxt-1]+=1
    return counts, sum(counts)

segments = load_segments(TXT_PATH)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>詳細使用方法請詳(Line:19931026a)</title>
  <style>
    body { font-family: Arial; padding:20px; }
    input { padding:5px; font-size:16px; }
    button { padding:5px 10px; font-size:16px; }
    table { border-collapse: collapse; margin-top:10px; width:100%; }
    th, td { border:1px solid #ccc; padding:6px; text-align:center; }
    .highlight { font-weight:bold; font-size:18px; color:#d9534f; }
  </style>
</head>
<body>
  <h1>詳細使用方法請詳(Line:19931026a)</h1>
  <input id="pattern" placeholder="輸入 6碼 / 5碼 / 4碼">
  <button onclick="search()">查詢</button>

  <div id="results"></div>
  <div id="compare"></div>
  <div id="sumTop3"></div>

<script>
let records = [];

async function search(){
  const pattern = document.getElementById("pattern").value.trim();
  if (!pattern) return;
  const res = await fetch("/api/search", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pattern})
  });
  const data = await res.json();
  if (data.error){
    alert(data.error); return;
  }
  records.push({pattern: pattern, counts:data.counts, total:data.total});
  showResult(pattern, data);

  // 等到三次 (6碼、5碼、4碼) 才做對比
  if (records.length === 3){
    renderCompareTable();
    records = []; // 自動清除，準備下一輪
  }
}

function showResult(pattern, data){
  let html = `<h2>查詢 ${pattern}</h2>`;
  html += `<table><tr><th>數字</th><th>次數</th><th>機率</th></tr>`;
  for (let i=0;i<6;i++){
    const cnt = data.counts[i];
    const prob = data.total ? ((cnt/data.total)*100).toFixed(0)+"%" : "0%";
    html += `<tr><td>${i+1}</td><td>${cnt}</td><td>${prob}</td></tr>`;
  }
  html += "</table>";
  document.getElementById("results").innerHTML += html;
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
  const diffOddEven = odd>even?`👉 單比雙多 ${odd-even} 次`:even>odd?`👉 雙比單多 ${even-odd} 次`:"👉 單雙一樣多";
  const diffBigSmall = big>small?`👉 大比小多 ${big-small} 次`:small>big?`👉 小比大多 ${small-big} 次`:"👉 大小一樣多";

  document.getElementById("compare").innerHTML = `
    <h2>三組對比結果 (6碼+5碼+4碼)</h2>
    <table><tr><th>數字</th><th>次數</th><th>機率</th></tr>
    ${arr.map(o=>`<tr><td>${o.num}</td><td>${o.cnt}</td><td>${(o.prob*100).toFixed(0)}%</td></tr>`).join("")}
    </table>
  `;
  document.getElementById("sumTop3").innerHTML = `
    <h2>加總後的前三名</h2>
    <p class="highlight">${top3Text}</p>
    <h3>單雙大小統計</h3>
    <p>單 ${odd}，雙 ${even}</p><p>${diffOddEven}</p>
    <p>大 ${big}，小 ${small}</p><p>${diffBigSmall}</p>
  `;
}
</script>
</body>
</html>
    """)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json()
    pattern = data.get("pattern","")
    counts,total = find_next_digit_counts(segments, pattern)
    if total==0:
        return jsonify({"error":"找不到組合"})
    return jsonify({"counts":counts,"total":total})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)