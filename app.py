import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

st.set_page_config(page_title="쿠팡키워드 추출기", layout="centered", initial_sidebar_state="expanded")

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

def add_keyword(kw):
    if kw in st.session_state.selected:
        return
    if len(st.session_state.selected) >= MAX_KEYWORDS:
        st.session_state.limit_hit = True
        return
    st.session_state.selected.append(kw)
    st.session_state.limit_hit = False

def remove_keyword(kw):
    if kw in st.session_state.selected:
        st.session_state.selected.remove(kw)
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

# ---------- CSS (:has() 미사용, 전역 선택자 기반) ----------
st.markdown("""
<style>
/* Streamlit 기본 헤더/툴바 제거 → 상단 여백 제거 */
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0.5rem !important; margin-top: 0 !important; }
[data-testid="stAppViewBlockContainer"] { padding-top: 0.5rem !important; }
section.main > div { padding-top: 0 !important; }

/* 복사용 키워드 바 (직접 클래스로 스타일 지정 → 깨진 블록 없음) */
.copybar {
    position: sticky; top: 0; z-index: 999;
    background: linear-gradient(180deg,#ffffff 0%,#fafbfc 100%);
    padding: 8px 14px;
    border-bottom: 1px solid #e6e8eb;
    box-shadow: 0 3px 10px rgba(0,0,0,0.06);
    border-radius: 0 0 12px 12px;
    margin-bottom: 8px;
}
.copybar-title { font-size: 15px; font-weight: 700; color: #37474f; margin-bottom: 4px; }

/* 결과 영역 키워드 버튼 = 전역 메인 버튼 대상. 사이드바는 아래에서 덮어씀 */
section.main .stButton button {
    padding: 14px 20px !important;
    font-size: 40px !important;
    font-weight: 800 !important;
    min-height: 0 !important;
    line-height: 1.2 !important;
    border-radius: 14px !important;
    border: 1.5px solid #e6e8eb !important;
    background: #ffffff !important;
    text-align: left !important;
    transition: all .15s ease !important;
}
section.main .stButton button:hover {
    border-color: #ff7043 !important;
    box-shadow: 0 4px 12px rgba(255,112,67,0.18) !important;
    transform: translateY(-1px) !important;
}
section.main .stButton button:disabled {
    background: #f1f3f5 !important;
    color: #9aa0a6 !important;
}

/* 검색량·점수 수치 : 버튼과 같은 높이로 세로 중앙 정렬 + 가려짐 방지 */
section.main div[data-testid="stHorizontalBlock"] { align-items: center !important; }
.metric-val {
    font-size: 34px !important;
    font-weight: 800 !important;
    color: #455a64 !important;
    line-height: 1.2 !important;
    text-align: center !important;
    display: flex; align-items: center; justify-content: center;
    min-height: 60px;
}
.metric-head {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #90a4ae !important;
    letter-spacing: .3px;
    text-align: center;
}

/* 사이드바 키워드 칩 : 33% 크기(한 줄 3개), 글씨 작게 */
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] .stButton button {
    padding: 3px 4px !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    min-height: 0 !important;
    line-height: 1.15 !important;
    border-radius: 8px !important;
    border: 1px solid #dfe3e8 !important;
    background: #ffffff !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    text-align: center !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] .stButton button:hover {
    border-color: #ff7043 !important;
    color: #ff5722 !important;
}
/* 사이드바 일반 버튼(추출하기/전체비우기)는 기본 크기 유지 */
section[data-testid="stSidebar"] > div > div > div > .stButton button {
    font-size: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- 사이드바 : 검색 + 담은 키워드 ----------
with st.sidebar:
    st.header("🛒 쿠팡키워드 추출기")
    st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣", key="raw_input", on_change=run_extract)
    st.slider("추출할 키워드 개수", 10, 50, 40, key="top_n")
    st.button("🔍 추출하기", use_container_width=True, on_click=run_extract, type="primary")

    st.divider()
    st.markdown(f"**담은 키워드  {len(st.session_state.selected)} / {MAX_KEYWORDS}**")
    if st.session_state.selected:
        if st.button("전체 비우기", use_container_width=True):
            st.session_state.selected = []
            st.session_state.limit_hit = False
            st.rerun()
        st.caption("키워드를 누르면 삭제돼요.")
        kws = list(st.session_state.selected)
        for start in range(0, len(kws), 3):     # 한 줄에 3개
            row = kws[start:start+3]
            cols = st.columns(3)
            for col, kw in zip(cols, row):
                col.button(f"{kw} ✕", key=f"chip_{start}_{kw}",
                           on_click=remove_keyword, args=(kw,), use_container_width=True)
    else:
        st.caption("아직 담은 키워드가 없어요.\n오른쪽에서 키워드를 눌러 담아보세요.")
    if st.session_state.limit_hit:
        st.error(f"최대 {MAX_KEYWORDS}개까지만 담을 수 있어요!")

# ---------- 상단 복사용 키워드 바 (페이지 최상단 요소) ----------
st.markdown('<div class="copybar">'
            f'<div class="copybar-title">📋 복사용 키워드 ({len(st.session_state.selected)}개)</div>'
            '</div>', unsafe_allow_html=True)
if st.session_state.selected:
    st.code(",".join(st.session_state.selected) + ",", language=None)
else:
    st.code(" ", language=None)

# ---------- 결과 표시 ----------
if st.session_state.get("results"):
    st.info("자동 인식된 상위어: " + st.session_state.get("related_info",""))
    st.subheader("추출된 키워드 · 클릭하면 담겨요 (관련도 높은 순)")
    h1, h2, h3 = st.columns([3, 1.4, 1.2])
    h1.markdown("<div class='metric-head' style='text-align:left'>키워드</div>", unsafe_allow_html=True)
    h2.markdown("<div class='metric-head'>검색량</div>", unsafe_allow_html=True)
    h3.markdown("<div class='metric-head'>점수</div>", unsafe_allow_html=True)
    for i, (kw, vol, intent, score) in enumerate(st.session_state.results):
        c1, c2, c3 = st.columns([3, 1.4, 1.2])
        already = kw in st.session_state.selected
        label = f"✔ {kw}" if already else kw
        c1.button(label, key=f"pick_{i}", on_click=add_keyword, args=(kw,),
                  disabled=already, use_container_width=True)
        c2.markdown(f"<div class='metric-val'>{vol:,}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-val'>{score}</div>", unsafe_allow_html=True)
elif "results" in st.session_state:
    st.warning("수집된 키워드가 없습니다. 상품명이나 개수를 조정해 보세요.")
