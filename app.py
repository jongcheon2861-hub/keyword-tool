import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

st.set_page_config(page_title="쿠팡키워드 추출기", layout="centered",
                   initial_sidebar_state="collapsed")

# ---------- 시크릿 ----------
API_KEY = st.secrets["API_KEY"]
SECRET = st.secrets["SECRET"]
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]
N_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
N_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

# ---------- 상수 ----------
MAX_KEYWORDS = 20
MIN_VOL = 10
TOP_N = 50

CATEGORY_MAP = {
    "과일": ["샤인머스캣", "사과", "포도", "귤", "딸기", "복숭아", "배", "감", "수박", "참외"],
    "채소": ["양파", "감자", "당근", "고구마", "마늘", "대파", "배추", "무"],
    "생활": ["휴지", "물티슈", "세제", "섬유유연제", "주방세제"],
}
BUY_COMMON = ["구매", "주문", "배송", "택배", "가격", "최저가", "특가", "무료배송", "당일배송"]
BUY_CAT = {
    "과일": ["kg", "박스", "산지직송", "제철", "당도", "달콤한", "선물", "선물세트"],
    "채소": ["kg", "박스", "국내산", "신선"],
    "생활": ["대용량", "묶음", "리필"],
}
INFO_WORDS = ["효능", "칼로리", "방법", "레시피", "뜻", "의미", "부작용", "후기만", "나무위키"]

# ---------- 함수 ----------
def normalize(s):
    return s.replace(" ", "").replace("머스켓", "머스캣")

def get_parent_terms(product):
    terms = set()
    for cat, items in CATEGORY_MAP.items():
        for it in items:
            if normalize(it) in normalize(product) or normalize(product) in normalize(it):
                terms.add(cat)
    return terms

def _naver_sign(ts, method, uri):
    msg = f"{ts}.{method}.{uri}"
    sig = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()

def naver_related_keywords(seed):
    uri = "/keywordstool"
    ts = str(round(time.time() * 1000))
    headers = {
        "X-Timestamp": ts,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": _naver_sign(ts, "GET", uri),
    }
    params = {"hintKeywords": seed.replace(" ", ""), "showDetail": "1"}
    try:
        r = requests.get("https://api.searchad.naver.com" + uri,
                         headers=headers, params=params, timeout=10)
        data = r.json().get("keywordList", [])
    except Exception:
        return []
    rows = []
    for d in data:
        kw = d.get("relKeyword", "")
        pc = d.get("monthlyPcQcCnt", 0)
        mo = d.get("monthlyMobileQcCnt", 0)
        pc = 0 if pc in ("< 10", "<10") else int(pc)
        mo = 0 if mo in ("< 10", "<10") else int(mo)
        rows.append({"kw": kw, "vol": pc + mo})
    return rows

def score_keyword(kw, vol, parents):
    s = 0.0
    for p in parents:
        if p in kw:
            s += 0.05
    for w in BUY_COMMON:
        if w in kw:
            s += 0.08
    for cat in parents:
        for w in BUY_CAT.get(cat, []):
            if w in kw:
                s += 0.06
    for w in INFO_WORDS:
        if w in kw:
            s -= 0.5
    s += min(vol / 20000, 1.0) * 0.85
    return round(s, 3)

# ---------- 상태 ----------
if "selected" not in st.session_state:
    st.session_state.selected = []
if "results" not in st.session_state:
    st.session_state.results = []
if "popup" not in st.session_state:
    st.session_state.popup = None
if "popup_id" not in st.session_state:
    st.session_state.popup_id = 0

def toggle_keyword(kw):
    if kw in st.session_state.selected:
        st.session_state.selected.remove(kw)
    elif len(st.session_state.selected) >= MAX_KEYWORDS:
        st.session_state.popup = f"{MAX_KEYWORDS} / {MAX_KEYWORDS}"
        st.session_state.popup_id += 1
        return
    else:
        st.session_state.selected.append(kw)
    st.session_state.popup = f"{len(st.session_state.selected)} / {MAX_KEYWORDS}"
    st.session_state.popup_id += 1

def run_extract():
    product = st.session_state.get("raw_input", "").strip()
    if not product:
        return
    parents = get_parent_terms(product)
    all_rows = []
    seen = set()
    for seed in product.split():
        for row in naver_related_keywords(seed):
            kw, vol = row["kw"], row["vol"]
            if vol < MIN_VOL:
                continue
            if kw in seen:
                continue
            seen.add(kw)
            all_rows.append({"kw": kw, "vol": vol,
                             "score": score_keyword(kw, vol, parents)})
    all_rows.sort(key=lambda x: x["score"], reverse=True)
    st.session_state.results = all_rows[:TOP_N]
    st.session_state.parents = parents

# ---------- CSS ----------
st.markdown("""
<style>
header[data-testid="stHeader"] {display:none !important;}
[data-testid="stToolbar"] {display:none !important;}
[data-testid="stDecoration"] {display:none !important;}
.block-container {padding-top:0.6rem !important;}

/* 상단 카드 */
.topcard {
    background: linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%);
    padding: 16px 20px 4px 20px;
    border: 1px solid #e6e8eb;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    margin-bottom: 10px;
}
.bar-title {font-size:22px; font-weight:800; color:#263238; margin-bottom:12px;}
.copy-head {font-size:15px; font-weight:700; color:#37474f; margin:2px 0 6px 0;}
.copy-badge {background:#1565c0; color:#fff; font-size:12px; font-weight:700;
             padding:2px 10px; border-radius:12px; margin-left:6px;}

/* 복사박스: 높이 고정, 좌우로만 늘어남 (아래로 절대 안 늘어남) */
.copy-box {
    background:#f0f7ff; border:1.5px solid #90caf9; border-radius:10px;
    color:#1565c0; font-size:15px; font-weight:500;
    padding:0 14px;
    height:46px; line-height:46px;          /* 고정 높이 */
    white-space:nowrap;
    overflow-x:auto; overflow-y:hidden;
    box-sizing:border-box;
}

/* 상위어 안내 */
.parent-box {
    background:#e3f2fd; border-radius:10px; color:#1565c0;
    font-size:14px; padding:12px 16px; margin:14px 0 4px 0;
}
.list-head {font-size:24px; font-weight:800; color:#263238; margin:6px 0 10px 0;}

/* 입력창 / 버튼 높이 정렬 */
div[data-testid="stTextInput"] input {height:52px !important; font-size:16px !important;}
[data-testid="stBaseButton-primary"] {
    height:52px !important; min-height:52px !important;
    font-weight:700 !important; border-radius:10px !important;
}

/* 키워드 버튼 */
[data-testid="stBaseButton-secondary"] {
    min-height:44px !important; height:44px !important;
    padding:0 14px !important; border-radius:12px !important;
    border:1.5px solid #e6e8eb !important; background:#fff !important;
}
[data-testid="stBaseButton-secondary"] p {
    font-size:17px !important; font-weight:500 !important;
    white-space:nowrap !important; overflow:hidden !important;
    text-overflow:ellipsis !important;
}
[data-testid="stBaseButton-secondary"]:hover {border-color:#4a90d9 !important;}

/* 선택된 키워드 강조 */
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] {
    background:#eef6ff !important; border-color:#4a90d9 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] p {
    color:#1565c0 !important; font-weight:700 !important;
}

/* 선택 마커: 높이 0 → 눌러도 간격 안 벌어짐 */
.kw-picked {display:block; height:0 !important; margin:0 !important; padding:0 !important;
            overflow:hidden !important; line-height:0 !important;}
[data-testid="stElementContainer"]:has(.kw-picked) {
    height:0 !important; margin:0 !important; padding:0 !important; min-height:0 !important;
}

/* 세로/가로 간격 축소 (처음부터 촘촘하게) */
div[data-testid="stVerticalBlock"] {gap:0.15rem !important;}
div[data-testid="stHorizontalBlock"] {gap:0.4rem !important;}
[data-testid="stElementContainer"] {margin:0 !important;}

/* 스크롤 컨테이너(목록) 테두리 제거 */
div[data-testid="stVerticalBlockBorderWrapper"] {border:none !important;}

/* 중앙 팝업 */
@keyframes popfade {0%{opacity:0;} 15%{opacity:1;} 85%{opacity:1;} 100%{opacity:0;}}
.center-pop {
    position:fixed; top:30%; left:50%; transform:translate(-50%,-50%);
    background:linear-gradient(135deg,#667eea 0%,#764ba2 45%,#f093fb 100%);
    color:#fff; font-size:20px; font-weight:800;
    padding:14px 30px; border-radius:16px;
    box-shadow:0 10px 30px rgba(118,75,162,0.4);
    z-index:99999; animation:popfade 1s ease forwards; pointer-events:none;
}
</style>
""", unsafe_allow_html=True)

# ---------- 팝업 ----------
if st.session_state.popup:
    st.markdown(
        f"<div class='center-pop' id='pop{st.session_state.popup_id}'>{st.session_state.popup}</div>",
        unsafe_allow_html=True)
    st.session_state.popup = None

# ---------- 상단 카드 ----------
st.markdown("<div class='topcard'><div class='bar-title'>🛒 쿠팡키워드 추출기</div></div>",
            unsafe_allow_html=True)

ca, cb = st.columns([3, 1.1], vertical_alignment="bottom")
with ca:
    st.text_input("상품명", "샤인머스캣", key="raw_input",
                  on_change=run_extract, label_visibility="collapsed")
with cb:
    st.button("🔍 추출하기", use_container_width=True,
              on_click=run_extract, type="primary")

n = len(st.session_state.selected)
st.markdown(
    f"<div class='copy-head'>📋 복사용 키워드 <span class='copy-badge'>{n}개</span></div>",
    unsafe_allow_html=True)
kw_text = ", ".join(st.session_state.selected) + " ," if st.session_state.selected else " "
st.markdown(f"<div class='copy-box'>{kw_text}</div>", unsafe_allow_html=True)

# ---------- 상위어 안내 ----------
parents = st.session_state.get("parents", set())
if parents:
    st.markdown(
        f"<div class='parent-box'>자동 인식된 상위어: {', '.join(parents)}</div>",
        unsafe_allow_html=True)

# ---------- 목록 (고정 높이 스크롤 컨테이너) ----------
st.markdown("<div class='list-head'>추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)</div>",
            unsafe_allow_html=True)

# ★ 핵심: 목록만 고정 높이 컨테이너 안에서 스크롤 → 상단 항상 보이고 아래 안 늘어남
with st.container(height=480):
    for i, row in enumerate(st.session_state.results):
        kw, vol, score = row["kw"], row["vol"], row["score"]
        c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="center")
        with c1:
            if kw in st.session_state.selected:
                st.markdown("<span class='kw-picked'></span>", unsafe_allow_html=True)
            st.button(kw, key=f"kw_{i}", use_container_width=True,
                      on_click=toggle_keyword, args=(kw,), type="secondary")
        with c2:
            st.markdown(f"<div style='text-align:center;font-weight:700;'>{vol:,}</div>",
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div style='text-align:center;color:#37474f;'>{score}</div>",
                        unsafe_allow_html=True)
