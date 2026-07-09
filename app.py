import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

st.set_page_config(layout="wide")

API_KEY     = st.secrets["API_KEY"]
SECRET      = st.secrets["SECRET"]
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]
N_CLIENT_ID     = st.secrets["NAVER_CLIENT_ID"]
N_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

MAX_KEYWORDS = 20
MIN_VOL = 10  # 최소 검색량 (내부 고정)

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
    headers = {"X-Naver-Client-Id": N_CLIENT_ID,
               "X-Naver-Client-Secret": N_CLIENT_SECRET}
    params = {"query": product, "display": 20, "sort": "sim"}
    terms, big_cat = set(), "기타"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        items = r.json().get("items", [])
        for it in items:
            cats = [it.get("category1"), it.get("category2"),
                    it.get("category3"), it.get("category4")]
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
    terms = {t for t in terms if t not in TOO_BROAD}
    return list(terms), big_cat

def naver_related_keywords(seed):
    base, uri = "https://api.searchad.naver.com", "/keywordstool"
    ts  = str(round(time.time()*1000))
    sig = base64.b64encode(hmac.new(SECRET.encode(),
          f"{ts}.GET.{uri}".encode(), hashlib.sha256).digest()).decode()
    headers = {"X-Timestamp":ts,"X-API-KEY":API_KEY,
               "X-Customer":str(CUSTOMER_ID),"X-Signature":sig}
    try:
        r = requests.get(base+uri, params={"hintKeywords":seed,"showDetail":1},
                         headers=headers, timeout=10)
        rows = r.json().get("keywordList", [])
    except Exception:
        return pd.DataFrame(columns=["키워드","검색량"])
    out=[]
    for k in rows:
        def n(v):
            v=str(v).replace("<","").replace(",","").strip()
            return int(v) if v.isdigit() else 0
        out.append({"키워드":k["relKeyword"],
                    "검색량":n(k["monthlyPcQcCnt"])+n(k["monthlyMobileQcCnt"])})
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

# ---------- sticky 상단바 CSS ----------
st.markdown("""
<style>
div[data-testid="stVerticalBlock"] > div:has(div.topbar-anchor) {
    position: sticky;
    top: 0;
    z-index: 999;
    background-color: #ffffff;
    padding: 8px 6px;
    border-bottom: 2px solid #e0e0e0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

st.title("농축수산물 구매전환 키워드 추출기")

# ============================================================
# 고정 상단바: 담은 키워드 (칩 형태, 클릭하면 삭제)
# ============================================================
with st.container():
    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    top1, top2 = st.columns([6, 1])
    top1.markdown(f"**담은 키워드  {len(st.session_state.selected)} / {MAX_KEYWORDS}**")
    if st.session_state.selected:
        if top2.button("비우기", use_container_width=True):
            st.session_state.selected = []
            st.session_state.limit_hit = False
            st.rerun()

    if st.session_state.selected:
        cols = st.columns(5)   # 한 줄에 5개씩
        for idx, kw in enumerate(list(st.session_state.selected)):
            col = cols[idx % 5]
            col.button(f"{kw}  ✕", key=f"chip_{idx}",
                       on_click=remove_keyword, args=(kw,),
                       use_container_width=True)
        st.caption("키워드를 누르면 삭제돼요.  복사용 ↓")
        st.code(",".join(st.session_state.selected) + ",", language=None)
    else:
        st.caption("아직 담은 키워드가 없어요. 아래에서 '➕ 담기'를 눌러보세요.")

    if st.session_state.limit_hit:
        st.error(f"최대 {MAX_KEYWORDS}개까지만 담을 수 있어요! 위에서 일부를 지운 뒤 추가하세요.")

st.divider()

# ============================================================
# 입력 + 추출
# ============================================================
st.write("상품명을 입력하면 상위어를 자동으로 찾아 관련 키워드를 뽑아요.")
raw = st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣")
top_n = st.slider("추출할 키워드 개수", 10, 50, 40)

if st.button("추출하기"):
    products = raw.split()
    norm_products = [normalize(p) for p in products]
    related_terms, intent_words = set(), set(BUY_COMMON)
    with st.spinner("상위 카테고리 분석 중..."):
        for p in products:
            terms, big = get_parent_terms(p)
            related_terms |= set(terms)
            intent_words |= set(BUY_CAT.get(big, []))
    st.session_state.related_info = ", ".join(sorted(related_terms)) or "없음"

    seeds = list(dict.fromkeys(list(products) + list(related_terms)))[:12]
    frames=[]
    with st.spinner("연관 키워드 수집 중..."):
        for s in seeds:
            frames.append(naver_related_keywords(s)); time.sleep(0.2)

    if frames and not all(f.empty for f in frames):
        all_kw = pd.concat(frames, ignore_index=True).drop_duplicates("키워드")
        norm_terms = [normalize(t) for t in related_terms]
        def is_related(kw):
            nk = normalize(kw)
            return any(t in nk for t in norm_products) or any(t in nk for t in norm_terms)
        all_kw = all_kw[all_kw["키워드"].apply(is_related)].copy()
        all_kw = all_kw[~all_kw["키워드"].str.contains("|".join(INFO_WORDS))].copy()
        all_kw = all_kw[all_kw["검색량"]>=MIN_VOL].copy()
        iw = list(intent_words)
        all_kw["구매의도"] = all_kw["키워드"].apply(lambda k: sum(1 for w in iw if w in k))
        all_kw["상품직결"] = all_kw["키워드"].apply(
            lambda k: 1 if any(t in normalize(k) for t in norm_products) else 0)
        all_kw["구매전환추정점수"] = (
            all_kw["상품직결"] * 0.4 +
            all_kw["검색량"].rank(pct=True) * 0.35 +
            all_kw["구매의도"].rank(pct=True) * 0.25
        ).round(3)
        result = all_kw.sort_values("구매전환추정점수", ascending=False).head(top_n)
        st.session_state.results = result[
            ["키워드","검색량","구매의도","구매전환추정점수"]].values.tolist()
    else:
        st.session_state.results = []
        st.error("수집된 키워드가 없습니다.")

# ============================================================
# 추출 결과 + ➕ 담기 버튼
# ============================================================
if st.session_state.get("results"):
    st.info("자동 인식된 상위어: " + st.session_state.get("related_info",""))
    st.subheader("추출된 키워드")
    h1, h2, h3, h4 = st.columns([1.4, 4, 2, 2])
    h1.markdown("**담기**"); h2.markdown("**키워드**")
    h3.markdown("**검색량**"); h4.markdown("**점수**")
    for i, (kw, vol, intent, score) in enumerate(st.session_state.results):
        c1, c2, c3, c4 = st.columns([1.4, 4, 2, 2])
        already = kw in st.session_state.selected
        c1.button("담김" if already else "➕ 담기",
                  key=f"add_{i}", on_click=add_keyword, args=(kw,),
                  disabled=already, use_container_width=True)
        c2.write(kw); c3.write(f"{vol:,}"); c4.write(f"{score}")
