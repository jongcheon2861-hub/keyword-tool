import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

st.set_page_config(page_title="쿠팡키워드 추출기", layout="centered", initial_sidebar_state="collapsed")

API_KEY = st.secrets["API_KEY"]
SECRET = st.secrets["SECRET"]
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]
N_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
N_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

MAX_KEYWORDS = 20
MIN_VOL = 10

TOO_BROAD = ["식품","농산물","축산물","수산물","과일","채소","정육","건어물",
             "가공식품","신선식품","farm","food"]
CATEGORY_MAP = {
    "과일":"과일/농산물","농산물":"과일/농산물","채소":"과일/농산물",
    "축산":"축산물","정육":"축산물","계란":"축산물",
    "수산":"수산물","건어물":"수산물","젓갈":"수산물",
}
BUY_COMMON = ["선물","선물세트","세트","가격","특가","할인","최저가","주문","구매",
              "택배","당일","당일배송","산지직송","직송","배송","박스","kg","1kg","2kg",
              "3kg","5kg","10kg","대용량","소포장","실속","프리미엄","명절","추석","설"]
BUY_CAT = {
    "과일/농산물": ["송이","알","브릭스","당도","제철","가정용","못난이","정품","특상","특대"],
    "축산물": ["1++","1+","등급","구이용","국거리","불고기용","냉장","냉동","무항생제","등심","안심"],
    "수산물": ["손질","냉동","급냉","생물","활","자연산","양식","국산","횟감","조림용","반건조","진공"],
}
INFO_WORDS = ["효능","효과","보관","칼로리","키우","재배","묘목","레시피","요리","먹는법",
              "뜻","영어","유래","종류","차이","시세","도매","경매","농사","나무","꽃","씨앗","수확시기"]

def normalize(s):
    return s.replace(" ", "").replace("머스켓", "머스캣")

def get_parent_terms(product):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": N_CLIENT_ID, "X-Naver-Client-Secret": N_CLIENT_SECRET}
    params = {"query": product, "display": 20, "sort": "sim"}
    terms, big_cat = set(), "기타"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        items = r.json().get("items", [])
        for it in items:
            cats = [it.get("category1"), it.get("category2"), it.get("category3"), it.get("category4")]
            joined = " ".join([str(c) for c in cats if c])
            for key, val in CATEGORY_MAP.items():
                if key in joined:
                    big_cat = val
            c4 = it.get("category4")
            if c4 and c4 not in TOO_BROAD:
                terms.add(c4)
            elif not c4:
                c3 = it.get("category3")
                if c3 and c3 not in TOO_BROAD:
                    terms.add(c3)
    except Exception as e:
        st.warning(f"쇼핑 카테고리 조회 실패({product}): {e}")
    return [t for t in terms if t not in TOO_BROAD], big_cat

def naver_related_keywords(seed):
    base, uri = "https://api.searchad.naver.com", "/keywordstool"
    ts = str(round(time.time()*1000))
    sig = base64.b64encode(hmac.new(SECRET.encode(), f"{ts}.GET.{uri}".encode(), hashlib.sha256).digest()).decode()
    headers = {"X-Timestamp": ts, "X-API-KEY": API_KEY, "X-Customer": str(CUSTOMER_ID), "X-Signature": sig}
    try:
        r = requests.get(base+uri, params={"hintKeywords": seed, "showDetail": 1}, headers=headers, timeout=10)
        rows = r.json().get("keywordList", [])
    except Exception:
        return pd.DataFrame(columns=["키워드","검색량"])
    out = []
    for k in rows:
        def n(v):
            v = str(v).replace("<","").replace(",","").strip()
            return int(v) if v.isdigit() else 0
        out.append({"키워드": k["relKeyword"], "검색량": n(k["monthlyPcQcCnt"]) + n(k["monthlyMobileQcCnt"])})
    return pd.DataFrame(out)

# ---------- 상태 ----------
if "selected" not in st.session_state:
    st.session_state.selected = []
if "limit_hit" not in st.session_state:
    st.session_state.limit_hit = False

def toggle_keyword(kw):
    if kw in st.session_state.selected:
        st.session_state.selected.remove(kw)
        st.session_state.limit_hit = False
        return
    if len(st.session_state.selected) >= MAX_KEYWORDS:
        st.session_state.limit_hit = True
        return
    st.session_state.selected.append(kw)
    st.session_state.limit_hit = False

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
        all_kw = all_kw[all_kw["키워드"].apply(is_related)].copy()
        all_kw = all_kw[~all_kw["키워드"].str.contains("|".join(INFO_WORDS))].copy()
        all_kw = all_kw[all_kw["검색량"] >= MIN_VOL].copy()
        iw = list(intent_words)
        all_kw["구매의도"] = all_kw["키워드"].apply(lambda k: sum(1 for w in iw if w in k))
        all_kw["상품직결"] = all_kw["키워드"].apply(lambda k: 1 if any(t in normalize(k) for t in norm_products) else 0)
        all_kw["구매전환추정점수"] = (
            all_kw["상품직결"] * 0.4 +
            all_kw["검색량"].rank(pct=True) * 0.35 +
            all_kw["구매의도"].rank(pct=True) * 0.25
        ).round(3)
        result = all_kw.sort_values(["상품직결", "구매전환추정점수"], ascending=[False, False]).head(st.session_state.get("top_n", 40))
        st.session_state.results = result[["키워드","검색량","구매의도","구매전환추정점수"]].values.tolist()
    else:
        st.session_state.results = []

# ---------- CSS ----------
st.markdown("""
<style>
/* Streamlit 기본 헤더/툴바 제거 → 상단 여백 제거 */
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0.5rem !important; margin-top: 0 !important; }
[data-testid="stAppViewBlockContainer"] { padding-top: 0.5rem !important; }

/* ===== 상단 고정바 (검색 + 복사용 키워드) ===== */
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) {
    position: sticky; top: 0; z-index: 999;
    background: linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%);
    padding: 10px 16px 12px 16px;
    border: 1px solid #e6e8eb;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
    margin-bottom: 10px;
}
div.topbar-anchor { height: 0 !important; margin: 0 !important; padding: 0 !important; }
.bar-title { font-size: 18px; font-weight: 800; color: #263238; margin-bottom: 6px; }
.copy-title { font-size: 14px; font-weight: 700; color: #37474f; margin-top: 6px; }

/* 상단바 추출 버튼 세로 정렬 */
div[data-testid="stVerticalBlock"]:has(div.topbar-anchor) div[data-testid="column"]:nth-of-type(3) .stButton {
    margin-top: 28px !important;
}

/* ===== 결과 키워드 버튼 박스 ===== */
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button {
    padding: 11px 15px !important;
    min-height: 52px !important;
    border-radius: 16px !important;
    border: 1.5px solid #e6e8eb !important;
    background: #ffffff !important;
    text-align: left !important;
    transition: all .15s ease !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button p,
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button div,
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button span {
    font-size: 20px !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-row) .stButton button:hover {
    border-color: #ff7043 !important;
    box-shadow: 0 5px 16px rgba(255,112,67,0.20) !important;
    transform: translateY(-1px) !important;
}
/* 담긴 상태 강조 */
div[data-testid="stHorizontalBlock"]:has(.kw-picked) .stButton button {
    background: #eef6ff !important;
    border-color: #4a90d9 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-picked) .stButton button p {
    color: #2f6fb3 !important;
}

/* 결과 버튼 행 사이 세로 간격 축소 */
div[data-testid="stVerticalBlock"]:has(.kw-row) { gap: 0.3rem !important; }
div[data-testid="stHorizontalBlock"]:has(.kw-row) { margin-bottom: 0 !important; }

/* 검색량·점수 수치 */
div[data-testid="stHorizontalBlock"]:has(.kw-row) { align-items: center !important; }
.metric-val {
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #607d8b !important;
    text-align: center !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- 상단 고정바 : 검색 + 복사용 키워드 ----------
with st.container():
    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="bar-title">🛒 쿠팡키워드 추출기</div>', unsafe_allow_html=True)

    ta, tb, tc = st.columns([3, 1.4, 1.2])
    ta.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣",
                  key="raw_input", on_change=run_extract)
    tb.slider("키워드 개수", 10, 50, 40, key="top_n")
    tc.button("🔍 추출하기", use_container_width=True, on_click=run_extract, type="primary")

    st.markdown(f'<div class="copy-title">📋 복사용 키워드 ({len(st.session_state.selected)}개)</div>',
                unsafe_allow_html=True)
    if st.session_state.selected:
        st.code(",".join(st.session_state.selected) + ",", language=None)
    else:
        st.code(" ", language=None)

    if st.session_state.limit_hit:
        st.error(f"최대 {MAX_KEYWORDS}개까지만 담을 수 있어요!")

# ---------- 결과 표시 ----------
if st.session_state.get("results"):
    st.info("자동 인식된 상위어: " + st.session_state.get("related_info",""))
    st.subheader("추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)")
    for i, (kw, vol, intent, score) in enumerate(st.session_state.results):
        c1, cgap, c2, c3 = st.columns([2.1, 0.9, 1.4, 1.2])
        already = kw in st.session_state.selected
        marker = "kw-row kw-picked" if already else "kw-row"
        c1.markdown(f"<div class='{marker}'></div>", unsafe_allow_html=True)
        label = f"✔ {kw}" if already else kw
        c1.button(label, key=f"pick_{i}", on_click=toggle_keyword, args=(kw,),
                  use_container_width=True)
        c2.markdown(f"<div class='metric-val'>{vol:,}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-val'>{score}</div>", unsafe_allow_html=True)
elif "results" in st.session_state:
    st.warning("수집된 키워드가 없습니다. 상품명이나 개수를 조정해 보세요.")
