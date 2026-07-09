import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

API_KEY     = st.secrets["API_KEY"]
SECRET      = st.secrets["SECRET"]
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]

CATEGORY_HINTS = {
    "과일": ["사과","딸기","감귤","귤","포도","샤인","머스캣","머스켓","배","복숭아",
            "수박","참외","자두","체리","블루베리","망고","키위","감","토마토","무화과",
            "한라봉","천혜향","멜론","앵두","살구","석류","과일"],
    "축산": ["한우","소고기","돼지","삼겹","목살","항정","닭","계란","오리","한돈",
            "정육","갈비","불고기","스테이크","우유","양고기","곱창","막창","차돌"],
    "수산": ["갈치","고등어","새우","오징어","굴","전복","연어","조기","광어","우럭",
            "문어","낙지","주꾸미","김","미역","다시마","건어물","생선","해물","젓갈",
            "명란","멸치","가리비","홍합","바지락","대게","킹크랩","랍스터","장어","아귀"],
}

def guess_category(kw):
    for cat, words in CATEGORY_HINTS.items():
        if any(w in kw for w in words):
            return cat
    return "기타"

BUY_COMMON = ["선물","선물세트","세트","가격","특가","할인","최저가","주문","구매",
              "택배","당일","당일배송","산지직송","직송","배송","박스","1박스","kg",
              "1kg","2kg","3kg","5kg","10kg","대용량","소포장","실속","프리미엄","명절",
              "추석","설","설날","제수용","차례","성묘"]

BUY_BY_CAT = {
    "과일": ["송이","알","브릭스","당도","생과일","제철","가정용","못난이","흠집",
            "정품","특상","특대","왕대","한알","냉장","GAP"],
    "축산": ["1++","1+","등급","한근","600g","300g","구이용","국거리","불고기용",
            "찜용","냉장","냉동","급냉","무항생제","암소","살치","등심","안심","채끝",
            "부채살","우삼겹","수육용","훈제"],
    "수산": ["손질","손질완료","냉동","급냉","생물","활","활어","자연산","양식","국산",
            "제철","횟감","구이용","조림용","탕용","무염","반건조","진공","특대","왕"],
}

INFO_WORDS = ["효능","효과","보관","보관법","칼로리","키우","재배","묘목","모종",
              "레시피","요리","먹는법","손질법","뜻","영어","유래","종류","차이",
              "가격동향","시세","도매","경매","농사","양식장","축제","축제일정",
              "나무","꽃","씨앗","파종","수확시기"]

def build_intent_words(products):
    words = set(BUY_COMMON)
    for p in products:
        words |= set(BUY_BY_CAT.get(guess_category(p), []))
    return list(words)

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
    except Exception as e:
        return pd.DataFrame(columns=["키워드","검색량"])
    out=[]
    for k in rows:
        def n(v):
            v=str(v).replace("<","").replace(",","").strip()
            return int(v) if v.isdigit() else 0
        out.append({"키워드":k["relKeyword"],
                    "검색량":n(k["monthlyPcQcCnt"])+n(k["monthlyMobileQcCnt"])})
    return pd.DataFrame(out)

st.title("농축수산물 구매전환 키워드 추출기")
st.write("상품명을 입력하면 관련된 '구매 의도 높은' 키워드를 뽑아드려요.")

raw = st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스캣")
top_n = st.slider("추출할 키워드 개수", 10, 50, 30)   # 기본 30개
min_vol = st.slider("최소 검색량", 0, 200, 10)         # 기본 10으로 완화

if st.button("추출하기"):
    products = raw.split()
    intent_words = build_intent_words(products)

    # ── 씨앗 자동 확장: 상품명 + (상품명+구매의도 조합) 을 함께 던져 후보 늘리기 ──
    seed_list = list(products)
    for p in products:
        for w in ["선물세트","가격","산지직송","kg","특가"]:
            seed_list.append(f"{p} {w}")

    frames=[]
    with st.spinner("수집 중... (씨앗을 여러 개 던져서 시간이 조금 걸려요)"):
        for s in seed_list:
            df = naver_related_keywords(s)
            frames.append(df); time.sleep(0.25)

    if frames and not all(f.empty for f in frames):
        all_kw = pd.concat(frames, ignore_index=True).drop_duplicates("키워드")

        # 입력 상품명이 포함된 키워드만
        mask = all_kw.apply(
            lambda r: any(p.replace(" ","") in r["키워드"].replace(" ","")
                          for p in products), axis=1)
        all_kw = all_kw[mask].copy()

        # 정보성 제외
        all_kw = all_kw[~all_kw["키워드"].str.contains("|".join(INFO_WORDS))].copy()

        # 검색량 기준 완화
        all_kw = all_kw[all_kw["검색량"]>=min_vol].copy()
        all_kw["카테고리"] = all_kw["키워드"].apply(guess_category)

        def intent_score(kw):
            return sum(1 for w in intent_words if w in kw)
        all_kw["구매의도"] = all_kw["키워드"].apply(intent_score)

        all_kw["구매전환추정점수"] = (
            all_kw["검색량"].rank(pct=True) * 0.5 +
            all_kw["구매의도"].rank(pct=True) * 0.5
        ).round(3)

        # 상위 N개만 자르기
        result = all_kw.sort_values("구매전환추정점수", ascending=False).head(top_n)

        st.success(f"완료! '{raw}' 관련 키워드 {len(result)}개 (요청: {top_n}개)")
        st.dataframe(result[["키워드","카테고리","검색량","구매의도","구매전환추정점수"]])
        st.download_button("CSV 다운로드",
            result.to_csv(index=False).encode("utf-8-sig"),
            "연관키워드_결과.csv", "text/csv")
    else:
        st.error("수집된 키워드가 없습니다. API 키를 확인하세요.")
