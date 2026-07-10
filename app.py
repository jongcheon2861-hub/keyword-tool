import streamlit as st
import pandas as pd
import requests, time, hmac, hashlib, base64
import streamlit.components.v1 as components

st.set_page_config(page_title="쿠팡 셀러 도구", layout="centered",
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

# ==================================================================
# 화면: 마진 계산기
# ==================================================================
MARGIN_CALC_HTML = """
<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
  * { box-sizing: border-box; }
  body { font-family: 'Malgun Gothic','Apple SD Gothic Neo',sans-serif; background:#f4f6f9; margin:0; padding:16px; color:#333; }
  h1 { font-size:20px; text-align:center; color:#1a73e8; margin:0 0 6px; }
  .desc { text-align:center; font-size:12px; color:#777; margin-bottom:14px; }
  .table-wrap { overflow-x:auto; background:#fff; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.08); padding:12px; }
  table { border-collapse:collapse; width:100%; font-size:12px; }
  th,td { border:1px solid #e3e8ef; padding:5px; text-align:center; white-space:nowrap; }
  thead th { background:#1a73e8; color:#fff; font-weight:600; position:sticky; top:0; }
  tbody tr:nth-child(even) { background:#f9fbff; }
  input,select { width:100%; padding:6px 5px; font-size:12px; border:1px solid #d5dae1; border-radius:6px; outline:none; text-align:right; }
  input[type="text"] { text-align:left; }
  select { -webkit-appearance:none; -moz-appearance:none; appearance:none; text-align:center; text-align-last:center; background-image:none; }
  select::-ms-expand { display:none; }
  input:focus,select:focus { border-color:#1a73e8; }
  .col-name { width:240px; }
  td.result { font-weight:700; background:#f0f5ff; color:#1a73e8; }
  td.discount-cell { font-weight:700; background:#fdeef0; color:#d63384; }
  td.margin-cell { font-weight:700; background:#eafaf3; color:#00a86b; }
  .no-col { background:#f4f6f9; font-weight:600; color:#555; }
  .buttons { margin:12px auto 0; text-align:center; }
  .btn { background:#1a73e8; color:#fff; border:none; padding:9px 18px; border-radius:8px; font-size:13px; cursor:pointer; margin:0 4px; }
  .btn.gray { background:#888; }
  tfoot td { background:#fff7e6; font-weight:700; color:#d35400; }
</style></head><body>
<h1>🧮 쿠팡 마진 계산기</h1>
<div class="desc">판매가 100원 단위 내림 · 마진율 자동 보정 · 최대 10개</div>
<div class="table-wrap"><table>
<thead><tr>
<th>No</th><th>상품명</th><th>공급가</th><th>택배비</th><th>할인율(%)</th><th>수수료(%)</th>
<th>마진율</th><th>판매가</th><th>마진액</th><th>쿠폰할인</th><th>정가</th>
</tr></thead>
<tbody id="tbody"></tbody>
<tfoot><tr><td colspan="7">합계</td>
<td id="sumFinal">-</td><td id="sumMargin">-</td><td id="sumDiscount">-</td><td id="sumOrig">-</td>
</tr></tfoot></table></div>
<div class="buttons">
<button class="btn" onclick="addRow()">+ 행 추가</button>
<button class="btn gray" onclick="clearAll()">전체 초기화</button>
</div>
<script>
const ROWS=10, DEFAULT_TARGET=20.0, tbody=document.getElementById('tbody');
function marginOptions(){let h='';for(let r=40.0;r>=9.99;r-=0.1){const v=r.toFixed(1);h+=`<option value="${v}"${v==='20.0'?' selected':''}>${v}%</option>`;}return h;}
function createRow(i){const tr=document.createElement('tr');tr.innerHTML=`
<td class="no-col">${i+1}</td>
<td><input type="text" class="col-name" maxlength="40" placeholder="상품명"></td>
<td><input type="number" class="supply" placeholder="0" oninput="calc()"></td>
<td><input type="number" class="ship" value="0" oninput="calc()"></td>
<td><input type="number" class="disc" value="60" oninput="calc()"></td>
<td><input type="number" class="fee" value="12" step="0.1" oninput="calc()"></td>
<td><select class="margin" onchange="onMarginChange(this)">${marginOptions()}</select></td>
<td class="result finalOut">-</td><td class="margin-cell marginOut">-</td>
<td class="discount-cell discountOut">-</td><td class="result origOut">-</td>`;
tr.querySelector('.margin').dataset.userTarget=DEFAULT_TARGET.toFixed(1);return tr;}
function buildTable(){tbody.innerHTML='';for(let i=0;i<ROWS;i++)tbody.appendChild(createRow(i));}
function addRow(){if(tbody.children.length>=ROWS){alert('최대 '+ROWS+'개까지');return;}tbody.appendChild(createRow(tbody.children.length));}
function clearAll(){if(confirm('모두 지울까요?')){buildTable();calc();}}
function won(n){return Math.round(n).toLocaleString('ko-KR');}
function onMarginChange(sel){sel.dataset.userTarget=parseFloat(sel.value).toFixed(1);calc();}
function setSelectToRate(sel,p){let r=Math.round(p*10)/10;if(r>40)r=40;if(r<10)r=10;sel.value=r.toFixed(1);}
function calc(){let sO=0,sD=0,sF=0,sM=0;
tbody.querySelectorAll('tr').forEach(tr=>{
const supply=parseFloat(tr.querySelector('.supply').value)||0;
const ship=parseFloat(tr.querySelector('.ship').value)||0;
const feeRate=(parseFloat(tr.querySelector('.fee').value)||0)/100;
const discRate=(parseFloat(tr.querySelector('.disc').value)||0)/100;
const ms=tr.querySelector('.margin');
const fo=tr.querySelector('.finalOut'),mo=tr.querySelector('.marginOut'),
dco=tr.querySelector('.discountOut'),oo=tr.querySelector('.origOut');
const targetRate=(parseFloat(ms.dataset.userTarget)||DEFAULT_TARGET)/100;
if(supply<=0){setSelectToRate(ms,targetRate*100);fo.textContent=mo.textContent=dco.textContent=oo.textContent='-';return;}
const denom=1-feeRate-targetRate;
if(denom<=0){fo.textContent=mo.textContent=dco.textContent=oo.textContent='오류';return;}
let fp=(supply+ship)/denom;fp=Math.floor(fp/100)*100;
const fee=fp*feeRate,margin=fp-supply-ship-fee;
setSelectToRate(ms,margin/fp*100);
const orig=fp*(1+discRate),disc=orig-fp;
fo.textContent=won(fp);mo.textContent=won(margin);dco.textContent=won(disc);oo.textContent=won(orig);
sF+=fp;sM+=margin;sD+=disc;sO+=orig;});
document.getElementById('sumFinal').textContent=won(sF);
document.getElementById('sumMargin').textContent=won(sM);
document.getElementById('sumDiscount').textContent=won(sD);
document.getElementById('sumOrig').textContent=won(sO);}
buildTable();calc();
</script></body></html>
"""

def render_margin_calculator():
    components.html(MARGIN_CALC_HTML, height=760, scrolling=True)

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

    if st.session_state.get("results"):
        st.markdown('<div class="parent-box">자동 인식된 상위어: '
                    + st.session_state.get("related_info", "") + '</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="list-head">추출된 키워드 · 클릭하면 담겨요 (다시 누르면 삭제)</div>',
                    unsafe_allow_html=True)
        with st.container(height=520):
            for i, (kw, vol, comp, score) in enumerate(st.session_state.results):
                c1, c2, c3 = st.columns([3, 1.4, 1.2], vertical_alignment="center")
                already = kw in st.session_state.selected
                with c1:
                    if already:
                        st.markdown("<span class='kw-picked'></span>", unsafe_allow_html=True)
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
    guide_html = r"""
<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
  * { box-sizing:border-box; }
  body { font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif; background:#f7f9fc; margin:0; padding:16px; color:#263238; }
  h1 { font-size:20px; color:#5b34c0; margin:0 0 4px; }
  .desc { font-size:12px; color:#888; margin-bottom:14px; }
  .sec { font-size:14px; font-weight:800; color:#fff; background:linear-gradient(135deg,#667eea,#764ba2);
         padding:7px 12px; border-radius:8px; margin:16px 0 8px; }
  .row { display:flex; align-items:stretch; gap:8px; margin-bottom:7px; }
  .label { flex:0 0 150px; display:flex; align-items:center; font-size:13px; font-weight:700;
           color:#37474f; background:#eef1f6; border-radius:8px; padding:0 12px; }
  .val { flex:1; }
  .val input { width:100%; height:38px; font-size:13px; padding:0 12px; border:1.5px solid #dfe4ea;
               border-radius:8px; outline:none; }
  .val input:focus { border-color:#667eea; box-shadow:0 0 0 3px rgba(102,126,234,0.15); }
  .copy { flex:0 0 52px; border:none; border-radius:8px; background:#1a73e8; color:#fff;
          font-size:12px; font-weight:700; cursor:pointer; }
  .copy:hover { background:#0d47a1; }
  .copy.done { background:#00a86b; }
  .hint { font-size:11px; color:#9aa4b2; margin:2px 0 6px 158px; }
</style></head><body>
<h1>📋 상품등록가이드</h1>
<div class="desc">항목별로 확인하며 복사 → 쿠팡 등록화면에 붙여넣기 (고정값은 미리 입력됨)</div>
<div id="wrap"></div>
<script>
  const ITEMS = [
    ["S","상품명 / 카테고리"],
    ["브랜드","브랜드없음(자체제작)",""],
    ["노출상품명","","후킹+신뢰+핵심 키워드 5개"],
    ["등록상품명","","판매자관리용"],
    ["카테고리","",""],
    ["S","옵션 / 가격"],
    ["중량","",""],
    ["수량","",""],
    ["정상가","",""],
    ["판매가","",""],
    ["S","상품 주요정보"],
    ["제조사","(브랜드)협력사",""],
    ["부가세","면세",""],
    ["S","검색 노출"],
    ["태그","",""],
    ["검색필터","",""],
    ["상품정보제공고시","농수축산물 / 전체상품 상세페이지 참조",""],
    ["품목/명칭","",""],
    ["포장단위 용량·수량·크기","",""],
    ["생산자(수입자)","(브랜드)협력사",""],
    ["원산지","국내산",""],
    ["S","배송 / 반품정보"],
    ["출고지","",""],
    ["택배사","CJ대한통운",""],
    ["배송방법","신선냉동",""],
    ["출고소요일","3일",""],
    ["반품/교환지","",""],
  ];
  const wrap = document.getElementById('wrap');
  let idx = 0;
  ITEMS.forEach(it => {
    if (it[0] === "S") {
      const s = document.createElement('div');
      s.className = 'sec'; s.textContent = it[1];
      wrap.appendChild(s); return;
    }
    const [label, def, hint] = it;
    const id = 'inp' + (idx++);
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <div class="label">${label}</div>
      <div class="val"><input id="${id}" type="text" value="${def}"></div>
      <button class="copy" onclick="doCopy('${id}', this)">복사</button>`;
    wrap.appendChild(row);
    if (hint) {
      const h = document.createElement('div');
      h.className = 'hint'; h.textContent = '💡 ' + hint;
      wrap.appendChild(h);
    }
  });
  function doCopy(id, btn) {
    const el = document.getElementById(id);
    el.select();
    navigator.clipboard.writeText(el.value).then(() => {
      btn.textContent = '완료'; btn.classList.add('done');
      setTimeout(() => { btn.textContent = '복사'; btn.classList.remove('done'); }, 1000);
    }).catch(() => {
      document.execCommand('copy');
      btn.textContent = '완료'; btn.classList.add('done');
      setTimeout(() => { btn.textContent = '복사'; btn.classList.remove('done'); }, 1000);
    });
  }
</script></body></html>
"""
    components.html(guide_html, height=1400, scrolling=True)

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
    min-height: 44px !important; height: 44px !important; padding: 0 14px !important;
    border-radius: 12px !important; border: 1.5px solid #e6e8eb !important;
    background: #fff !important; justify-content: flex-start !important;
}
[data-testid="stBaseButton-secondary"] p {
    font-size: 17px !important; font-weight: 500 !important;
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
.metric-val { min-height:44px; display:flex; align-items:center; justify-content:center;
    font-size:16px; font-weight:600; color:#607d8b; }
div[data-testid="stVerticalBlockBorderWrapper"] { border:none !important; }

.center-popup {
    position: fixed; top: 30%; left: 50%; transform: translate(-50%,-50%);
    z-index: 100000; padding: 12px 26px; border-radius: 16px;
    font-size: 22px; font-weight: 800; color: #fff;
    background: linear-gradient(135deg,#667eea 0%,#764ba2 45%,#f093fb 100%);
    box-shadow: 0 12px 30px rgba(118,75,162,0.45); pointer-events: none; white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# ==================================================================
# 상단 메뉴 + 화면 전환 (탭 순서: 마진계산기 / 키워드추출기 / 상품등록가이드)
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
