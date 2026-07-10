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
    "과일": ["샤인머스캣", "사과", "포도", "귤", "딸기", "복숭아"],
    "채소": ["양파", "감자", "당근", "고구마"],
    "생활": ["휴지", "물티슈", "세제"],
}
BUY_COMMON = ["구매", "주문", "배송", "택배", "가격", "최저가", "특가", "무료배송", "당일배송"]
BUY_CAT = {
    "과일": ["kg", "박스", "산지직송", "제철", "당도", "달콤한"],
    "채소": ["kg", "박스", "국내산", "신선"],
    "생활": ["대용량", "묶음", "리필"],
}
INFO_WORDS = ["효능", "칼로리", "방법", "레시피", "뜻", "의미", "부작용", "후기만", "나무위키"]

# ---------- 함수 ----------
def normalize(s):
    return s.replace(" ", "").replace("머스켓", "머스캣")

def get_parent_terms(product):
    terms, big = [], ""
    try:
        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {"X-Naver-Client-Id": N_CLIENT_ID,
                   "X-Naver-Client-Secret": N_CLIENT_SECRET}
        params = {"query": product, "display": 10}
        r = requests.get(url, headers=headers, params=params, timeout=5)
        if r.status_code == 200:
            cats = set()
            for it in r.json().get("items", []):
                for k in ("category1", "category2", "category3"):
                    v = it.get(k, "").strip()
                    if v:
                        cats.add(v)
            terms = list(cats)
    except Exception:
        pass
    npd = normalize(product)
    for cat, members in CATEGORY_MAP.items():
        if any(normalize(m) in npd or npd in normalize(m) for m in members):
            big = cat
            terms.append(cat)
            break
    return list(dict.fromkeys(terms)), big

def _naver_sign(ts, method, path):
    msg = ts + "." + method + "." + path
    sig = hmac.new(SECRET.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("utf-8")

def naver_related_keywords(seed):
    try:
        path = "/keywordstool"
        ts = str(round(time.time() * 1000))
        sig = _naver_sign(ts, "GET", path)
        headers = {"X-Timestamp": ts, "X-API-KEY": API_KEY,
                   "X-Customer": str(CUSTOMER_ID), "X-Signature": sig}
        params = {"hintKeywords": seed.replace(" ", ""), "showDetail": 1}
        r = requests.get("https://api.searchad.naver.com" + path,
                         headers=headers, params=params, timeout=5)
        if r.status_code != 200:
            return pd.DataFrame(columns=["키워드", "검색량"])
        rows = []
        for it in r.json().get("keywordList", []):
            def to_int(x):
                if isinstance(x, str):
                    x = x.replace("<", "").replace(",", "").strip()
                try:
                    return int(x)
                except Exception:
                    return 0
            vol = to_int(it.get("monthlyPcQcCnt", 0)) + to_int(it.get("monthlyMobileQcCnt", 0))
            rows.append({"키워드": it.get("relKeyword", ""), "검색량": vol})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["키워드", "검색량"])

# ---------- 상태 ----------
if "selected" not in st.session_state:
    st.session_state.selected = []
if "popup" not in st.session_state:
    st.session_state.popup = None
if "popup_id" not in st.session_state:
    st.session_state.popup_id = 0

def toggle_keyword(kw):
    if kw in st.session_state.selected:
        st.session_state.selected.remove(kw)
        st.session_state.popup = str(len(st.session_state.selected)) + " / " + str(MAX_KEYWORDS)
    elif len(st.session_state.selected) >= MAX_KEYWORDS:
        st.session_state.popup = str(MAX_KEYWORDS) + " / " + str(MAX_KEYWORDS)
    else:
        st.session_state.selected.append(kw)
        st.session_state.popup = str(len(st.session_state.selected)) + " / " + str(MAX_KEYWORDS)
    st.session_state.popup_id += 1

def run_extract():
    products = st.session_state.get("raw_input", "").split()
    if not products:
        st.session_state.results = []
        return
    norm_products = [normalize(p) for p in products]
    related_terms, intent_words = set(), set(BUY_COMMON)
    for p in products:
        terms, big = get_parent_terms(p)
        related_terms |= set(terms)
        intent_words |= set(BUY_CAT.get(big, []))
    st.session_state.related_info = ", ".join(sorted(related_terms)) or "없음"
    seeds = list(dict.fromkeys(list(products) + list(related_terms)))[:12]
    frames = []
    for s in seeds:
        frames.append(naver_related_keywords(s))
        time.sleep(0.2)
    if frames and not all(f.empty for f in frames):
        all_kw = pd.concat(frames, ignore_index=True).drop_duplicates("키워드")
        norm_terms = [normalize(t) for t in related_terms]
        def is_related(kw):
            nk = normalize(kw)
            return any(t in nk for t in norm_products) or any(t in nk for t in norm_terms)
        all_kw = all_kw[all_kw["키워드"].apply(is_related)]
        if INFO_WORDS:
            all_kw = all_kw[~all_kw["키워드"].str.contains("|".join(INFO_WORDS))]
        all_kw = all_kw[all_kw["검색량"] >= MIN_VOL]
        iw = list(intent_words)
        all_kw["구매의도"] = all_kw["키워드"].apply(lambda k: sum(1 for w in iw if w in k))
        all_kw["상품직결"] = all_kw["키워드"].apply(
            lambda k: 1 if any(t in normalize(k) for t in norm_products) else 0)
        all_kw["구매전환추정점수"] = (
            all_kw["상품직결"] * 0.4 +
            all_kw["검색량"].rank(pct=True) * 0.35 +
            all_kw["구매의도"].rank(pct=True) * 0.25
        ).round(3)
        result = all_kw.sort_values(["상품직결", "구매전환추정점수"],
                                    ascending=[False, False]).head(TOP_N)
        st.session_state.results = result[
            ["키워드", "검색량", "구매의도", "구매전환추정점수"]].values.tolist()
    else:
        st.session_state.results = []

# ---------- CSS ----------
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ★ 페이지 전체 스크롤 막기 → 상단바 영역 고정 효과 */
html, body { overflow: hidden !important; height: 100vh !important; }
[data-testid="stAppViewContainer"] { overflow: hidden !important; height: 100vh !important; }
[data-testid="stMain"] { overflow: hidden !important; }
.block-container {
    padding-top: 0.5rem !important;
    height: 100vh !important;
    overflow: hidden !important;
}

/* 상단 카드 (고정 아님, 그냥 위에 배치) */
.topcard {
    background: linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%);
    padding: 16px 20px 6px 20px;
    border: 1px solid #e6e8eb;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    margin-bottom: 6px;
}
.bar-title { font-size: 22px; font-weight: 800; color: #263238; margin-bottom: 10px; }

div[data-testid="stTextInput"] input { height: 52px !important; font-size: 16px !important; }
[data-testid="stBaseButton-primary"] {
    height: 40px !important; min-height: 40px !important;
    padding: 0 !important; margin: 0 !important;
    font-weight: 700 !important; border-radius: 14px !important;
}

.copy-head { font-size: 15px; font-weight: 700; color:#37474f; margin: 8px 0 20px 0; }
.copy-badge { background:#1565c0; color:#fff; font-size:12px; font-weight:700;
    padding:2px 10px; border-radius:12px; margin-left:6px; }
[data-testid="stCode"] {
    background: #f0f7ff !important; border: 1.5px solid #90caf9 !important;
    border-radius: 10px !important; margin: 0 !important;
}
[data-testid="stCode"] pre {
    background: transparent !important;
    white-space: nowrap !important;
    overflow-x: scroll !important;
    overflow-y: hidden !important;
    padding: 12px 52px 10px 14px !important;
}
[data-testid="stCode"] code {
    color: #1565c0 !important; font-weight: 400 !important;
    font-size: 12px !important; white-space: nowrap !important;
}
[data-testid="stCode"] pre::-webkit-scrollbar { height: 9px; }
[data-testid="stCode"] pre::-webkit-scrollbar-thumb { background: #90caf9; border-radius: 6px; }
[data-testid="stCode"] pre::-webkit-scrollbar-track { background: #e3f2fd; border-radius: 6px; }

/* 상위어 안내 */
.parent-box {
    background:#e3f2fd; border-radius:10px; color:#1565c0;
    font-size:14px; padding:12px 16px; margin:6px 0 4px 0;
}
.list-head { font-size:20px; font-weight:800; color:#263238; margin:14px 0 14px 0; }

/* 키워드 버튼 */
[data-testid="stBaseButton-secondary"] {
    min-height: 44px !important; height: 44px !important;
    padding: 0 14px !important;
    border-radius: 12px !important; border: 1.5px solid #e6e8eb !important;
    background: #ffffff !important; transition: all .12s ease !important;
    justify-content: flex-start !important;
}
[data-testid="stBaseButton-secondary"] p {
    font-size: 17px !important; font-weight: 500 !important; line-height: 1.1 !important;
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
}
[data-testid="stBaseButton-secondary"]:hover { border-color:#ff7043 !important; }
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] {
    background: #eef6ff !important; border-color: #4a90d9 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] p {
    color: #1565c0 !important; font-weight: 700 !important;
}

/* 선택 마커: 높이 0 → 눌러도 간격 안 벌어짐 */
.kw-picked { display:block !important; height:0 !important; margin:0 !important;
    padding:0 !important; overflow:hidden !important; line-height:0 !important; }
[data-testid="stElementContainer"]:has(.kw-picked) {
    height:0 !important; min-height:0 !important; margin:0 !important; padding:0 !important;
}

/* 세로/가로 간격 좁게 */
div[data-testid="stVerticalBlock"] { gap: 0.15rem !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.4rem !important; }
[data-testid="stElementContainer"] { margin: 0 !important; }

.metric-val { min-height:44px; display:flex; align-items:center; justify-content:center;
    font-size:16px; font-weight:600; color:#607d8b; }

/* 목록 스크롤 컨테이너 테두리 제거 */
div[data-testid="stVerticalBlockBorderWrapper"] { border:none !important; }

.center-popup {
    position: fixed; top: 30%; left: 50%;
    transform: translate(-50%, -50%); z-index: 100000;
    padding: 12px 26px; border-radius: 16px;
    font-size: 22px; font-weight: 800; color: #ffffff;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 45%, #f093fb 100%);
    box-shadow: 0 12px 30px rgba(118,75,162,0.45);
    pointer-events: none; white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# ---------- 팝업 ----------
if st.session_state.get("popup"):
    pid = str(st.session_state.popup_id)
    msg = st.session_state.popup
    anim = "popfade" + pid
    ph = """
    <style>
    @keyframes ANIM {
        0%{opacity:0;transform:translate(-50%,-50%) scale(0.8);}
        15%{opacity:1;transform:translate(-50%,-50%) scale(1);}
        80%{opacity:1;transform:translate(-50%,-50%) scale(1);}
        100%{opacity:0;transform:translate(-50%,-50%) scale(0.9);}
    }
    #popup-PID { animation: ANIM 1s ease forwards; }
    </style>
    <div class="center-popup" id="popup-PID">✅ MSG</div>
    """
    ph = ph.replace("ANIM", anim).replace("PID", pid).replace("MSG", msg)
    st.markdown(ph, unsafe_allow_html=True)
    st.session_state.popup = None

# ==================================================================
# 1) 상단 박스 영역 (제목 + 검색 + 복사용 키워드)  ← 스크롤 안 됨
# ==================================================================
st.markdown('<div class="topcard"><div class="bar-title">🛒 쿠팡키워드 추출기</div></div>',
            unsafe_allow_html=True)

ta, tb = st.columns([3, 1.2], vertical_alignment="bottom")
with ta:
    st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣",
                  key="raw_input", on_change=run_extract,
                  label_visibility="collapsed")
with tb:
    st.button("🔍 추출하기", use_container_width=True,
              on_click=run_extract, type="primary")

n = len(st.session_state.selected)
st.markdown('<div class="copy-head">📋 복사용 키워드 '
            '<span class="copy-badge">' + str(n) + '개</span></div>',
            unsafe_allow_html=True)
kw_text = ",".join(st.session_state.selected) + "," if st.session_state.selected else " "
st.code(kw_text, language=None)

# ==================================================================
# 2) 추출된 키워드 영역 (분리 + 컨테이너 안에서만 스크롤)
# ==================================================================
if st.session_state.get("results"):
    st.markdown('<div class="parent-box">자동 인식된 상위어: '
                + st.session_state.get("related_info", "") + '</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="list-head">추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)</div>',
                unsafe_allow_html=True)

    # ★ 목록만 고정 높이 컨테이너 안에서 스크롤 (숫자로 하단까지 조절)
    with st.container(height=620):
        for i, (kw, vol, intent, score) in enumerate(st.session_state.results):
            c1, c2, c3 = st.columns([3, 1.4, 1.2], vertical_alignment="center")
            already = kw in st.session_state.selected
            with c1:
                if already:
                    st.markdown("<span class='kw-picked'></span>", unsafe_allow_html=True)
                st.button(kw, key="pick_" + str(i),
                          on_click=toggle_keyword, args=(kw,), use_container_width=True)
            c2.markdown("<div class='metric-val'>" + format(vol, ",") + "</div>",
                        unsafe_allow_html=True)
            c3.markdown("<div class='metric-val'>" + str(score) + "</div>",
                        unsafe_allow_html=True)
elif "results" in st.session_state:
    st.warning("수집된 키워드가 없습니다. 상품명이나 개수를 조정해 보세요.")
