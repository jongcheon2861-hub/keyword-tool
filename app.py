import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64
import json, math
import streamlit.components.v1 as components

st.set_page_config(page_title="쿠팡 셀러 도구", layout="wide",
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
    "사과": ["사과", "부사", "홍로", "아오리"],
    "배": ["배", "신고배"],
    "감귤": ["감귤", "귤", "한라봉", "천혜향", "레드향", "만감류", "황금향"],
    "오렌지": ["오렌지", "네이블"],
    "포도": ["포도", "샤인머스캣", "샤인머스켓", "캠벨포도", "거봉", "청포도", "머스캣", "델라웨어", "머루"],
    "딸기": ["딸기", "설향"],
    "블루베리": ["블루베리"],
    "체리": ["체리"],
    "복숭아": ["복숭아", "천도복숭아", "백도", "황도"],
    "자두": ["자두", "후무사", "대석", "플럼"],
    "매실": ["매실"],
    "수박": ["수박"],
    "참외": ["참외"],
    "멜론": ["멜론", "머스크멜론"],
    "감": ["감", "단감", "홍시", "곶감", "대봉"],
    "석류": ["석류"],
    "무화과": ["무화과"],
    "키위": ["키위", "참다래"],
    "레몬": ["레몬", "라임"],
    "바나나": ["바나나"],
    "파인애플": ["파인애플"],
    "망고": ["망고", "애플망고"],
    "아보카도": ["아보카도"],
    "자몽": ["자몽"],
    "배추": ["배추", "알배기"],
    "양배추": ["양배추", "적양배추"],
    "상추": ["상추", "양상추", "쌈채소"],
    "시금치": ["시금치"],
    "미나리": ["미나리"],
    "부추": ["부추"],
    "깻잎": ["깻잎"],
    "무": ["무", "총각무", "알타리"],
    "당근": ["당근"],
    "우엉": ["우엉"],
    "연근": ["연근"],
    "도라지": ["도라지"],
    "더덕": ["더덕"],
    "감자": ["감자"],
    "고구마": ["고구마", "꿀고구마", "밤고구마", "호박고구마"],
    "호박": ["호박", "단호박", "밤호박", "애호박"],
    "오이": ["오이"],
    "고추": ["고추", "청양고추", "풋고추"],
    "파프리카": ["파프리카", "피망"],
    "가지": ["가지"],
    "양파": ["양파", "적양파"],
    "대파": ["대파", "쪽파", "실파"],
    "마늘": ["마늘", "깐마늘", "다진마늘"],
    "생강": ["생강"],
    "버섯": ["버섯", "표고", "느타리", "새송이", "팽이", "양송이"],
    "콩나물": ["콩나물", "숙주"],
    "두부": ["두부"],
    "브로콜리": ["브로콜리"],
    "아스파라거스": ["아스파라거스"],
    "옥수수": ["옥수수", "초당옥수수"],
    "쌀": ["쌀", "백미", "현미", "찹쌀"],
    "잡곡": ["잡곡", "보리", "귀리", "콩", "팥", "녹두", "수수", "기장", "율무", "혼합곡"],
    "소고기": ["소고기", "쇠고기", "한우", "육우", "채끝", "안심", "등심", "차돌박이", "양지", "사태", "우삼겹"],
    "소갈비": ["소갈비", "엘에이갈비", "la갈비"],
    "삼겹살": ["삼겹살", "생삼겹", "냉동삼겹"],
    "목살": ["목살"],
    "돼지고기": ["돼지고기", "돈육", "앞다리", "뒷다리", "항정살", "갈매기살", "돼지불고기"],
    "닭고기": ["닭고기", "생닭", "닭가슴살", "닭다리", "닭날개", "닭발", "근위", "삼계", "백숙"],
    "오리고기": ["오리고기", "생오리", "오리훈제", "오리주물럭"],
    "양고기": ["양고기", "양갈비", "양꼬치"],
    "계란": ["계란", "달걀", "구운계란", "훈제계란", "무정란", "유정란"],
    "메추리알": ["메추리알"],
    "갈치": ["갈치"],
    "고등어": ["고등어"],
    "삼치": ["삼치"],
    "꽁치": ["꽁치"],
    "임연수": ["임연수"],
    "가자미": ["가자미"],
    "우럭": ["우럭"],
    "대구": ["대구"],
    "명태": ["명태", "동태", "황태", "코다리", "북어", "노가리"],
    "조기": ["조기", "굴비"],
    "옥돔": ["옥돔"],
    "홍어": ["홍어"],
    "참치": ["참치"],
    "연어": ["연어", "훈제연어"],
    "장어": ["장어", "바다장어", "붕장어", "민물장어", "먹장어", "갯장어", "아나고", "하모"],
    "생선회": ["생선회", "회"],
    "오징어": ["오징어", "건오징어", "물오징어"],
    "낙지": ["낙지"],
    "문어": ["문어"],
    "주꾸미": ["주꾸미", "쭈꾸미"],
    "한치": ["한치"],
    "새우": ["새우", "대하", "흰다리새우"],
    "꽃게": ["꽃게"],
    "대게": ["대게", "홍게"],
    "킹크랩": ["킹크랩"],
    "랍스터": ["랍스터", "바닷가재", "가재"],
    "조개": ["조개", "바지락", "꼬막", "홍합", "가리비"],
    "전복": ["전복"],
    "굴": ["굴"],
    "소라": ["소라", "골뱅이"],
    "멍게": ["멍게", "해삼", "성게알"],
    "김": ["김", "조미김", "돌김"],
    "미역": ["미역"],
    "다시마": ["다시마"],
    "매생이": ["매생이"],
    "멸치": ["멸치", "다시멸치"],
    "쥐포": ["쥐포"],
    "건새우": ["건새우"],
    "과메기": ["과메기"],
    "진미채": ["진미채"],
    "명란젓": ["명란젓", "명란"],
    "새우젓": ["새우젓"],
    "게장": ["게장", "간장게장", "양념게장", "대하장"],
    "젓갈": ["젓갈", "오징어젓", "낙지젓", "조개젓", "창난젓", "토하젓"],
    "족발": ["족발", "보쌈"],
    "돈가스": ["돈가스"],
    "떡갈비": ["떡갈비"],
    "베이컨": ["베이컨"],
    "햄": ["햄", "소시지"],
    "육포": ["육포"],
    "삼계탕": ["삼계탕"],
    "곱창": ["곱창", "막창", "대창"],
}

BUY_COMMON = ["구매", "주문", "배송", "택배", "가격", "최저가", "특가", "무료배송", "당일배송", "로켓배송", "정품"]
BUY_CAT = {}
INFO_WORDS = ["효능", "칼로리", "방법", "레시피", "뜻", "의미", "부작용", "후기만", "나무위키"]

# ---------- 키워드 추출 함수 ----------
def normalize(s):
    return s.replace(" ", "").replace("머스켓", "머스캣")

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
            return pd.DataFrame(columns=["키워드", "검색량", "경쟁강도"])
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
            comp = it.get("compIdx", "-")
            rows.append({"키워드": it.get("relKeyword", ""), "검색량": vol, "경쟁강도": comp})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["키워드", "검색량", "경쟁강도"])

def find_category_in_text(text):
    nt = normalize(text)
    for cat, members in CATEGORY_MAP.items():
        if any(normalize(m) in nt or nt in normalize(m) for m in members):
            return cat
    return ""

def get_parent_and_related(product):
    base_df = naver_related_keywords(product)
    big = find_category_in_text(product)
    if not big and not base_df.empty:
        rel_kws = [normalize(k) for k in base_df["키워드"].tolist()]
        best_cat, best_hit = "", 0
        for cat, members in CATEGORY_MAP.items():
            hit = 0
            for m in members:
                nm = normalize(m)
                hit += sum(1 for rk in rel_kws if nm in rk)
            hit += sum(2 for rk in rel_kws if normalize(cat) in rk)
            if hit > best_hit:
                best_hit, best_cat = hit, cat
        big = best_cat
    return big, base_df

# ---------- 상태 ----------
if "selected" not in st.session_state:
    st.session_state.selected = []
if "popup" not in st.session_state:
    st.session_state.popup = None
if "popup_id" not in st.session_state:
    st.session_state.popup_id = 0
if "mc_product" not in st.session_state:
    st.session_state.mc_product = ""
if "mc_rows" not in st.session_state:
    st.session_state.mc_rows = [
        {"opt": "", "supply": 0, "ship": 0, "disc": 60.0, "fee": 12.0, "margin": 20.0}
    ]
if "mc_sent" not in st.session_state:
    st.session_state.mc_sent = []  # 가이드로 넘긴 계산 결과
if "mc_mgmt_name" not in st.session_state:
    st.session_state.mc_mgmt_name = ""
if "mc_mgmt_sent" not in st.session_state:
    st.session_state.mc_mgmt_sent = ""
if "mc_fixed_coupon" not in st.session_state:
    st.session_state.mc_fixed_coupon = None

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
    related_terms = set()
    intent_words = set(BUY_COMMON)
    frames = []
    seen_seeds = set()
    for p in products:
        big, base_df = get_parent_and_related(p)
        if not base_df.empty:
            frames.append(base_df)
        seen_seeds.add(normalize(p))
        if big:
            related_terms.add(big)
            intent_words |= set(BUY_CAT.get(big, []))
    st.session_state.related_info = ", ".join(sorted(related_terms)) or "없음"
    for t in related_terms:
        if normalize(t) in seen_seeds:
            continue
        frames.append(naver_related_keywords(t))
        seen_seeds.add(normalize(t))
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
            ["키워드", "검색량", "경쟁강도", "구매전환추정점수"]].values.tolist()
    else:
        st.session_state.results = []

# ---------- 마진 계산 ----------
def calc_margin(supply, ship, disc, fee, margin, fixed_coupon=None):
    if not supply or supply <= 0:
        return None

    disc_rate = disc / 100.0
    fee_rate  = fee / 100.0
    target    = margin / 100.0

    denom = 1 - fee_rate - target
    if denom <= 0:
        return None
    fp = math.floor(((supply + ship) / denom) / 100) * 100  # 판매가

    fee_amt    = fp * fee_rate
    margin_amt = fp - supply - ship - fee_amt

    if fixed_coupon is not None:
        # 판매가 고정, 쿠폰할인 금액 고정 → 정상가/할인율만 재계산
        disc_amt = fixed_coupon
        orig     = fp + disc_amt
        disc_rate_out = (disc_amt / orig) if orig > 0 else 0.0
    else:
        # 정가 대비 할인율 → 정상가 = 판매가 ÷ (1 - 할인율)
        if disc_rate >= 1:
            return None
        orig     = fp / (1 - disc_rate)
        disc_amt = orig - fp
        disc_rate_out = disc_rate

    return {
        "final":     fp,
        "margin":    margin_amt,
        "discount":  disc_amt,
        "orig":      orig,
        "disc_rate": disc_rate_out * 100,
    }

# ==================================================================
# 화면: 마진 계산기
# ==================================================================
def render_margin_calculator():
    st.markdown('<div class="topcard"><div class="bar-title">🧮 마진계산기</div></div>',
                unsafe_allow_html=True)

    st.session_state.mc_product = st.text_input(
        "노출상품명",
        value=st.session_state.get("mc_product", ""),
        placeholder="노출상품명 (가이드의 노출상품명으로 전달)")

    st.session_state.mc_mgmt_name = st.text_input(
        "등록상품명(관리용)",
        value=st.session_state.get("mc_mgmt_name", ""),
        placeholder="등록상품명(관리용) (가이드로 전달)")

    applied = st.session_state.mc_fixed_coupon is not None

    ca, cb, cc = st.columns([1, 1, 2])
    with ca:
        if st.button("＋ 행 추가", use_container_width=True):
            if len(st.session_state.mc_rows) < 10:
                st.session_state.mc_rows.append(
                    {"opt": "", "supply": 0, "ship": 0, "disc": 60.0, "fee": 12.0, "margin": 20.0})
    with cb:
        if st.button("－ 행 삭제", use_container_width=True):
            if len(st.session_state.mc_rows) > 1:
                st.session_state.mc_rows.pop()
    with cc:
        coupon_label = "🎟 쿠폰할인 적용중 (누르면 해제)" if applied else "🎟 쿠폰할인 일괄 적용"
        toggle_coupon = st.button(coupon_label, use_container_width=True,
                                  type=("primary" if applied else "secondary"))

    if toggle_coupon:
        if applied:
            st.session_state.mc_fixed_coupon = None
            st.rerun()
        else:
            first = st.session_state.mc_rows[0]
            base_res = calc_margin(first["supply"], first["ship"], first["disc"],
                                   first["fee"], first["margin"])
            if base_res:
                st.session_state.mc_fixed_coupon = int(base_res["discount"])
                st.rerun()
            else:
                st.warning("1번 행의 공급가를 먼저 입력하세요.")

    fixed = st.session_state.mc_fixed_coupon

    COLS = [1.2, 1.3, 1.2, 1.1, 1.1, 1.1, 1.3, 1.3, 1.3, 1.3, 1.1]

    h = st.columns(COLS, gap="small")
    heads = ["옵션명", "공급가", "택배비", "할인율%", "수수료%", "마진율%",
             "판매가", "마진액", "쿠폰할인", "정상가", "적용할인%"]
    for col, name in zip(h, heads):
        col.markdown(f"<div style='font-size:12px;font-weight:700;color:#0d47a1;"
                     f"text-align:center;'>{name}</div>", unsafe_allow_html=True)

    results = []
    for i, row in enumerate(st.session_state.mc_rows):
        c = st.columns(COLS, gap="small")
        row["opt"] = c[0].text_input("옵션명", value=row["opt"], key=f"mc_opt_{i}",
                                     max_chars=6, label_visibility="collapsed",
                                     placeholder="옵션")
        row["supply"] = c[1].number_input("공급가", value=int(row["supply"]),
                                          step=100, min_value=0, key=f"mc_sup_{i}",
                                          label_visibility="collapsed")
        row["ship"] = c[2].number_input("택배비", value=int(row["ship"]),
                                        step=100, min_value=0, key=f"mc_ship_{i}",
                                        label_visibility="collapsed")
        row["disc"] = c[3].number_input("할인율", value=float(row["disc"]),
                                        step=1.0, min_value=0.0, key=f"mc_disc_{i}",
                                        label_visibility="collapsed")
        row["fee"] = c[4].number_input("수수료", value=float(row["fee"]),
                                       step=0.1, min_value=0.0, key=f"mc_fee_{i}",
                                       label_visibility="collapsed")
        row["margin"] = c[5].number_input("마진율", value=float(row["margin"]),
                                          step=0.1, min_value=0.0, key=f"mc_mrg_{i}",
                                          label_visibility="collapsed")

        res = calc_margin(row["supply"], row["ship"], row["disc"], row["fee"],
                          row["margin"], fixed_coupon=fixed)
        if res:
            c[6].markdown(f"<div class='mc-out mc-final'>{int(res['final']):,}</div>",
                          unsafe_allow_html=True)
            c[7].markdown(f"<div class='mc-out mc-margin'>{int(res['margin']):,}</div>",
                          unsafe_allow_html=True)
            c[8].markdown(f"<div class='mc-out mc-disc'>{int(res['discount']):,}</div>",
                          unsafe_allow_html=True)
            c[9].markdown(f"<div class='mc-out mc-orig'>{int(res['orig']):,}</div>",
                          unsafe_allow_html=True)
            c[10].markdown(f"<div class='mc-out mc-rate'>{res['disc_rate']:.1f}%</div>",
                           unsafe_allow_html=True)
            results.append({
                "opt": row["opt"],
                "supply": int(row["supply"]),
                "ship": int(row["ship"]),
                "disc": float(row["disc"]),
                "fee": float(row["fee"]),
                "margin_rate": float(row["margin"]),
                "final": int(res["final"]),
                "margin": int(res["margin"]),
                "discount": int(res["discount"]),
                "orig": int(res["orig"]),
                "disc_rate": round(res["disc_rate"], 1),
            })
        else:
            for k in range(6, 11):
                c[k].markdown("<div class='mc-out mc-empty'>-</div>", unsafe_allow_html=True)

    st.markdown("")
    if st.button("📤 상품등록가이드로 넘기기", type="primary", use_container_width=True):
        st.session_state.mc_sent = results
        st.session_state.mc_mgmt_sent = st.session_state.get("mc_mgmt_name", "")
        st.success("✅ 상품등록가이드로 넘겼습니다. '상품등록가이드' 탭에서 확인하세요.")

# ==================================================================
# 화면: 키워드 추출기
# ==================================================================
def render_keyword_tool():
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

    st.markdown('<div class="topcard"><div class="bar-title">🛒 쿠팡키워드 추출기</div></div>',
                unsafe_allow_html=True)
    ta, tb = st.columns([3, 1.2], vertical_alignment="bottom")
    with ta:
        st.text_input("상품명 (여러 개는 띄어쓰기)", "샤인머스켓",
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
    st.caption("💡 선택한 키워드는 '상품등록가이드'의 태그 항목에 자동으로 채워집니다.")

    if st.session_state.get("results"):
        st.markdown('<div class="parent-box">자동 인식된 상위어: '
                    + st.session_state.get("related_info", "") + '</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="list-head">추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)</div>',
                    unsafe_allow_html=True)
        with st.container(height=520, key="kwlist"):
            for i, (kw, vol, comp, score) in enumerate(st.session_state.results):
                c1, c2, c3 = st.columns([3, 1.4, 1.2], vertical_alignment="center")
                already = kw in st.session_state.selected
                with c1:
                    if already:
                        st.markdown("<span class='kw-
                        picked'></span>", unsafe_allow_html=True)
                    st.button(kw, key="pick_" + str(i),
                              on_click=toggle_keyword, args=(kw,), use_container_width=True)
                c2.markdown("<div class='metric-val'>" + format(vol, ",") + "</div>",
                            unsafe_allow_html=True)
                c3.markdown("<div class='metric-val'>" + str(comp) + "</div>",
                            unsafe_allow_html=True)
    elif "results" in st.session_state:
        st.warning("수집된 키워드가 없습니다. 상품명이나 개수를 조정해 보세요.")

# ==================================================================
# 화면: 상품등록가이드
# ==================================================================
def render_product_guide():
    st.markdown('<div class="topcard"><div class="bar-title">📋 상품등록 가이드</div></div>',
                unsafe_allow_html=True)

    selected_kw = ", ".join(st.session_state.get("selected", []))
    mc_product = st.session_state.get("mc_product", "")
    mc_mgmt = st.session_state.get("mc_mgmt_sent", "")
    mc_sent = st.session_state.get("mc_sent", [])
    mc_options = [r["opt"] for r in mc_sent if r["opt"]]
    pkg_text = " ".join('"' + o + '",' for o in mc_options).rstrip(",")

    # 넘어온 마진 결과: 옵션별 (옵션명, 중량빈칸, 정상가, 판매가)
    opt_rows = [[r["opt"], "", str(r["orig"]), str(r["final"])] for r in mc_sent]

    # 쿠폰할인 목록 (옵션명 + 쿠폰할인금액)
    coupon_rows = [[(r.get("opt") or f"옵션{i+1}"), int(r.get("discount", 0))]
                   for i, r in enumerate(mc_sent)]

    # 구글시트 표 (한 행 = 옵션 하나)
    sheet_rows = []
    for r in mc_sent:
        sheet_rows.append([
            mc_product, mc_mgmt, r.get("opt", ""),
            r.get("supply", 0), r.get("ship", 0), r.get("disc", 0),
            r.get("fee", 0), r.get("margin_rate", 0),
            r.get("final", 0), r.get("margin", 0),
            r.get("discount", 0), r.get("orig", 0),
        ])

    GUIDE_HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing:border-box; font-family:'Malgun Gothic',sans-serif; }
  body { margin:0; padding:6px 4px; background:#fff; }

  .sec { font-size:14px; font-weight:800; color:#0d47a1;
         margin:14px 0 6px; padding-bottom:4px; border-bottom:2px solid #e3ecfb; }

  .row { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
  .label { flex:0 0 150px; font-size:12.5px; font-weight:700; color:#333; }
  .row input { flex:1; height:36px; padding:4px 8px; font-size:12.5px;
               border:1px solid #d5dae1; border-radius:6px; outline:none;
               transition:background .15s,border-color .15s; }
  .row input.filled { background:#fff8e1; border-color:#f0c000; }
  .row input.copied { background:#eafaf3 !important; border-color:#2e7d32 !important;
                      color:#00794c !important; font-weight:700 !important; }
  .cbtn { flex:0 0 auto; height:36px; padding:0 12px; border:none; border-radius:6px;
          background:linear-gradient(135deg,#1a73e8,#0d47a1); color:#fff;
          font-size:12px; font-weight:700; cursor:pointer; }

  .opt-table { width:100%; border-collapse:collapse; margin-top:4px; table-layout:fixed; }
  .opt-table th, .opt-table td { border:1px solid #d5dae1; padding:2px; text-align:center; }
  .opt-table th { background:#f1f6ff; font-size:11.5px; font-weight:800; color:#0d47a1; }
  .cellbox { display:flex; align-items:center; gap:2px; }
  .cellbox input { flex:1; min-width:0; height:32px; padding:2px 3px; font-size:11.5px;
                   border:1px solid #e1e6ec; border-radius:5px; outline:none; text-align:center;
                   transition:background .15s,border-color .15s; }
  .cellbox input.filled { background:#fff8e1; border-color:#f0c000; }
  .cellbox input.copied { background:#eafaf3 !important; border-color:#2e7d32 !important;
                          color:#00794c !important; font-weight:700 !important; }
  .mini-copy { flex:0 0 auto; width:20px; height:28px; border:none; border-radius:4px;
               background:#eef3fb; color:#0d47a1; font-size:10px; font-weight:800; cursor:pointer; padding:0; }
  .del-btn { width:24px; height:28px; border:none; border-radius:4px;
             background:#fdecec; color:#d63031; font-size:12px; font-weight:800; cursor:pointer; padding:0; }
  .del-btn:hover { background:#f8d7da; }
  .empty-msg { font-size:12px; color:#999; text-align:center; padding:8px 0; }

  .wbtn { height:34px; padding:0 16px; border:1px solid #2e7d32; border-radius:6px;
          background:#fff; color:#2e7d32; font-size:12.5px; font-weight:700; cursor:pointer; }
  .wbtn:hover { background:#eefaf0; }
  .legend { font-size:11.5px; color:#777; margin:4px 0 2px; }
  .legend b { padding:1px 6px; border-radius:4px; }
  .legend .lg-fill { background:#fff8e1; color:#8a6d00; }
  .legend .lg-copy { background:#eafaf3; color:#00794c; }
</style>
</head>
<body>

<div class="sec">상품명 / 카테고리</div>
<div class="legend">색상 안내: <b class="lg-fill">노랑=입력됨</b> · <b class="lg-copy">초록=복사완료</b></div>
<div id="topArea"></div>

<div class="sec">옵션 / 가격</div>

<div class="row">
  <div class="label">중량 일괄 입력</div>
  <input type="text" id="weightInput" placeholder="모든 옵션의 중량 칸에 적용 (예: 1kg)">
  <button class="cbtn" onclick="applyWeightFromInput()">적용</button>
</div>

<table class="opt-table">
  <colgroup>
    <col style="width:23%"><col style="width:23%"><col style="width:23%">
    <col style="width:23%"><col style="width:8%">
  </colgroup>
  <thead>
    <tr><th>옵션</th><th>중량</th><th>정상가</th><th>판매가</th><th>삭제</th></tr>
  </thead>
  <tbody id="optBody"></tbody>
</table>
<div id="emptyMsg" class="empty-msg">마진계산기에서 넘기면 여기에 표시됩니다.</div>

<div class="sec">상품 주요정보</div>
<div id="infoArea"></div>

<div class="sec">검색 노출</div>
<div id="searchArea"></div>

<div class="sec">배송 / 반품</div>
<div id="shipArea"></div>

<div class="sec">쿠폰할인</div>
<div id="couponArea"></div>

<div class="sec">구글시트 표 (보관용)</div>
<div style="margin-bottom:6px;">
  <button class="wbtn" onclick="copySheet()">📋 전체 복사 (구글시트 붙여넣기용)</button>
  <span id="copyMsg" style="font-size:12px;color:#2e7d32;font-weight:700;margin-left:8px;"></span>
</div>
<div style="overflow-x:auto;">
  <table class="opt-table" id="sheetTable" style="table-layout:auto;"><thead><tr>
    <th>노출상품명</th><th>등록상품명</th><th>옵션명</th><th>공급가</th><th>택배비</th>
    <th>할인율</th><th>수수료</th><th>마진율</th><th>판매가</th><th>마진액</th>
    <th>쿠폰할인</th><th>정상가</th>
  </tr></thead><tbody id="sheetBody"></tbody></table>
</div>

<script>
  const KEYWORD_TAGS = "__SELECTED_KW__";
  const MC_PRODUCT = "__MC_PRODUCT__";
  const MC_MGMT = "__MC_MGMT__";
  const OPT_ROWS = __OPT_ROWS__;
  const PKG_TEXT = "__PKG_TEXT__";
  const COUPON_ROWS = __COUPON_ROWS__;
  const SHEET_ROWS  = __SHEET_ROWS__;

  const TOP = [
    ["브랜드", "브랜드없음(자체제작)"],
    ["노출상품명", MC_PRODUCT],
    ["등록상품명(관리용)", MC_MGMT],
    ["카테고리", ""],
  ];
  const INFO = [
    ["제조사", "(브랜드)협력사"],
    ["부가세", "면세"],
  ];
  const SEARCH = [
    ["태그", KEYWORD_TAGS],
    ["검색필터", ""],
    ["상품정보제공고시", "농수축산물 / 전체상품 상세페이지 참조"],
    ["품목 또는 명칭", "✅ 해당필터 등록"],
    ["포장단위 용량/수량/크기", PKG_TEXT],
    ["생산자(수입자)", "(브랜드)협력사"],
    ["원산지", "국내산"],
  ];
  const SHIP = [
    ["출고지", "사업장소재지"],
    ["택배사", "CJ대한통운"],
    ["배송방법", "신선냉동"],
    ["출고소요일", "3일"],
    ["반품/교환지", "사업장소재지"],
  ];

  function refreshFilled(inp){
    if(inp.classList.contains("copied")) return;
    if(inp.value.trim() !== "") inp.classList.add("filled");
    else inp.classList.remove("filled");
  }
  function copyRowInput(inp){
    navigator.clipboard.writeText(inp.value).then(()=>{
      inp.classList.remove("filled"); inp.classList.add("copied");
    });
  }
  function copyCell(inp){
    navigator.clipboard.writeText(inp.value).then(()=>{
      inp.classList.remove("filled"); inp.classList.add("copied");
    });
  }

  function buildRows(arr, containerId){
    const box = document.getElementById(containerId);
    arr.forEach(([label, val])=>{
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML =
        '<div class="label">'+label+'</div>' +
        '<input type="text" value="'+String(val).replace(/"/g,'&quot;')+'">' +
        '<button class="cbtn">복사</button>';
      const inp = row.querySelector("input");
      const btn = row.querySelector(".cbtn");
      refreshFilled(inp);
      inp.addEventListener("input", ()=>{ inp.classList.remove("copied"); refreshFilled(inp); });
      btn.onclick = ()=> copyRowInput(inp);
      box.appendChild(row);
    });
  }

  buildRows(TOP, "topArea");
  buildRows(INFO, "infoArea");
  buildRows(SEARCH, "searchArea");
  buildRows(SHIP, "shipArea");

  function makeCell(cls, val, ph){
    const v = (val!==undefined && val!==null && val!=="") ? String(val).replace(/"/g,'&quot;') : "";
    return '<td><div class="cellbox">' +
             '<input type="text" class="'+cls+'" value="'+v+'" placeholder="'+ph+'">' +
             '<button class="mini-copy">복사</button>' +
           '</div></td>';
  }

  function refreshEmptyMsg(){
    const tb = document.getElementById("optBody");
    document.getElementById("emptyMsg").style.display =
      tb.children.length === 0 ? "block" : "none";
  }

  function addOptRow(r){
    r = r || ["","","",""];
    const tb = document.getElementById("optBody");
    const tr = document.createElement("tr");
    tr.innerHTML =
      makeCell("c-opt", r[0], "옵션") +
      makeCell("c-w",   r[1], "중량") +
      makeCell("c-n",   r[2], "정상가") +
      makeCell("c-s",   r[3], "판매가") +
      '<td><button class="del-btn" title="삭제">✕</button></td>';
    tr.querySelectorAll(".cellbox").forEach(box=>{
      const inp = box.querySelector("input");
      const btn = box.querySelector(".mini-copy");
      refreshFilled(inp);
      inp.addEventListener("input", ()=>{ inp.classList.remove("copied"); refreshFilled(inp); });
      btn.onclick = ()=> copyCell(inp);
    });
    tr.querySelector(".del-btn").onclick = ()=>{ tr.remove(); refreshEmptyMsg(); };
    tb.appendChild(tr);
    refreshEmptyMsg();
  }

  function applyWeightAll(val){
    document.querySelectorAll("#optBody .c-w").forEach(inp=>{
      inp.value = val; inp.classList.remove("copied"); refreshFilled(inp);
    });
  }
  function applyWeightFromInput(){
    const el = document.getElementById("weightInput");
    applyWeightAll(el.value.trim());
  }

  // 마진계산기에서 넘어온 옵션 행 자동 생성
  if(OPT_ROWS && OPT_ROWS.length){
    OPT_ROWS.forEach(r=> addOptRow(r));
  } else {
    refreshEmptyMsg();
  }

  // 쿠폰할인 목록 렌더
  (function(){
    const box = document.getElementById("couponArea");
    if(!COUPON_ROWS || !COUPON_ROWS.length){
      box.innerHTML = '<div class="empty-msg">마진계산기에서 넘기면 표시됩니다.</div>';
      return;
    }
    COUPON_ROWS.forEach(([name, amt])=>{
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML =
        '<div class="label">'+name+'</div>' +
        '<input type="text" value="'+String(amt)+'">' +
        '<button class="cbtn">복사</button>';
      const inp = row.querySelector("input");
      const btn = row.querySelector(".cbtn");
      refreshFilled(inp);
      inp.addEventListener("input", ()=>{ inp.classList.remove("copied"); refreshFilled(inp); });
      btn.onclick = ()=> copyRowInput(inp);
      box.appendChild(row);
    });
  })();

  // 구글시트 표 렌더
  (function(){
    const tb = document.getElementById("sheetBody");
    if(!SHEET_ROWS || !SHEET_ROWS.length){
      tb.innerHTML = '<tr><td colspan="12" class="empty-msg">마진계산기에서 넘기면 표시됩니다.</td></tr>';
      return;
    }
    SHEET_ROWS.forEach(r=>{
      const tr = document.createElement("tr");
      tr.innerHTML = r.map(v=>'<td style="font-size:11px;padding:4px;white-space:nowrap;">'+String(v)+'</td>').join("");
      tb.appendChild(tr);
    });
  })();

  // 구글시트 붙여넣기용 전체 복사
  function copySheet(){
    if(!SHEET_ROWS || !SHEET_ROWS.length) return;
    const head = ["노출상품명","등록상품명","옵션명","공급가","택배비","할인율",
                  "수수료","마진율","판매가","마진액","쿠폰할인","정상가"];
    const lines = [head.join("\t")];
    SHEET_ROWS.forEach(r=> lines.push(r.join("\t")));
    const text = lines.join("\n");
    navigator.clipboard.writeText(text).then(()=>{
      const m = document.getElementById("copyMsg");
      m.textContent = "복사됨 ✓ 구글시트에 붙여넣기 하세요";
      setTimeout(()=>{ m.textContent=""; }, 2500);
    });
  }
</script>

</body>
</html>
"""
    safe_kw = selected_kw.replace("\\", "\\\\").replace('"', '\\"')
    safe_prod = mc_product.replace("\\", "\\\\").replace('"', '\\"')
    safe_mgmt = mc_mgmt.replace("\\", "\\\\").replace('"', '\\"')
    safe_pkg = pkg_text.replace("\\", "\\\\").replace('"', '\\"')
    GUIDE_HTML = GUIDE_HTML.replace("__SELECTED_KW__", safe_kw)
    GUIDE_HTML = GUIDE_HTML.replace("__MC_PRODUCT__", safe_prod)
    GUIDE_HTML = GUIDE_HTML.replace("__MC_MGMT__", safe_mgmt)
    GUIDE_HTML = GUIDE_HTML.replace("__OPT_ROWS__", json.dumps(opt_rows, ensure_ascii=False))
    GUIDE_HTML = GUIDE_HTML.replace("__PKG_TEXT__", safe_pkg)
    GUIDE_HTML = GUIDE_HTML.replace("__COUPON_ROWS__", json.dumps(coupon_rows, ensure_ascii=False))
    GUIDE_HTML = GUIDE_HTML.replace("__SHEET_ROWS__", json.dumps(sheet_rows, ensure_ascii=False))

    components.html(GUIDE_HTML, height=2000, scrolling=True)

# ==================================================================
# 공통 CSS
# ==================================================================
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0.6rem !important; }

.topcard {
    background: linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%);
    padding: 14px 20px 6px 20px; border: 1px solid #e6e8eb;
    border-radius: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.06); margin-bottom: 14px;
}
.bar-title { font-size: 20px; font-weight: 700; color: #263238; margin-bottom: 8px; }

div[role="radiogroup"] { gap: 8px !important; margin-bottom: 10px !important; }
div[role="radiogroup"] label {
    background:#f1f3f5 !important; border:1.5px solid #e6e8eb !important;
    border-radius:12px !important; padding:8px 16px !important; font-weight:700 !important;
}
div[role="radiogroup"] label:has(input:checked) {
    background:linear-gradient(135deg,#667eea,#764ba2) !important;
    border-color:transparent !important;
}
div[role="radiogroup"] label:has(input:checked) div { color:#fff !important; }

div[data-testid="stTextInput"] input {
    height: 46px !important; font-size: 15px !important; color: #263238 !important;
    padding: 0 14px !important; border-radius: 12px !important;
    border: 1.5px solid #dfe4ea !important; background: #ffffff !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #667eea !important; box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
}
div[data-testid="stTextInput"] div[data-baseweb="input"] {
    border: none !important; box-shadow: none !important; background: transparent !important;
}

[data-testid="stBaseButton-primary"] {
    height: 46px !important; min-height: 46px !important; border: none !important;
    border-radius: 12px !important; color: #fff !important;
    background: linear-gradient(135deg,#667eea 0%,#764ba2 100%) !important;
    box-shadow: 0 4px 14px rgba(102,126,234,0.35) !important;
}
[data-testid="stBaseButton-primary"] p { font-size: 15px !important; font-weight: 800 !important; color:#fff !important; }

.copy-head { font-size: 15px; font-weight: 700; color:#37474f; margin: 8px 0 14px 0; }
.copy-badge { background:#1565c0; color:#fff; font-size:12px; font-weight:700;
    padding:2px 10px; border-radius:12px; margin-left:6px; }
[data-testid="stCode"] { background:#f0f7ff !important; border:1.5px solid #90caf9 !important;
    border-radius:10px !important; }
[data-testid="stCode"] code { color:#1565c0 !important; font-size:12px !important; }

.parent-box { background:#e3f2fd; border-radius:10px; color:#1565c0;
    font-size:14px; padding:12px 16px; margin:6px 0 4px 0; }
.list-head { font-size:18px; font-weight:800; color:#263238; margin:14px 0 12px 0; }

[data-testid="stBaseButton-secondary"] {
    min-height: 40px !important; height: 40px !important; padding: 0 14px !important;
    border-radius: 12px !important; border: 1.5px solid #e6e8eb !important;
    background: #fff !important; justify-content: flex-start !important;
    margin: 0 !important;
}
[data-testid="stBaseButton-secondary"] p {
    font-size: 16px !important; font-weight: 500 !important;
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
}
[data-testid="stBaseButton-secondary"]:hover { border-color:#ff7043 !important; }
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] {
    background:#eef6ff !important; border-color:#4a90d9 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] p {
    color:#1565c0 !important; font-weight:700 !important;
}
.kw-picked { display:block !important; height:0 !important; margin:0 !important;
    padding:0 !important; overflow:hidden !important; line-height:0 !important; }
[data-testid="stElementContainer"]:has(.kw-picked) {
    height:0 !important; min-height:0 !important; margin:0 !important; padding:0 !important;
}
.metric-val { min-height:40px; display:flex; align-items:center; justify-content:center;
    font-size:16px; font-weight:600; color:#607d8b; }
div[data-testid="stVerticalBlockBorderWrapper"] { border:none !important; }

/* ===== 키워드 목록 간격 완전 제거 (kwlist 안에서만) ===== */
.st-key-kwlist div[data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-kwlist div[data-testid="stHorizontalBlock"] {
    margin: 0 !important; gap: 4px !important; row-gap: 0 !important; min-height: 0 !important;
}
.st-key-kwlist div[data-testid="stElementContainer"] {
    margin: 0 !important; padding: 0 !important; min-height: 0 !important;
}
.st-key-kwlist [data-testid="stBaseButton-secondary"] {
    min-height: 34px !important; height: 34px !important; margin: 0 !important;
}
.st-key-kwlist .metric-val { min-height: 34px !important; }

/* 선택 시 벌어지지 않게 kw-picked 완전 0높이 */
.st-key-kwlist .kw-picked {
    display: block !important; height: 0 !important; max-height: 0 !important;
    margin: 0 !important; padding: 0 !important; line-height: 0 !important;
    overflow: hidden !important; font-size: 0 !important;
}
.st-key-kwlist div[data-testid="stElementContainer"]:has(.kw-picked) {
    height: 0 !important; min-height: 0 !important; max-height: 0 !important;
    margin: 0 !important; padding: 0 !important; overflow: hidden !important;
}
/* 선택 색상 표시 */
.st-key-kwlist div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] {
    background: #eef6ff !important; border-color: #4a90d9 !important;
}
.st-key-kwlist div[data-testid="stHorizontalBlock"]:has(.kw-picked) [data-testid="stBaseButton-secondary"] p {
    color: #1565c0 !important; font-weight: 700 !important;
}

# ==================================================================
# 상단 메뉴 + 화면 전환
# ==================================================================
menu = st.radio(
    "메뉴",
    ["🧮 마진계산기", "🛒 쿠팡키워드 추출기", "📋 상품등록가이드"],
    horizontal=True,
    label_visibility="collapsed",
)

if menu == "🧮 마진계산기":
    render_margin_calculator()
elif menu == "🛒 쿠팡키워드 추출기":
    render_keyword_tool()
else:
    render_product_guide()
