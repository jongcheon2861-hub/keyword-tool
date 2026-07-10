import streamlit as st

st.set_page_config(page_title="진단", layout="centered")

st.markdown("""
<div id="diag-marker" style="padding:10px;background:#43e97b;color:#fff;border-radius:8px;">
진단 마커
</div>
<script>
const out = [];
let marker = window.parent.document.getElementById('diag-marker');
out.push("parent 접근 가능: " + (marker ? "예" : "아니오(iframe 격리)"));
out.push("iframe 개수: " + window.parent.document.querySelectorAll('iframe').length);
out.push("내 위치 iframe? " + (window.self !== window.top ? "예(iframe 안)" : "아니오(최상위)"));
const box = document.createElement('div');
box.style.cssText = "margin-top:10px;padding:10px;background:#222;color:#0f0;font-family:monospace;white-space:pre-wrap;border-radius:8px;";
box.textContent = out.join("\\n");
document.body.appendChild(box);
</script>
""", unsafe_allow_html=True)

st.write("위 초록 박스 아래 검은 상자의 내용을 알려주세요.")
