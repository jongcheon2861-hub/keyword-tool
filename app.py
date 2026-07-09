import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

# ============================================================
# API 키 (Streamlit Secrets에서 읽어옴)
# ============================================================
API_KEY     = st.secrets["API_KEY"]              # 검색광고 액세스라이선스
SECRET      = st.secrets["SECRET"]               # 검색광고 비밀키
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]          # 검색광고 고객ID
N_CLIENT_ID     = st.secrets["NAVER_CLIENT_ID"]      # 쇼핑검색 Client ID
N_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]  # 쇼핑검색 Client Secret

# ============================================================
# 상위어로 쓰기엔 너무 넓은 대분류 (제외 대상)
# ============================================================
TOO_BROAD = ["식품","농산물","축산물","수산물","과일","채소","정육","건어물",
             "가공식품","신선식품","farm","food"]

# 대분류 판정용 (구매의도 단어 세트 선택에 사용)
CATEGORY_MAP = {
    "과일":"과일/농산물","농산물":"과일/농산물","채소":"과일/농산물",
    "축산":"축산물","정육":"축산물","계란":"축산물",
    "수산":"수산물","건어물":"수산물","젓갈":"수산물",
}

# ============================================================
# 구매 의도 단어 (공통 + 카테고리별)
# ============================================================
BUY_COMMON = ["선물","선물세트","세트","가격","특가","할인","최저가","주문","구매",
              "택배","당일","당일배송","산지직송","직송","배송","박스","kg","1kg","2kg",
              "3kg","5kg","10kg","대용량","소포장","실속","프리미엄","명절","추석","설"]
BUY_CAT = {
    "과일/농산물": ["송이","알","브릭스","당도","제철","가정용","못난이","정품","특상","특대"],
    "축산물": ["1++","1+","등급","구이용","국거리","불고기용","냉장","냉동","무항생제","등심","안심"],
    "수산물": ["손질","냉동","급냉","생물","활","자연산","양식","국산","횟감","조림용","반건조","진공"],
}

# 전환과 거리가 먼 정보성 단어 (제외)
INFO_WORDS = ["효능","효과","보관","칼로리","키우","재배","묘목","레시피","요리","먹는법",
              "뜻","영어","유래","종류","차이","시세","도매","경매","농사","나무","꽃","씨앗","수확시기"]

def normalize(s):
    """비교용 정규화: 공백 제거 + 켓/캣 통일"""
    return s.replace(" ", "").replace("머스켓", "머스캣")

# ============================================================
# 네이버 쇼핑 검색 → 카테고리 경로에서 상위어 자동 추출
#   category4(가장 세부) 한 단계만 채택. 대분류는 제외.
# ============================================================
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

            # 핵심: category4(가장 하위)만 상위어로 채택
            c4 = it.get("category4")
            if c4 and c4 not in TOO_BROAD:
                terms.add(c4)
            elif not c4:               # category4가 없으면 category3로 대체
                c3 = it.get("category3")
                if c3 and c3 not in TOO_BROAD:
                    terms.add(c3)
    except Exception as e:
        st.warning(f"쇼핑 카테고리 조회 실패({product}): {e}")
    terms = {t for t in terms if t not in TOO_BROAD}
    return list(terms), big_cat

# ============================================================
# 네이버 검색광고 키워드도구 → 연관 키워드 + 검색량
# ============================================================
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

# ============================================================
# 웹 화면
# ============================================================
st.title("농축수산물 구매전환 키워드 추출기")
st.write("상품명을 입력하면 네이버 쇼핑 카테고리에서 상위어를 자동으로 찾아 관련 키워드를 뽑아요.")

raw = st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣")
top_n = st.slider("추출할 키워드 개수", 10, 50, 30)
min_vol = st.slider("최소 검색량", 0, 200, 10)

if st.button("추출하기"):
    products = raw.split()
    norm_products = [normalize(p) for p in products]

    # 1) 각 상품의 상위어(category4) 자동 추출
    related_terms, intent_words = set(), set(BUY_COMMON)
    with st.spinner("상위 카테고리 분석 중..."):
        for p in products:
            terms, big = get_parent_terms(p)
            related_terms |= set(terms)
            intent_words |= set(BUY_CAT.get(big, []))
    st.info("자동 인식된 상위어: " + (", ".join(sorted(related_terms)) or "없음"))

    # 2) 상품 + 상위어를 씨앗으로 연관 키워드 수집
    seeds = list(dict.fromkeys(list(products) + list(related_terms)))[:12]
    frames=[]
    with st.spinner("연관 키워드 수집 중..."):
        for s in seeds:
            frames.append(naver_related_keywords(s)); time.sleep(0.2)

    if frames and not all(f.empty for f in frames):
        all_kw = pd.concat(frames, ignore_index=True).drop_duplicates("키워드")

        # 3) 상품명 직접 포함 또는 상위어 포함이면 관련 키워드로 인정
        norm_terms = [normalize(t) for t in related_terms]
        def is_related(kw):
            nk = normalize(kw)
            if any(t in nk for t in norm_products): return True
            if any(t in nk for t in norm_terms):    return True
            return False
        all_kw = all_kw[all_kw["키워드"].apply(is_related)].copy()

        # 4) 정보성 제외 + 검색량 필터
        all_kw = all_kw[~all_kw["키워드"].str.contains("|".join(INFO_WORDS))].copy()
        all_kw = all_kw[all_kw["검색량"]>=min_vol].copy()

        # 5) 점수 계산
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
        st.success(f"완료! '{raw}' 관련 키워드 {len(result)}개")
        st.dataframe(result[["키워드","상품직결","검색량","구매의도","구매전환추정점수"]])
        st.download_button("CSV 다운로드",
            result.to_csv(index=False).encode("utf-8-sig"),
            "연관키워드_결과.csv", "text/csv")
    else:
        st.error("수집된 키워드가 없습니다. API 키를 확인하세요.")
