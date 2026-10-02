import hashlib
import hmac
import json
import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from research_ui import render_research
from education import render_education
from automatic import brief
from data_registry import PROVIDERS, capabilities as active_capabilities, health_all
from providers import DataError, Official, demo
from storage import Store
from portfolio_ui import render_portfolio
from ui_v2 import apply_theme, brand, card, empty_state, hero, source_badge


load_dotenv()
st.set_page_config(
    page_title="StockDash · PlanX Investment OS",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    for key in [
        "APP_PASSWORD",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "DATA_GO_KR_SERVICE_KEY",
        "DART_CRTFC_KEY",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "KIS_ENV", "KIS_APP_KEY", "KIS_APP_SECRET", "KIS_CANO", "KIS_ACNT_PRDT_CD",
    ]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except FileNotFoundError:
    pass


def apply_dashboard_theme():
    st.markdown("""
<style>
/* StockDash Dashboard 2026 */
.stApp{background:#f4f7fb!important}
.block-container{max-width:1500px!important;padding:24px 32px 56px!important}
section[data-testid="stSidebar"]{background:#ffffff!important;border-right:1px solid #e7ebf2!important}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label{border-radius:12px!important;padding:10px 12px!important;color:#526176!important}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked){background:#edf4ff!important;box-shadow:inset 3px 0 #2563eb!important;color:#1d4ed8!important}
.sd-top{display:flex;justify-content:space-between;align-items:center;margin:2px 0 18px}
.sd-title{font-size:28px;font-weight:850;letter-spacing:-.045em;color:#172033}
.sd-sub{font-size:13px;color:#7b8799;margin-top:5px}
.sd-status{display:inline-flex;align-items:center;gap:7px;padding:8px 12px;border-radius:999px;background:#ecfdf5;border:1px solid #bbf7d0;color:#047857;font-size:12px;font-weight:750}
.sd-dot{width:7px;height:7px;border-radius:50%;background:#10b981}
.sd-hero{background:linear-gradient(135deg,#172a4d 0%,#1f4d8f 60%,#2563eb 100%);border-radius:22px;padding:28px 30px;color:white;margin:0 0 20px;box-shadow:0 18px 40px rgba(30,64,120,.16)}
.sd-hero .eyebrow{font-size:11px;letter-spacing:.12em;font-weight:800;opacity:.72}
.sd-hero h1{font-size:32px;color:white;margin:8px 0 6px;letter-spacing:-.045em}
.sd-hero p{font-size:14px;color:#dce8fb;margin:0;max-width:720px}
.sd-card{background:#fff;border:1px solid #e6ebf2;border-radius:17px;padding:18px 19px;box-shadow:0 7px 24px rgba(30,50,80,.035);height:100%}
.sd-card-title{font-size:12px;color:#7b8799;font-weight:700}
.sd-card-value{font-size:24px;font-weight:850;color:#172033;letter-spacing:-.035em;margin-top:8px}
.sd-card-change{font-size:12px;font-weight:750;margin-top:7px}
.sd-up{color:#059669}.sd-down{color:#dc2626}.sd-muted{color:#9aa6b5}
.sd-section{font-size:18px;font-weight:820;color:#172033;margin:24px 0 12px;letter-spacing:-.025em}
.sd-panel{background:#fff;border:1px solid #e6ebf2;border-radius:18px;padding:20px;box-shadow:0 7px 24px rgba(30,50,80,.03)}
.sd-panel-title{font-size:15px;font-weight:800;color:#172033;margin-bottom:4px}
.sd-panel-sub{font-size:11px;color:#8a96a8;margin-bottom:14px}
.sd-donut{width:178px;height:178px;border-radius:50%;margin:10px auto 12px;position:relative}
.sd-donut:after{content:"";position:absolute;inset:42px;background:#fff;border-radius:50%}
.sd-donut-label{position:absolute;z-index:2;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;font-weight:850;color:#172033}
.sd-donut-label small{font-size:10px;color:#8a96a8;font-weight:600}
.sd-holding{display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-bottom:1px solid #eef1f5}
.sd-holding:last-child{border-bottom:0}
.sd-holding-name{font-size:13px;font-weight:750;color:#253247}
.sd-holding-meta{font-size:11px;color:#8a96a8;margin-top:2px}
.sd-holding-value{font-size:13px;font-weight:800;color:#253247;text-align:right}
.sd-empty{border:1px dashed #cfd7e3;background:#fbfcfe;border-radius:14px;padding:22px;color:#718096}
.sd-table{background:#fff;border:1px solid #e6ebf2;border-radius:16px;padding:4px}
@media(max-width:800px){.block-container{padding:18px 14px 40px!important}.sd-hero h1{font-size:27px}.sd-title{font-size:24px}}
</style>
""", unsafe_allow_html=True)

apply_theme()
apply_dashboard_theme()


class SessionStore:
    cloud = False

    def read(self):
        return st.session_state.setdefault("practice_data", {"stocks": [], "journal": [], "runs": []})

    def save_stock(self, stock):
        data = self.read()
        for index, old in enumerate(data["stocks"]):
            if old["code"] == stock["code"]:
                data["stocks"][index] = {**old, **stock}
                return
        data["stocks"].append(stock)

    def log(self, collection, item):
        self.read()[collection].append(item)

    def change(self, operation):
        operation(self.read())


def load_store(password):
    sample = not password
    if sample or st.session_state.get("practice_mode"):
        current_store = SessionStore()
    else:
        current_store = Store()
    return sample, current_store, current_store.read()


def stock_label(item):
    code = item.get("code", "")
    suffix = "코드 확인 대기" if code.startswith("pending-") else code
    return f"{item.get('name', '종목')} · {suffix}"


def extract_business_sentences(report):
    excerpt = report.get("business_excerpt", "")
    sentences = [
        x.strip()
        for x in re.split(r"(?<=[.!?])\s+", excerpt)
        if 35 < len(x.strip()) < 650
        and any(w in x for w in ["사업", "제조", "생산", "판매", "서비스"])
        and re.search(r"다[.!?]$", x.strip())
        and "---" not in x
    ]
    return sentences[:3]


password = os.getenv("APP_PASSWORD", "")
if password and not st.session_state.get("authorized"):
    hero("StockDash", "공식 데이터를 연결해 시장과 기업의 변화를 한 흐름으로 읽습니다.", "SECURE ACCESS")
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        with st.container(border=True):
            st.subheader("개인 대시보드 열기")
            with st.form("login"):
                entered = st.text_input("비밀번호", type="password", placeholder="설정한 비밀번호를 입력하세요")
                if st.form_submit_button("대시보드 열기", type="primary", use_container_width=True):
                    if hmac.compare_digest(entered.encode(), password.encode()):
                        st.session_state.authorized = True
                        st.rerun()
                    st.error("비밀번호를 확인하세요.")
    st.stop()

try:
    sample_mode, store, state = load_store(password)
except Exception:
    hero("저장 공간 연결 확인", "기존 자료는 덮어쓰지 않습니다. 저장소 설정만 확인합니다.", "STORAGE")
    st.error("비밀번호 확인은 통과했지만 종목 저장 공간을 열지 못했습니다.")
    url_set = bool(os.getenv("SUPABASE_URL", "").strip())
    key_set = bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())
    if url_set != key_set:
        st.info("Supabase URL과 service_role 키 중 하나만 설정되어 있습니다.")
    elif url_set:
        st.info("Supabase 프로젝트 주소·서버 키·schema.sql 실행 여부를 확인하세요.")
    else:
        st.info("로컬 저장 파일을 열지 못했습니다. 아래 임시 실습은 현재 접속에서만 유지됩니다.")
    if st.button("저장 연결 없이 임시 실습 시작", type="primary"):
        st.session_state.practice_mode = True
        st.rerun()
    st.stop()


def run_analysis(code):
    try:
        with st.spinner("공식 시세 · 결산 · 가치 · 사업 공시를 확인합니다…"):
            provider = st.session_state.get("directory_provider") or Official()
            if code.startswith("pending-"):
                pending = next((s for s in state["stocks"] if s["code"] == code), {})
                matches = provider.search(pending.get("name", ""))
                if len(matches) != 1:
                    st.session_state.search_candidates = matches
                    st.info("검색 목록에서 정확한 종목을 선택하세요.")
                    return
                code = matches[0]["code"]

            price, price_day, price_name = provider.price(code, date.today())
            try:
                report = provider.automatic(code)
            except DataError as error:
                existing = next((s for s in state["stocks"] if s["code"] == code), {})
                partial = {
                    **existing,
                    "code": code,
                    "name": price_name,
                    "kind": existing.get("kind", "관심"),
                    "price_snapshot": {"price": price, "date": price_day},
                    "analysis_error": str(error),
                }
                st.session_state.latest_analysis = partial
                try:
                    store.save_stock(partial)
                    st.session_state.save_notice = "시세·관심종목은 저장했습니다. 재무 분석은 완료되지 않았습니다."
                except Exception:
                    st.session_state.save_notice = "시세만 조회했습니다. 저장소 기록은 실패했습니다."
                st.session_state.selected_code = code
                st.session_state.force_nav = "종목 분석"
                st.session_state.pop("stock_picker", None)
                st.session_state.pop("search_candidates", None)
                st.rerun()

            result = brief(report)
            ai = None  # Narrative research is supplied through chat, without an LLM API.
            at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
            existing = next((s for s in state["stocks"] if s["code"] == code), {})
            stock = {
                **existing,
                "code": code,
                "name": report["name"],
                "kind": existing.get("kind", "관심"),
                "year": report["years"][-1]["year"],
                "report": report,
                "automatic_brief": result,
                "ai_brief": ai,
                "analyzed_at": at,
                "analysis_error": None,
            }
            st.session_state.latest_analysis = stock
            try:
                store.save_stock(stock)
                store.log(
                    "journal",
                    {
                        "code": code,
                        "at": at,
                        "kind": "automatic",
                        "report": report,
                        "automatic_brief": result,
                        "ai_brief": ai,
                    },
                )

                def consolidate(data):
                    pending_ids = {
                        s["code"]
                        for s in data["stocks"]
                        if s["code"].startswith("pending-")
                        and s["name"].casefold() == report["name"].casefold()
                    }
                    for item in data["journal"]:
                        if item["code"] in pending_ids:
                            item["code"] = code
                    data["stocks"] = [s for s in data["stocks"] if s["code"] not in pending_ids]

                store.change(consolidate)
                st.session_state.save_notice = "분석 결과와 이력을 저장했습니다."
            except Exception:
                st.session_state.save_notice = "분석은 끝났지만 저장하지 못했습니다. JSON 다운로드로 보관할 수 있습니다."

            st.session_state.selected_code = code
            st.session_state.force_nav = "종목 분석"
            st.session_state.pop("stock_picker", None)
            st.session_state.pop("search_candidates", None)
        st.rerun()
    except DataError as error:
        st.error(str(error))
    except Exception:
        st.error("분석을 마치지 못했습니다. 이전 결과는 유지됩니다.")


choices = {s["code"]: s for s in state.get("stocks", [])}
latest = st.session_state.get("latest_analysis")
if latest:
    choices[latest["code"]] = latest

if st.session_state.get("force_nav"):
    st.session_state.nav_choice = st.session_state.pop("force_nav")

NAV_ITEMS = ["대시보드", "종목 분석", "공시 분석", "시장 현황", "테마 & 섹터", "포트폴리오", "관심 종목", "AI 인사이트", "설정"]
legacy = {"내 종목":"대시보드", "통합 분석":"대시보드", "홈":"대시보드", "계좌 연결":"포트폴리오"}
current = st.session_state.get("nav_choice", "대시보드")
if current not in NAV_ITEMS:
    st.session_state.nav_choice = legacy.get(current, "대시보드")
    if current not in legacy:
        st.session_state.advanced_page = current

with st.sidebar:
    brand()
    nav = st.radio("메뉴", NAV_ITEMS, key="nav_choice")
    st.markdown("---")
    if choices and nav == "설정":
        codes = list(choices)
        preferred = st.session_state.get("selected_code")
        selected = st.selectbox(
            "현재 종목",
            codes,
            index=codes.index(preferred) if preferred in codes else 0,
            format_func=lambda c: stock_label(choices[c]),
            key="stock_picker",
        )
        stock = choices[selected]
    elif choices:
        stock = choices.get(st.session_state.get("selected_code"), next(iter(choices.values())))
    else:
        stock = {"code": "SAMPLE", "name": "가상 반도체", "report": demo()}

    if sample_mode:
        st.caption("가상 예시 모드")
    elif st.session_state.get("practice_mode"):
        st.caption("임시 저장 모드")
    else:
        st.caption("클라우드 저장" if store.cloud else "실행 서버 저장")

    if password and st.button("로그아웃", use_container_width=True):
        st.session_state.clear()
        st.rerun()

report = stock.get("report")
is_demo = stock.get("code") == "SAMPLE"


def global_search():
    if sample_mode:
        st.info("현재는 가상 예시 모드입니다. APP_PASSWORD와 공식 API 키가 설정되면 실데이터 검색이 열립니다.")
        return
    with st.form("global_search"):
        col_q, col_b = st.columns([6, 1])
        with col_q:
            query = st.text_input(
                "통합 검색",
                placeholder="종목명, 종목코드, 기업명 일부를 검색하세요. 예: 삼성전자 · 005930 · 하이닉스",
                label_visibility="collapsed",
            )
        with col_b:
            submitted = st.form_submit_button("검색·분석", type="primary", use_container_width=True)
    if submitted:
        try:
            provider = st.session_state.get("directory_provider") or Official()
            st.session_state.directory_provider = provider
            matches = provider.search(query)
            st.session_state.search_candidates = matches
            if len(matches) == 1:
                run_analysis(matches[0]["code"])
            elif not matches:
                st.info("일치하는 상장 기업이 없습니다. 기업명 일부나 6자리 종목코드로 다시 검색하세요.")
        except DataError as error:
            st.error(str(error))

    matches = st.session_state.get("search_candidates", [])
    if len(matches) > 1:
        with st.container(border=True):
            st.caption("검색어와 일치하는 기업입니다.")
            with st.form("candidate"):
                candidate = st.selectbox(
                    "검색된 종목",
                    matches,
                    format_func=lambda x: x["name"] + " · " + x["code"],
                )
                if st.form_submit_button("이 종목 분석", type="primary"):
                    run_analysis(candidate["code"])



def _html_card(title, value, change="", tone="muted"):
    cls={"up":"sd-up","down":"sd-down"}.get(tone,"sd-muted")
    return f'<div class="sd-card"><div class="sd-card-title">{title}</div><div class="sd-card-value">{value}</div><div class="sd-card-change {cls}">{change}</div></div>'

def _portfolio_donut(positions):
    if not positions:
        return '<div class="sd-empty">계좌를 연결하면 실제 보유 비중이 원형 차트로 표시됩니다.</div>'
    weights=[max(float(p.get("weight",0)),0) for p in positions]
    total=sum(weights) or 1
    palette=["#2563eb","#10b981","#f59e0b","#8b5cf6","#ef4444","#06b6d4","#f97316","#64748b"]
    stops=[]; cursor=0
    for i,w in enumerate(weights):
        end=cursor+w/total*360
        stops.append(f"{palette[i%len(palette)]} {cursor:.1f}deg {end:.1f}deg")
        cursor=end
    gradient=", ".join(stops)
    return f'''<div class="sd-donut" style="background:conic-gradient({gradient})">
      <div class="sd-donut-label"><span>{total:.0f}%</span><small>보유 비중</small></div>
    </div>'''

def render_dashboard():
    snapshot=st.session_state.get("account_snapshot") or {}
    positions=snapshot.get("positions",[])
    latest_stock=stock if stock and stock.get("code")!="SAMPLE" else None
    st.markdown('''<div class="sd-top"><div><div class="sd-title">StockDash</div><div class="sd-sub">시장 · 포트폴리오 · 관심종목을 한 화면에서 확인하세요.</div></div><div class="sd-status"><span class="sd-dot"></span> Dashboard</div></div>''',unsafe_allow_html=True)
    st.markdown('''<div class="sd-hero"><div class="eyebrow">STOCK DASHBOARD</div><h1>오늘의 투자 화면</h1><p>주요 시장 흐름과 내 포트폴리오, 관심종목의 핵심 정보를 빠르게 확인할 수 있도록 구성했습니다.</p></div>''',unsafe_allow_html=True)
    global_search()

    st.markdown('<div class="sd-section">주요 지수</div>',unsafe_allow_html=True)
    idx=st.columns(4)
    for col,title,cap in zip(idx,["KOSPI","KOSDAQ","S&P 500","NASDAQ"],["market.index","market.index","market.index","market.index"]):
        with col: st.markdown(_html_card(title,"연결 대기","실시간 지수 API 필요 · "+cap),unsafe_allow_html=True)

    st.markdown('<div class="sd-section">포트폴리오</div>',unsafe_allow_html=True)
    p1,p2,p3,p4=st.columns(4)
    if snapshot:
        cards=[("평가금액",f"{snapshot.get('value',0):,.0f}원","계좌 조회 기준"),
               ("평가손익",f"{snapshot.get('pnl',0):+,.0f}원","조회 시점 기준","up" if snapshot.get("pnl",0)>=0 else "down"),
               ("예수금",f"{snapshot.get('cash'):,.0f}원" if snapshot.get("cash") is not None else "미수집","KIS 계좌 기준"),
               ("보유종목",f"{len(positions)}개","국내주식")]
        for col,data in zip([p1,p2,p3,p4],cards):
            with col: st.markdown(_html_card(*data),unsafe_allow_html=True)
    else:
        for col,title in zip([p1,p2,p3,p4],["평가금액","평가손익","예수금","보유종목"]):
            with col: st.markdown(_html_card(title,"계좌 연결 대기","포트폴리오에서 계좌를 연결하세요"),unsafe_allow_html=True)

    left,right=st.columns([1.15,1])
    with left:
        st.markdown('<div class="sd-panel"><div class="sd-panel-title">포트폴리오 비중</div><div class="sd-panel-sub">보유 국내주식 평가액 기준</div>',unsafe_allow_html=True)
        if positions:
            st.markdown(_portfolio_donut(positions),unsafe_allow_html=True)
            for p in sorted(positions,key=lambda x:float(x.get("weight",0)),reverse=True)[:6]:
                st.markdown(f'''<div class="sd-holding"><div><div class="sd-holding-name">{p.get("name","")}</div><div class="sd-holding-meta">{p.get("code","")}</div></div><div class="sd-holding-value">{float(p.get("weight",0)):.1f}%</div></div>''',unsafe_allow_html=True)
        else:
            st.markdown('<div class="sd-empty">아직 계좌 데이터가 없습니다.<br><br>포트폴리오 메뉴에서 계좌를 연결하면 실제 보유 비중과 원형 차트가 자동으로 표시됩니다.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sd-panel"><div class="sd-panel-title">관심종목</div><div class="sd-panel-sub">저장된 종목의 최근 분석 상태</div>',unsafe_allow_html=True)
        watch=[x for x in choices.values() if x.get("code")!="SAMPLE"]
        if watch:
            for x in watch[:7]:
                report_x=x.get("report") or {}
                price=report_x.get("price")
                val=f"{price:,.0f}원" if isinstance(price,(int,float)) else "분석 대기"
                st.markdown(f'''<div class="sd-holding"><div><div class="sd-holding-name">{x.get("name","")}</div><div class="sd-holding-meta">{x.get("code","") if not str(x.get("code","")).startswith("pending-") else "코드 확인 대기"}</div></div><div class="sd-holding-value">{val}</div></div>''',unsafe_allow_html=True)
        else:
            st.markdown('<div class="sd-empty">저장된 관심종목이 없습니다.<br><br>관심 종목 메뉴에서 종목을 추가하세요.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="sd-section">최근 공시</div>',unsafe_allow_html=True)
    if latest_stock and latest_stock.get("report"):
        notices=sorted(latest_stock["report"].get("disclosures",[]),key=lambda x:x.get("date",""),reverse=True)
        if notices:
            for item in notices[:5]:
                st.link_button(item["date"]+" · "+item["title"],item["url"],use_container_width=True)
        else:
            st.markdown('<div class="sd-empty">선택 종목의 최근 공시가 없습니다.</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="sd-empty">종목을 검색하면 해당 기업의 공식 공시가 이 영역에 표시됩니다.</div>',unsafe_allow_html=True)


def render_home():
    hero(
        "시장을 읽고, 더 나은 판단을 만듭니다.",
        "공시·재무·시세를 한 흐름으로 연결하고, 새 기관 API가 추가될수록 시장·수급·산업 분석이 확장됩니다.",
    )
    global_search()

    st.subheader("시장 스냅샷")
    cols = st.columns(4)
    market_cards = [
        ("KOSPI", "데이터 연결 필요", "market.index"),
        ("KOSDAQ", "데이터 연결 필요", "market.index"),
        ("외국인 수급", "데이터 연결 필요", "market.investor_flow"),
        ("원/달러", "데이터 연결 필요", "macro.fx"),
    ]
    for col, (title, value, cap) in zip(cols, market_cards):
        with col:
            card(title, value, f"필요 Capability · {cap}")

    left, right = st.columns([2, 1])
    with left:
        with st.container(border=True):
            st.subheader("주요 지수 추이")
            empty_state(
                "시장 시계열 API 연결 대기",
                "지수 API가 연결되면 KOSPI·KOSDAQ과 주요 시장 흐름을 이 영역에 표시합니다. 가상 지수는 넣지 않습니다.",
            )
    with right:
        with st.container(border=True):
            st.subheader("오늘의 주요 변화")
            if report and not is_demo:
                notices = sorted(report.get("disclosures", []), key=lambda x: x.get("date", ""), reverse=True)
                if notices:
                    for item in notices[:4]:
                        st.link_button(item["date"] + " · " + item["title"], item["url"], use_container_width=True)
                else:
                    st.caption("선택 종목의 최근 공시가 수집되지 않았습니다.")
            else:
                empty_state("종목을 검색해 시작", "검색 후 선택 종목의 최신 공시와 핵심 변화를 여기에 모읍니다.")

    st.subheader("내 분석 포커스")
    if report:
        result = brief(report)
        fair = result.get("fair")
        cols = st.columns(4)
        with cols[0]:
            card("현재 선택", stock["name"], stock_label(stock))
        with cols[1]:
            card("성장", result["growth"], "확정 결산 기반")
        with cols[2]:
            card("가치 상태", result["value"], "역사적 배수 참고")
        with cols[3]:
            value = f"{fair['base']:,.0f}원" if fair else "자료 부족"
            card("적정가 참고", value, "목표주가가 아닌 참고값")
    else:
        empty_state("아직 분석된 종목이 없습니다", "상단 검색에서 종목을 선택하면 기업·재무·공시 분석이 저장됩니다.")

    st.subheader("확장 준비")
    c1, c2, c3 = st.columns(3)
    with c1:
        card("상승률 TOP", "API 연결 대기", "market ranking")
    with c2:
        card("거래대금 TOP", "API 연결 대기", "market turnover")
    with c3:
        ai = stock.get("ai_brief", {})
        if ai.get("status") == "ok":
            card("AI 인사이트", "분석 준비됨", "수집 데이터 해설")
        else:
            card("AI 인사이트", "선택 기능", "OPENAI API 연결 시 활성화")


def render_market():
    hero("시장 현황", "지수·거래대금·시장 폭·투자자 수급을 한 화면으로 연결하는 영역입니다.", "MARKET")
    caps = active_capabilities()
    source_badge(f"현재 활성 Capability {len(caps)}개", "ok" if caps else "wait")
    st.markdown("")
    rows = [
        ("시장 지수", "market.index", "KOSPI·KOSDAQ 지수와 등락"),
        ("시장 폭", "market.breadth", "상승·하락 종목 수와 확산도"),
        ("거래대금", "market.turnover", "시장/종목 거래대금"),
        ("투자자 수급", "market.investor_flow", "외국인·기관·개인 순매수"),
        ("업종", "sector.performance", "업종별 등락과 주도 섹터"),
        ("환율", "macro.fx", "원/달러 등 거시 변수"),
    ]
    for title, cap, desc in rows:
        with st.container(border=True):
            a, b = st.columns([2, 5])
            with a:
                st.markdown(f"**{title}**")
                source_badge("연결됨" if cap in caps else "기관 API 필요", "ok" if cap in caps else "wait")
            with b:
                st.write(desc)
                st.caption(cap)


def render_stock():
    title = stock["name"] + (" · 가상 예시" if is_demo else " · " + ("코드 확인 대기" if stock["code"].startswith("pending-") else stock["code"]))
    hero(title, "기업 특징 → 실적 → 가치 → 공시 → 다음 확인 질문 순서로 읽습니다.", "STOCK 360")
    global_search()

    if not is_demo:
        b1, b2 = st.columns([1, 5])
        with b1:
            if st.button("최신 데이터", type="primary", use_container_width=True):
                run_analysis(stock["code"])
        with b2:
            if st.session_state.get("save_notice"):
                st.caption(st.session_state.save_notice)

    if stock.get("analysis_error"):
        st.warning(stock["analysis_error"])
        snapshot = stock.get("price_snapshot")
        if snapshot:
            st.metric("조회된 기준 종가", f"{snapshot['price']:,.0f}원")
            st.caption("시세 기준일: " + snapshot["date"])

    if not report:
        empty_state("기업·재무 자료 없음", "관심종목과 투자일지는 사용할 수 있습니다. 데이터가 없으면 임의 분석값을 만들지 않습니다.")
        return

    result = brief(report)
    fair = result["fair"]
    company = report.get("company", {})
    sectors = result["sectors"]
    sentences = extract_business_sentences(report)

    st.caption(
        f"시세 {report.get('price_date','')} · 결산 {report['years'][-1]['year']} · "
        f"{report.get('basis','')} · 조회 {report.get('fetched','')}"
    )
    if report.get("sample"):
        st.warning("가상 종목·숫자입니다. 실제 투자 판단에 사용하지 마세요.")

    tabs = st.tabs(["한눈에 분석", "기업·섹터", "공시", "투자일지"])
    with tabs[0]:
        cols = st.columns(4)
        cols[0].metric("기준 종가", f"{report['price']:,.0f}원")
        cols[1].metric("성장", result["growth"])
        cols[2].metric("가치 상태", result["value"])
        cols[3].metric("적정주가 참고", f"{fair['base']:,.0f}원" if fair else "자료 부족")

        left, right = st.columns([2, 1])
        with left:
            with st.container(border=True):
                st.subheader("이 기업은 무엇을 하나요?")
                if sentences:
                    for sentence in sentences:
                        st.write("• " + sentence)
                elif report.get("business_excerpt"):
                    st.info("사업 원문은 수집됐지만 요약할 설명 문장을 찾지 못했습니다.")
                else:
                    st.info("사업 원문이 아직 수집되지 않았습니다.")
                st.caption(f"사업보고서 발췌 · {report['years'][-1]['year']}년 결산 기준")
        with right:
            with st.container(border=True):
                st.subheader("사업 키워드")
                st.write(" · ".join(x["sector"] for x in sectors) if sectors else "분류 대기")
                st.caption("공시 원문 키워드 후보이며 공식 주력 섹터 확정이 아닙니다.")
                st.write("업종코드 · " + str(company.get("induty_code", "미수집")))

        st.subheader("실적 변화")
        chart = pd.DataFrame(report["years"])[["year", "revenue", "profit"]].rename(
            columns={"year": "연도", "revenue": "매출", "profit": "영업이익"}
        )
        chart["연도"] = chart["연도"].astype(str)
        st.bar_chart(chart.set_index("연도"), color=["#2563EB", "#10B981"])
        st.dataframe(chart, hide_index=True, use_container_width=True)
        st.caption("단위 억원 · 확정 결산 기준. 분기 실적이나 미래 전망을 대신하지 않습니다.")

        st.subheader("판단 근거")
        m1, m2, m3 = st.columns(3)
        m1.metric("매출 성장률", f"{result['revenue_growth']:+.1f}%" if result["revenue_growth"] is not None else "자료 부족")
        m2.metric("영업이익 성장률", f"{result['profit_growth']:+.1f}%" if result["profit_growth"] is not None else "자료 부족")
        m3.metric("영업이익률", f"{result['margin']:.1f}%" if result["margin"] is not None else "자료 부족")

        if fair:
            f1, f2, f3 = st.columns(3)
            f1.metric("역사적 낮은 범위", f"{fair['low']:,.0f}원")
            f2.metric("역사적 중간 참고", f"{fair['base']:,.0f}원")
            f3.metric("역사적 높은 범위", f"{fair['high']:,.0f}원")
            st.caption(f"중간 참고값 대비 현재 가격 차이 {fair['gap']:+.1f}% · 매수/매도 신호가 아닙니다.")
        st.write(result["fair_reason"])

        ai = stock.get("ai_brief")
        if ai and ai.get("status") == "ok":
            with st.expander("AI 핵심 해설"):
                st.markdown(ai["text"])
                st.caption("공식 데이터·공시 발췌 기반 해설 · 원문 대조 필요")

    with tabs[1]:
        st.subheader("기업 핵심 분석")
        st.write(result["summary"])
        if company:
            st.caption("DART 기업명 · " + str(company.get("corp_name", "")) + " / 업종코드 · " + str(company.get("induty_code", "")))
        excerpt = report.get("business_excerpt", "")
        if excerpt:
            with st.container(border=True):
                st.write(excerpt[:2200] + ("…" if len(excerpt) > 2200 else ""))
            with st.expander("사업보고서 발췌 전체 보기"):
                st.text(excerpt)
        if sectors:
            st.subheader("섹터 후보와 확인 지표")
            for sector in sectors:
                with st.container(border=True):
                    st.markdown("**" + sector["sector"] + "**")
                    st.write(sector["logic"])
                    st.write("확인할 지표 · " + " · ".join(sector["signals"]))
                    st.caption("원문 발견 단어 · " + ", ".join(sector["keywords"]))

    with tabs[2]:
        st.subheader("최근 공시")
        st.caption("현재 수집본 기준이며 실시간 뉴스 전체를 뜻하지 않습니다.")
        notices = sorted(report.get("disclosures", []), key=lambda x: x.get("date", ""), reverse=True)
        if notices:
            for item in notices[:12]:
                st.link_button(item["date"] + " · " + item["title"], item["url"], use_container_width=True)
        else:
            empty_state("최근 공시 없음", "현재 수집본에 공시가 없으며, 공시가 없다는 확정 판단은 아닙니다.")

    with tabs[3]:
        if is_demo:
            st.info("실제 종목을 분석하면 투자일지와 분석 이력을 저장할 수 있습니다.")
        else:
            with st.form("note"):
                kind = st.selectbox("내 종목 구분", ["관심", "보유"], index=1 if stock.get("kind") == "보유" else 0)
                note = st.text_area("나의 판단 · 다음 확인 조건")
                if st.form_submit_button("기록 저장", type="primary"):
                    try:
                        store.save_stock({"code": stock["code"], "kind": kind})
                        store.log(
                            "journal",
                            {
                                "code": stock["code"],
                                "at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
                                "kind": "note",
                                "note": note,
                            },
                        )
                        st.session_state.pop("latest_analysis", None)
                        st.rerun()
                    except Exception:
                        st.error("기록 저장 실패. 입력 내용을 복사해 보관하세요.")

            st.download_button(
                "현재 분석 JSON 다운로드",
                json.dumps(stock, ensure_ascii=False, indent=2),
                file_name=stock["code"] + "-analysis.json",
                mime="application/json",
            )
            history = [item for item in state.get("journal", []) if item["code"] == stock["code"]]
            for item in reversed(history):
                with st.expander(item["at"] + " · " + item["kind"]):
                    if item.get("note"):
                        st.write(item["note"])
                    elif item.get("automatic_brief"):
                        st.write(item["automatic_brief"]["summary"])
                        st.caption("시세 기준일 · " + item.get("report", {}).get("price_date", ""))


def render_disclosures():
    hero("공시 분석", "실적·수주·투자·자본조달 등 기업의 공식 변화를 먼저 확인합니다.", "DART")
    global_search()
    if not report:
        empty_state("분석할 공시가 없습니다", "종목을 검색해 공식 공시 데이터를 먼저 수집하세요.")
        return
    notices = sorted(report.get("disclosures", []), key=lambda x: x.get("date", ""), reverse=True)
    st.subheader(stock["name"] + " · 최근 공시")
    if notices:
        for item in notices[:20]:
            with st.container(border=True):
                a, b = st.columns([1, 6])
                with a:
                    st.markdown("**" + item["date"] + "**")
                with b:
                    st.write(item["title"])
                    st.link_button("공시 원문", item["url"])
    else:
        empty_state("현재 수집 공시 없음", "공시 수집 범위와 기준일을 확인하세요.")


def render_watchlist():
    hero("관심 종목", "분석이 끝나지 않아도 저장하고, 다음 확인 조건을 남길 수 있습니다.", "WATCHLIST")
    if sample_mode:
        st.info("APP_PASSWORD 설정 후 개인 관심종목 저장이 활성화됩니다.")
        return

    with st.container(border=True):
        st.subheader("관심종목 추가")
        with st.form("save_watch_only"):
            name = st.text_input("종목명", placeholder="예: 삼성전자")
            code = st.text_input("종목코드", placeholder="선택 · 6자리", max_chars=6)
            if st.form_submit_button("관심종목 저장", type="primary"):
                name, code = name.strip(), code.strip()
                if not name or (code and (len(code) != 6 or not code.isascii() or not code.isdigit())):
                    st.error("종목명을 입력하고, 코드는 생략하거나 숫자 6자리로 입력하세요.")
                else:
                    existing = next((s for s in state["stocks"] if s["name"].casefold() == name.casefold()), {})
                    identity = existing.get("code") or code or "pending-" + hashlib.sha256(name.casefold().encode()).hexdigest()[:16]
                    try:
                        store.save_stock({"code": identity, "name": name, "kind": existing.get("kind", "관심")})
                        st.session_state.selected_code = identity
                        st.rerun()
                    except Exception:
                        st.error("관심종목 저장에 실패했습니다.")

    st.subheader("저장된 종목")
    if choices:
        rows = []
        for item in choices.values():
            if item.get("code") == "SAMPLE":
                continue
            rows.append(
                {
                    "종목": item.get("name", ""),
                    "코드": "확인 대기" if item["code"].startswith("pending-") else item["code"],
                    "구분": item.get("kind", "관심"),
                    "최근 분석": item.get("analyzed_at", "")[:16].replace("T", " "),
                    "상태": "분석 필요" if not item.get("report") else "분석 저장됨",
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            empty_state("관심종목 없음", "위 입력창에서 첫 종목을 추가하세요.")
    else:
        empty_state("관심종목 없음", "위 입력창에서 첫 종목을 추가하세요.")


def render_ai():
    hero("AI 인사이트", "AI는 숫자를 만들지 않고 수집된 공식 데이터의 변화와 의미를 설명합니다.", "AI")
    if not report:
        empty_state("분석 데이터가 필요합니다", "종목 분석을 먼저 실행한 뒤 AI 해설을 확인하세요.")
        return
    ai = stock.get("ai_brief")
    if ai and ai.get("status") == "ok":
        st.subheader(stock["name"] + " · 핵심 해설")
        st.markdown(ai["text"])
        st.caption("AI 해설 · 공식 데이터와 공시 발췌 기반 · 원문 대조 필요")
    else:
        empty_state(
            "AI 해설 미연결",
            "OPENAI_API_KEY와 사용 가능한 OPENAI_MODEL이 설정되면 종목 분석 시 공식 데이터 기반 해설을 함께 생성합니다.",
        )


def render_sources():
    hero("데이터 연결 관리", "기관 API의 인증·응답·사용 가능 기능을 한 곳에서 확인합니다.", "DATA SOURCES")
    st.caption("키 값 자체는 화면에 표시하지 않습니다.")

    if st.button("전체 연결 진단", type="primary"):
        with st.spinner("기관 API 상태를 확인합니다…"):
            st.session_state.provider_health = health_all()

    health_by_id = {row["provider_id"]: row for row in st.session_state.get("provider_health", [])}
    for spec in PROVIDERS:
        check = health_by_id.get(spec.provider_id)
        with st.container(border=True):
            left, right = st.columns([2, 5])
            with left:
                st.subheader(spec.name)
                if not check:
                    source_badge("진단 전", "wait")
                elif check["status"] == "ok":
                    source_badge("정상", "ok")
                elif check["status"] == "not_configured":
                    source_badge("인증정보 필요", "wait")
                else:
                    source_badge("확인 필요", "bad")
            with right:
                st.markdown("**사용 가능 기능**")
                st.write(" · ".join(spec.capabilities))
                if check:
                    st.caption(
                        f"{check['detail']} · 응답 {check['latency_ms']}ms · 확인 {check['checked_at']}"
                    )

    st.subheader("추가 기관 API 슬롯")
    empty_state(
        "Adapter Registry 준비됨",
        "새 기관 API는 기관명·문서·인증정보를 받으면 Capability를 분류한 뒤 독립 Adapter로 연결합니다.",
    )


def render_placeholder(title, subtitle, required):
    hero(title, subtitle, title.upper())
    caps = active_capabilities()
    for name, cap, desc in required:
        with st.container(border=True):
            a, b = st.columns([2, 5])
            with a:
                st.markdown("**" + name + "**")
                source_badge("연결됨" if cap in caps else "API 연결 대기", "ok" if cap in caps else "wait")
            with b:
                st.write(desc)
                st.caption(cap)


if nav == "대시보드":
    render_dashboard()
elif nav == "포트폴리오":
    render_portfolio(store, sample_mode)
elif nav == "교육자료":
    render_education()
else:
    st.header("설정과 추가 도구")
    st.caption("계좌 연결 없이도 내 종목을 추가하고 조사 결과를 확인할 수 있습니다.")
    options = ["사용 안내", "데이터 연결 관리", "종목 분석", "공시 분석", "시장 현황", "테마 & 섹터"]
    previous = st.session_state.get("advanced_page", "사용 안내")
    if previous not in options: st.session_state.advanced_page = "사용 안내"
    page = st.selectbox("필요한 도구", options, key="advanced_page")
    if page == "사용 안내":
        st.markdown("**1. 내 종목**에서 기업 이름을 추가하세요.\n\n**2. 조사 요청**을 열어 요청문을 이 채팅에 보내세요.\n\n**3. 종목을 선택**해 핵심 요약과 자세한 근거를 확인하세요.")
        st.link_button("상세 사용 안내", "https://github.com/planxs-ai/stock-dash/blob/main/CHAT-RESEARCH.md")
    elif page == "데이터 연결 관리": render_sources()
    elif page == "종목 분석": render_stock()
    elif page == "공시 분석": render_disclosures()
    elif page == "시장 현황": render_market()
    else:
        render_placeholder("테마 & 섹터", "산업별 흐름을 확인합니다.", [("업종 강도", "sector.performance", "업종별 등락과 거래대금"), ("업종 수급", "sector.flow", "외국인·기관 자금 흐름"), ("산업 수출", "industry.export", "품목별 수출 변화")])
