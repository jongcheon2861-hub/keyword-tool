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

TOO_BROAD = ["선물", "추천", "인기", "판매", "브랜드", "세트", "모음"]

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
    s = s.replace(" ", "")
    s = s.replace("머스켓", "머스캣")
    return s

def get_parent_terms(product):
    """네이버 쇼핑 검색으로 상위어(카테고리) 추출"""
    terms, big = [], ""
    try:
        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": N_CLIENT_ID,
            "X-Naver-Client-Secret": N_CLIENT_SECRET,
        }
        params = {"query": product, "display": 10}
        r = requests.get(url, headers=headers, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get("items", [])
            cats = set()
            for it in items:
                for k in ("category1", "category2", "category3"):
                    v = it.get(k, "").strip()
                    if v:
                        cats.add(v)
            terms = list(cats)
    except Exception:
        pass
    # 내부 카테고리 매핑으로 큰 분류 추정
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
    """네이버 검색광고 키워드도구 API"""
    try:
        path = "/keywordstool"
        ts = str(round(time.time() * 1000))
        sig = _naver_sign(ts, "GET", path)
        headers = {
            "X-Timestamp": ts,
            "X-API-KEY": API_KEY,
            "X-Customer": str(CUSTOMER_ID),
            "X-Signature": sig,
        }
        params = {"hintKeywords": seed.replace(" ", ""), "showDetail": 1}
        r = requests.get("https://api.searchad.naver.com" + path,
                         headers=headers, params=params, timeout=5)
        if r.status_code != 200:
            return pd.DataFrame(columns=["키워드", "검색량"])
        rows = []
        for it in r.json().get("keywordList", []):
            kw = it.get("relKeyword", "")
            pc = it.get("monthlyPcQcCnt", 0)
            mo = it.get("monthlyMobileQcCnt", 0)
            def to_int(x):
                if isinstance(x, str):
                    x = x.replace("<", "").replace(",", "").strip()
                try:
                    return int(x)
                except Exception:
                    return 0
            vol = to_int(pc) + to_int(mo)
            rows.append({"키워드": kw, "검색량": vol})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["키워드", "검색량"])

# ---------- 상태 ----------
if "selected" not in st.session_state:
    st.session_state.selected = []

def toggle_keyword(kw):
    if kw in st.session_state.selected:
        st.session_state.selected.remove(kw)
        st.toast(str(len(st.session_state.selected)) + " / " + str(MAX_KEYWORDS), icon="✅")
    elif len(st.session_state.selected) >= MAX_KEYWORDS:
        st.toast(str(MAX_KEYWORDS) + " / " + str(MAX_KEYWORDS), icon="✅")
    else:
        st.session_state.selected.append(kw)
        st.toast(str(len(st.session_state.selected)) + " / " + str(MAX_KEYWORDS), icon="✅")

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
        result = all_kw.sort_values(
            ["상품직결", "구매전환추정점수"], ascending=[False, False]).head(TOP_N)
        st.session_state.results = result[
            ["키워드", "검색량", "구매의도", "구매전환추정점수"]].values.tolist()
    else:
        st.session_state.results = []

# ---------- CSS ----------
st.markdown("""
<style>
/* 기본 헤더/툴바 숨김 */
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ★ sticky 동작을 위해 상위 컨테이너 overflow 해제 */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.block-container,
[data-testid="stAppViewBlockContainer"] {
    overflow: visible !important;
}
.block-container {
    padding-top: 0.5rem !important;
    margin-top: 0 !important;
}

/* ★ 상단 고정바 : topbar-anchor 를 가진 블록을 sticky */
div[data-testid="stVerticalBlock"]:has(> div div.topbar-anchor),
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) {
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
    background: linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%) !important;
    padding: 12px 18px 14px 18px !important;
    border: 1px solid #e6e8eb !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08) !important;
    margin-bottom: 14px !important;
}

/* 앵커 자체는 공간 차지 안 하게 */
div.topbar-anchor { height: 0; margin: 0; padding: 0; }

/* 타이틀 */
.bar-title {
    font-size: 22px; font-weight: 800; color: #263238;
    margin-bottom: 8px;
}

/* 입력창 · 버튼 높이 맞춤 */
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) div[data-testid="stTextInput"] input {
    height: 52px !important; font-size: 16px !important;
}
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) .stButton button {
    height: 52px !important; margin-top: 30px !important;
    font-weight: 700 !important; border-radius: 10px !important;
}

/* 복사용 키워드 헤더 */
.copy-head { font-size: 15px; font-weight: 700; color: #37474f; margin: 4px 0 6px 0; }
.copy-badge {
    background: #1565c0; color: #fff; font-size: 12px; font-weight: 700;
    padding: 2px 10px; border-radius: 12px; margin-left: 6px;
}

/* 복사용 코드박스 : 얇은 글씨 · 가로 스크롤 */
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) [data-testid="stCode"] pre,
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) code {
    background: #f0f7ff !important;
    border: 1.5px solid #90caf9 !important;
    color: #1565c0 !important;
    font-weight: 400 !important;
    white-space: nowrap !important;
    overflow-x: auto !important;
}

/* 결과 키워드 버튼 */
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button {
    padding: 11px 15px !important;
    min-height: 52px !important;
    border-radius: 14px !important;
    border: 1.5px solid #e6e8eb !important;
    background: #ffffff !important;
    text-align: left !important;
    transition: all .15s ease !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button p,
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button div,
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button span {
    font-size: 20px !important; font-weight: 500 !important; line-height: 1.2 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button:hover {
    border-color: #ff7043 !important;
    box-shadow: 0 4px 12px rgba(255,112,67,0.18) !important;
    transform: translateY(-1px);
}
/* 담긴 상태 */
div[data-testid="stHorizontalBlock"]:has(.kw-picked) .stButton button {
    background: #eef6ff !important; border-color: #4a90d9 !important; color: #1565c0 !important;
}

/* 결과 행 간격 좁힘 */
div[data-testid="stVerticalBlock"]:has(.kw-row) { gap: 0.15rem !important; }

/* 지표 텍스트 */
.metric-val {
    min-height: 52px; display: flex; align-items: center; justify-content: center;
    font-size: 17px; font-weight: 600; color: #607d8b;
}

/* ===== 알림(토스트) 예쁜 스타일 ===== */
div[data-testid="stToast"] {
    min-width: 130px !important;
    padding: 16px 26px !important;
    border-radius: 20px !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 45%, #f093fb 100%) !important;
    box-shadow: 0 14px 34px rgba(118, 75, 162, 0.45) !important;
    border: none !important;
}
div[data-testid="stToast"] * {
    color: #ffffff !important;
    font-size: 26px !important;
    font-weight: 800 !important;
    letter-spacing: 0.5px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- 상단 고정바 ----------
with st.container():
    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="bar-title">🛒 쿠팡키워드 추출기</div>', unsafe_allow_html=True)
    ta, tb = st.columns([3, 1.2])
    with ta:
        st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣",
                      key="raw_input", on_change=run_extract)
    with tb:
        st.button("🔍 추출하기", use_container_width=True,
                  on_click=run_extract, type="primary")
    n = len(st.session_state.selected)
    st.markdown(
        '<div class="copy-head">📋 복사용 키워드 '
        '<span class="copy-badge">' + str(n) + '개</span></div>',
        unsafe_allow_html=True)
    if st.session_state.selected:
        st.code(",".join(st.session_state.selected) + ",")
    else:
        st.code(" ")

# ---------- 결과 표시 ----------
if st.session_state.get("results"):
    st.info("자동 인식된 상위어: " + st.session_state.get("related_info", ""))
    st.subheader("추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)")
    for i, (kw, vol, intent, score) in enumerate(st.session_state.results):
        c1, cgap, c2, c3 = st.columns([2.1, 0.9, 1.4, 1.2])
        already = kw in st.session_state.selected
        marker = "kw-row kw-picked" if already else "kw-row"
        c1.markdown("<div class='" + marker + "'></div>", unsafe_allow_html=True)
        label = ("✔ " + kw) if already else kw
        c1.button(label, key="pick_" + str(i),
                  on_click=toggle_keyword, args=(kw,), use_container_width=True)
        c2.markdown("<div class='metric-val'>" + format(vol, ",") + "</div>",
                    unsafe_allow_html=True)
        c3.markdown("<div class='metric-val'>" + str(score) + "</div>",
                    unsafe_allow_html=True)
elif "results" in st.session_state:
    st.warning("수집된 키워드가 없습니다. 상품명이나 개수를 조정해 보세요.")
