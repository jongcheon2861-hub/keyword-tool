import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64

API_KEY     = st.secrets["API_KEY"]
SECRET      = st.secrets["SECRET"]
CUSTOMER_ID = st.secrets["CUSTOMER_ID"]

CATEGORY_HINTS = {
    "과일": ["사과","딸기","감귤","귤","포도","배","복숭아","머스캣","수박","참외","토마토","과일"],
    "축산": ["한우","소고기","돼지","삼겹","닭","계란","오리","한돈","정육","갈비"],
    "수산": ["갈치","고등어","새우","오징어","굴","전복","연어","김","건어물","생선","해물"],
}

def guess_category(kw):
    for cat, words in CATEGORY_HINTS.items():
        if any(w in kw for w in words):
            return cat
    return "기타"

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
        st.warning(f"'{seed}' 수집 실패: {e}")
        return pd.DataFrame(columns=["키워드","검색량"])
    out=[]
    for k in rows:
        def n(v):
            v=str(v).replace("<","").replace(",","").strip()
            return int(v) if v.isdigit() else 0
        out.append({"키워드":k["relKeyword"],
                    "검색량":n(k["monthlyPcQcCnt"])+n(k["monthlyMobileQcCnt"])})
    return pd.DataFrame(out)

st.title("농축수산물 연관 키워드 추출기")
st.write("상품명을 입력하면 연관 키워드와 구매신호 점수를 뽑아드려요.")

raw = st.text_input("상품명 (여러 개는 띄어쓰기)", "사과 한우 갈치")

if st.button("추출하기"):
    products = raw.split()
    frames=[]
    with st.spinner("수집 중..."):
        for p in products:
            df = naver_related_keywords(p); df["입력상품"]=p
            frames.append(df); time.sleep(0.3)
    if frames and not all(f.empty for f in frames):
        all_kw = pd.concat(frames, ignore_index=True).drop_duplicates("키워드")
        all_kw["카테고리"] = all_kw["키워드"].apply(guess_category)
        all_kw = all_kw[all_kw["검색량"]>=100].copy()
        all_kw["구매신호점수"] = all_kw["검색량"].rank(pct=True).round(3)
        result = all_kw.sort_values("구매신호점수", ascending=False)
        st.success(f"완료! 키워드 {len(result)}개 추출")
        st.dataframe(result[["키워드","카테고리","검색량","구매신호점수"]])
        st.download_button("엑셀(CSV) 다운로드",
            result.to_csv(index=False).encode("utf-8-sig"),
            "연관키워드_결과.csv", "text/csv")
    else:
        st.error("수집된 키워드가 없습니다. API 키를 확인하세요.")
