import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="쿠팡 마진 계산기", layout="wide")

# 메인으로 돌아가기 링크
st.page_link("app.py", label="⬅ 키워드 추출기로 돌아가기")

MARGIN_CALC_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
  h1 { font-size: 22px; text-align: center; color: #1a73e8; margin: 0 0 8px; }
  .desc { text-align: center; font-size: 13px; color: #777; margin-bottom: 20px; }
  .table-wrap { overflow-x: auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 16px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #e3e8ef; padding: 6px 6px; text-align: center; white-space: nowrap; }
  thead th { background: #1a73e8; color: #fff; font-weight: 600; position: sticky; top: 0; }
  tbody tr:nth-child(even) { background: #f9fbff; }
  input, select { width: 100%; padding: 7px 6px; font-size: 13px; border: 1px solid #d5dae1; border-radius: 6px; outline: none; text-align: right; }
  input[type="text"] { text-align: left; }
  input:focus, select:focus { border-color: #1a73e8; }
  .col-no { width: 36px; } .col-name { width: 300px; } .col-num { width: 66px; } .col-margin { width: 74px; } .col-out { width: 84px; }
  td.result { font-weight: 700; background: #f0f5ff; color: #1a73e8; }
  td.discount-cell { font-weight: 700; background: #fdeef0; color: #d63384; }
  td.margin-cell { font-weight: 700; background: #eafaf3; color: #00a86b; }
  .no-col { background:#f4f6f9; font-weight:600; color:#555; }
  .buttons { margin: 16px auto 0; text-align: center; }
  .btn { background: #1a73e8; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; margin: 0 4px; }
  .btn.gray { background: #888; }
  .btn:hover { opacity: 0.9; }
  tfoot td { background: #fff7e6; font-weight: 700; color: #d35400; }
</style>
</head>
<body>

<h1>🧮 쿠팡 마진 계산기</h1>
<div class="desc">판매가 100원 단위 내림 · 마진율 자동 보정 · 최대 10개</div>

<div class="table-wrap">
  <table>
    <colgroup>
      <col class="col-no"><col class="col-name"><col class="col-num"><col class="col-num">
      <col class="col-num"><col class="col-num"><col class="col-margin">
      <col class="col-out"><col class="col-margin"><col class="col-out"><col class="col-out">
    </colgroup>
    <thead>
      <tr>
        <th>No</th><th>상품명</th><th>공급가</th><th>택배비</th>
        <th>할인율<br>(%)</th><th>쿠팡<br>수수료(%)</th><th>마진율</th>
        <th>판매가</th><th>마진액</th><th>쿠폰<br>할인금액</th><th>상품등록가<br>(정가)</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
    <tfoot>
      <tr>
        <td colspan="7">합계</td>
        <td id="sumFinal">-</td><td id="sumMargin">-</td><td id="sumDiscount">-</td><td id="sumOrig">-</td>
      </tr>
    </tfoot>
  </table>
</div>

<div class="buttons">
  <button class="btn" onclick="addRow()">+ 행 추가</button>
  <button class="btn gray" onclick="clearAll()">전체 초기화</button>
</div>

<script>
  const ROWS = 10;
  const DEFAULT_TARGET = 20.0;
  const tbody = document.getElementById('tbody');

  function marginOptions() {
    let html = '';
    for (let r = 40.0; r >= 9.99; r -= 0.1) {
      const v = r.toFixed(1);
      const selected = (v === '20.0') ? ' selected' : '';
      html += `<option value="${v}"${selected}>${v}%</option>`;
    }
    return html;
  }

  function createRow(i) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="no-col">${i + 1}</td>
      <td><input type="text" maxlength="40" placeholder="상품명 (최대 40자)"></td>
      <td><input type="number" class="supply" placeholder="0" oninput="calc()"></td>
      <td><input type="number" class="ship" value="0" oninput="calc()"></td>
      <td><input type="number" class="disc" value="60" oninput="calc()"></td>
      <td><input type="number" class="fee" value="12" step="0.1" oninput="calc()"></td>
      <td><select class="margin" onchange="onMarginChange(this)">${marginOptions()}</select></td>
      <td class="result finalOut">-</td>
      <td class="margin-cell marginOut">-</td>
      <td class="discount-cell discountOut">-</td>
      <td class="result origOut">-</td>
    `;
    tr.querySelector('.margin').dataset.userTarget = DEFAULT_TARGET.toFixed(1);
    return tr;
  }

  function buildTable() {
    tbody.innerHTML = '';
    for (let i = 0; i < ROWS; i++) tbody.appendChild(createRow(i));
  }

  function addRow() {
    if (tbody.children.length >= ROWS) { alert('최대 ' + ROWS + '개까지 계산할 수 있습니다.'); return; }
    tbody.appendChild(createRow(tbody.children.length));
  }

  function clearAll() {
    if (confirm('입력한 내용을 모두 지울까요?')) { buildTable(); calc(); }
  }

  function won(n) { return Math.round(n).toLocaleString('ko-KR'); }

  function onMarginChange(sel) {
    sel.dataset.userTarget = parseFloat(sel.value).toFixed(1);
    calc();
  }

  function setSelectToRate(sel, ratePct) {
    let r = Math.round(ratePct * 10) / 10;
    if (r > 40.0) r = 40.0;
    if (r < 10.0) r = 10.0;
    sel.value = r.toFixed(1);
  }

  function calc() {
    let sumOrig = 0, sumDiscount = 0, sumFinal = 0, sumMargin = 0;

    tbody.querySelectorAll('tr').forEach(tr => {
      const supply = parseFloat(tr.querySelector('.supply').value) || 0;
      const ship = parseFloat(tr.querySelector('.ship').value) || 0;
      const feeRate = (parseFloat(tr.querySelector('.fee').value) || 0) / 100;
      const discRate = (parseFloat(tr.querySelector('.disc').value) || 0) / 100;
      const marginSel = tr.querySelector('.margin');

      const finalOut = tr.querySelector('.finalOut');
      const marginOut = tr.querySelector('.marginOut');
      const discountOut = tr.querySelector('.discountOut');
      const origOut = tr.querySelector('.origOut');

      const targetRate = (parseFloat(marginSel.dataset.userTarget) || DEFAULT_TARGET) / 100;

      if (supply <= 0) {
        setSelectToRate(marginSel, targetRate * 100);
        finalOut.textContent = marginOut.textContent =
          discountOut.textContent = origOut.textContent = '-';
        return;
      }

      const denom = 1 - feeRate - targetRate;
      if (denom <= 0) {
        finalOut.textContent = marginOut.textContent =
          discountOut.textContent = origOut.textContent = '오류';
        return;
      }

      let finalPrice = (supply + ship) / denom;
      finalPrice = Math.floor(finalPrice / 100) * 100;

      const fee = finalPrice * feeRate;
      const margin = finalPrice - supply - ship - fee;

      const actualRate = margin / finalPrice * 100;
      setSelectToRate(marginSel, actualRate);

      const original = finalPrice * (1 + discRate);
      const discountAmount = original - finalPrice;

      finalOut.textContent = won(finalPrice);
      marginOut.textContent = won(margin);
      discountOut.textContent = won(discountAmount);
      origOut.textContent = won(original);

      sumFinal += finalPrice;
      sumMargin += margin;
      sumDiscount += discountAmount;
      sumOrig += original;
    });

    document.getElementById('sumFinal').textContent = won(sumFinal);
    document.getElementById('sumMargin').textContent = won(sumMargin);
    document.getElementById('sumDiscount').textContent = won(sumDiscount);
    document.getElementById('sumOrig').textContent = won(sumOrig);
  }

  buildTable();
  calc();
</script>
</body>
</html>
"""

components.html(MARGIN_CALC_HTML, height=800, scrolling=True)
