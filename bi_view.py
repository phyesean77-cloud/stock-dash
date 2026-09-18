"""Portfolio BI views built only from stored reports and account snapshots."""
from collections import defaultdict
import html

import requests
import altair as alt
import pandas as pd
import streamlit as st

GOLD = '#b1883c'
TEAL = '#37867b'
INK = '#493e2f'


def theme():
    st.markdown('''<style>
    .stApp{background:#F5F8FC;color:#14213D}
    [data-testid="stSidebar"]{background:#FFFFFF!important;border-right:1px solid #E5EAF2}
    [data-testid="stSidebar"] *{color:#4B5B73!important}
    .block-container{max-width:1500px;padding-top:1.1rem}
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#E5EAF2!important;border-radius:16px!important;background:#FFFFFF}
    [data-testid="stMetric"]{background:#FFFFFF;border:1px solid #E5EAF2;border-radius:14px;padding:18px 20px;box-shadow:0 5px 18px rgba(28,48,80,.03)}
    [data-testid="stMetricLabel"]{color:#718096}
    [data-testid="stMetricValue"]{font-family:inherit;color:#14213D;font-weight:800}
    .stButton>button[kind="primary"]{background:#2563EB;border-color:#2563EB;color:white}
    .px-eyebrow{font-size:13px;letter-spacing:2px;color:#2563EB;margin:0 0 5px}
    .px-business{padding:20px 22px;border-left:3px solid #2563EB;background:#EFF6FF;border-radius:0 12px 12px 0;font-size:16px;line-height:1.8}
    .home-section-title{margin:8px 0 18px}.home-section-title span,.panel-kicker{font-size:11px;font-weight:800;letter-spacing:2px;color:#2563EB}.home-section-title h2{font-size:30px;margin:2px 0 0}.stat-card{background:#fff;border:1px solid #E5EAF2;border-radius:16px;padding:20px 22px;min-height:112px;box-shadow:0 8px 24px rgba(37,99,235,.05)}.stat-label{font-size:13px;color:#718096}.stat-value{font-size:25px;font-weight:800;color:#14213D;margin-top:9px;letter-spacing:-.04em}.stat-sub{font-size:12px;color:#94A3B8;margin-top:7px}.stat-sub.up,.watch-value.up{color:#DC2626}.stat-sub.down,.watch-value.down{color:#2563EB}.panel-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}.panel-head h3{margin:2px 0 0;font-size:18px}.watch-row,.research-row{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #EEF2F7;padding:13px 0}.watch-row:last-child,.research-row:last-child{border-bottom:0}.watch-row strong,.research-row strong{font-size:14px;color:#1E293B}.watch-row small{display:block;color:#94A3B8;font-size:11px;margin-top:3px}.watch-value{text-align:right;font-size:14px;font-weight:800;color:#64748B}.watch-value small{display:block;color:#94A3B8;font-size:10px;font-weight:500;margin-top:3px}.research-row span{font-size:11px;color:#94A3B8}
    h1,h2,h3{color:#14213D!important;letter-spacing:-.03em}
    </style>''', unsafe_allow_html=True)


def draw(chart):
    st.altair_chart(chart.configure(background='#fffdf9').configure_view(stroke=None)
                    .configure_axis(labelColor=INK,titleColor=INK,gridColor='#eee8dd',labelFontSize=13,titleFontSize=13)
                    .configure_legend(labelColor=INK,titleColor=INK,labelFontSize=13), use_container_width=True)


def _fmt_money(value):
    try:
        return f"{float(value):,.0f}원"
    except Exception:
        return "-"


def _trend_class(value):
    try:
        return "up" if float(value) >= 0 else "down"
    except Exception:
        return "neutral"


@st.cache_data(ttl=300, show_spinner=False)
def _major_indices():
    """Fetch major market indices from Yahoo Finance chart data."""
    symbols = [
        ("KOSPI", "코스피", "^KS11"),
        ("KOSDAQ", "코스닥", "^KQ11"),
        ("S&P 500", "S&P 500", "^GSPC"),
        ("NASDAQ", "나스닥", "^IXIC"),
        ("Dow", "다우존스", "^DJI"),
        ("Nikkei 225", "닛케이 225", "^N225"),
    ]
    rows = []
    for key, label, symbol in symbols:
        try:
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"range": "5d", "interval": "1d", "events": "history"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5,
            )
            response.raise_for_status()
            meta = response.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            previous = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price is None:
                continue
            change = float(price) - float(previous) if previous is not None else None
            pct = (change / float(previous) * 100) if previous else None
            rows.append({
                "key": key,
                "label": label,
                "price": float(price),
                "change": change,
                "pct": pct,
            })
        except Exception:
            continue
    return rows

def _render_major_indices():
    """Render the major market indices near the top of the dashboard."""
    with st.container(border=True):
        st.markdown(
            '<div class="panel-head"><div><span class="panel-kicker">MARKET INDEX</span>'
            '<h3>주요 지수</h3></div><span style="font-size:11px;color:#94A3B8;">5분 캐시</span></div>',
            unsafe_allow_html=True,
        )
        indices = _major_indices()
        if indices:
            index_cols = st.columns(len(indices), gap="small")
            for col, item in zip(index_cols, indices):
                with col:
                    pct = item["pct"]
                    change = item["change"]
                    cls = _trend_class(pct)
                    pct_text = f"{pct:+.2f}%" if pct is not None else "-"
                    change_text = f"{change:+,.2f}" if change is not None else "-"
                    st.markdown(
                        f'<div class="stat-card" style="min-height:100px;padding:15px 16px;">'
                        f'<div class="stat-label">{html.escape(item["label"])}</div>'
                        f'<div class="stat-value" style="font-size:21px;margin-top:6px;">{item["price"]:,.2f}</div>'
                        f'<div class="stat-sub {cls}" style="font-weight:700;">{change_text} ({pct_text})</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("주요 지수 데이터를 불러오지 못했습니다.")
        st.caption("KOSPI · KOSDAQ · S&P 500 · NASDAQ · Dow · Nikkei 225 · Yahoo Finance 기준")


def overview(details, snapshot):
    """Bright, glanceable home dashboard.

    All figures come from the stored research/account snapshot; no values are fabricated.
    """
    reports = [r for _, r, _, _ in details.values() if r]
    positions = (snapshot or {}).get("positions", [])

    # ---------- top summary ----------
    st.markdown(
        '<div class="home-section-title"><span>MY DASHBOARD</span><h2>내 투자 현황</h2></div>',
        unsafe_allow_html=True,
    )

    # 주요 지수는 홈 화면 최상단에서 한눈에 확인합니다.
    _render_major_indices()

    if positions:
        value = sum(float(p.get("value", 0) or 0) for p in positions)
        pnl = sum(float(p.get("pnl", 0) or 0) for p in positions)
        cost = value - pnl
        pnl_pct = pnl / cost * 100 if cost else 0
        cards = [
            ("총 평가금액", _fmt_money(value), "계좌 조회 기준"),
            ("평가손익", f"{pnl:+,.0f}원", f"{pnl_pct:+.1f}%", _trend_class(pnl)),
            ("보유 종목", f"{len(positions)}개", f"관심종목 {len(details)}개"),
            ("조사 완료", f"{len(reports)}개", f"추가 조사 {max(0, len(details)-len(reports))}개"),
        ]
    else:
        cards = [
            ("관심종목", f"{len(details)}개", "내 관심 목록"),
            ("조사 완료", f"{len(reports)}개", f"추가 조사 {max(0, len(details)-len(reports))}개"),
            ("계좌 연결", "연결 필요", "보유자산을 보려면 계좌 연결"),
            ("데이터 상태", "정상", "저장된 조사자료 기준"),
        ]

    cols = st.columns(4, gap="medium")
    for i, item in enumerate(cards):
        with cols[i]:
            title, value, sub, *tone = item
            cls = tone[0] if tone else "neutral"
            st.markdown(
                f'<div class="stat-card"><div class="stat-label">{html.escape(title)}</div>'
                f'<div class="stat-value">{html.escape(value)}</div>'
                f'<div class="stat-sub {cls}">{html.escape(sub)}</div></div>',
                unsafe_allow_html=True,
            )

    # ---------- middle row ----------
    left, right = st.columns([1.75, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-head"><div><span class="panel-kicker">PERFORMANCE</span><h3>관심종목 실적 흐름</h3></div></div>', unsafe_allow_html=True)
            groups = defaultdict(list)
            for r in reports:
                f = r.get("financial")
                if f:
                    key = (f.get("period"), f.get("prior_period"), f.get("basis"), f.get("currency"), f.get("unit"))
                    groups[key].append((r, f))

            if not groups:
                st.info("종목 조사 결과가 들어오면 실적 흐름이 표시됩니다.")
            else:
                keys = list(groups)
                key = (
                    st.selectbox(
                        "비교 기간·기준",
                        keys,
                        format_func=lambda k: f"{k[0]} 누적 / 전년 {k[1]} · {k[2]}",
                        key="bi_period",
                        label_visibility="collapsed",
                    )
                    if len(keys) > 1
                    else keys[0]
                )
                bars = []
                for r, f in groups[key]:
                    prior = float(f.get("prior_operating_profit", 0) or 0)
                    now = float(f.get("operating_profit", 0) or 0)
                    if prior > 0:
                        bars.append({"종목": r.get("name", ""), "증가율": (now / prior - 1) * 100})
                if bars:
                    df = pd.DataFrame(bars).sort_values("증가율", ascending=False)
                    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=5, size=24).encode(
                        x=alt.X("증가율:Q", title="영업이익 증가율 (%)", axis=alt.Axis(format="+.0f")),
                        y=alt.Y("종목:N", sort="-x", title=None),
                        color=alt.condition(
                            alt.datum.증가율 >= 0,
                            alt.value("#2563EB"),
                            alt.value("#94A3B8"),
                        ),
                        tooltip=[
                            alt.Tooltip("종목:N"),
                            alt.Tooltip("증가율:Q", format="+.1f", title="증가율"),
                        ],
                    ).properties(height=max(250, min(390, len(df) * 42)))
                    draw(chart)
                else:
                    st.info("비교 가능한 전년 영업이익 자료가 없습니다.")
                st.caption(f"{key[0]} / {key[1]} · {key[2]} · 같은 기준의 조사자료만 비교")

    with right:
        with st.container(border=True):
            st.markdown('<div class="panel-head"><div><span class="panel-kicker">WATCHLIST</span><h3>관심 종목</h3></div></div>', unsafe_allow_html=True)
            items = []
            for key, (stock, r, trend, frame) in details.items():
                f = r.get("financial") if r else None
                growth_value = None
                if f:
                    try:
                        prior = float(f.get("operating_profit", 0) or 0)
                        before = float(f.get("prior_operating_profit", 0) or 0)
                        if before:
                            growth_value = (prior / before - 1) * 100
                    except Exception:
                        pass
                items.append((stock.get("name", ""), trend.get("daily", "-"), growth_value))

            if items:
                for name, daily, growth_value in items[:8]:
                    growth_text = f"{growth_value:+.1f}%" if growth_value is not None else "조사 필요"
                    cls = "up" if growth_value is not None and growth_value >= 0 else "neutral"
                    st.markdown(
                        f'<div class="watch-row"><div><strong>{html.escape(name)}</strong>'
                        f'<small>영업이익 성장</small></div><div class="watch-value {cls}">'
                        f'{html.escape(growth_text)}<small>일봉 {html.escape(str(daily))}</small></div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("관심종목을 추가해 주세요.")

    # ---------- bottom row ----------
    left2, mid2 = st.columns([1.35, 1], gap="large")

    with left2:
        with st.container(border=True):
            st.markdown('<div class="panel-head"><div><span class="panel-kicker">HOLDINGS</span><h3>보유 종목</h3></div></div>', unsafe_allow_html=True)
            if positions:
                df = pd.DataFrame([
                    {
                        "종목": p.get("name", ""),
                        "평가금액": float(p.get("value", 0) or 0),
                        "손익": float(p.get("pnl", 0) or 0),
                    }
                    for p in positions
                ])
                st.dataframe(
                    df.style.format({"평가금액": "{:,.0f}원", "손익": "{:+,.0f}원"}),
                    hide_index=True,
                    use_container_width=True,
                    height=min(320, 52 + len(df) * 35),
                )
            else:
                st.markdown("**계좌를 연결하면 보유 종목이 표시됩니다.**")
                st.caption("왼쪽 메뉴의 계좌 연결에서 조회할 수 있습니다.")

    with mid2:
        with st.container(border=True):
            st.markdown('<div class="panel-head"><div><span class="panel-kicker">ALLOCATION</span><h3>포트폴리오 비중</h3></div></div>', unsafe_allow_html=True)
            if positions:
                df = pd.DataFrame([
                    {"종목": p.get("name", ""), "평가액": float(p.get("value", 0) or 0)}
                    for p in positions if float(p.get("value", 0) or 0) > 0
                ])
                if not df.empty:
                    df["비중"] = df["평가액"] / df["평가액"].sum()
                    color = alt.Color(
                        "종목:N",
                        scale=alt.Scale(range=["#2563EB", "#60A5FA", "#93C5FD", "#CBD5E1", "#64748B", "#1E3A8A", "#1D4ED8", "#93C5FD"]),
                        legend=alt.Legend(orient="bottom", columns=2, title=None),
                    )
                    base = alt.Chart(df).encode(
                        theta=alt.Theta("평가액:Q", stack=True),
                        color=color,
                        tooltip=[
                            alt.Tooltip("종목:N", title="종목"),
                            alt.Tooltip("평가액:Q", format=",.0f", title="평가금액"),
                            alt.Tooltip("비중:Q", format=".1%", title="비중"),
                        ],
                    )
                    pie = base.mark_arc(innerRadius=52, outerRadius=88, stroke="#FFFFFF", strokeWidth=2)
                    labels = base.transform_filter(
                        alt.datum.비중 >= 0.04
                    ).mark_text(radius=108, fontSize=12, fontWeight="bold").encode(
                        text=alt.Text("비중:Q", format=".1%"),
                        color=alt.value("#14213D"),
                    )
                    chart = (pie + labels).properties(height=285)
                    draw(chart)
            else:
                st.caption("계좌 연결 후 종목별 평가금액 비중을 확인할 수 있습니다.")



def detail(r):
    a,b,c=st.columns([1.15,1,1],gap='large')
    with a,st.container(border=True):
        st.subheader('주력사업과 기업 특징')
        business=r.get('business') or r.get('summary')
        if business:st.markdown('<div class="px-business">'+html.escape(business['text'])+'</div>',unsafe_allow_html=True)
        else:st.info('사업 내용 조사 필요')
    with b,st.container(border=True):
        st.subheader('영업이익 변화')
        f=r.get('financial')
        if f:
            df=pd.DataFrame([{'기간':f['prior_period'],'영업이익':f['prior_operating_profit']},{'기간':f['period'],'영업이익':f['operating_profit']}])
            draw(alt.Chart(df).mark_bar(size=45,cornerRadiusTopLeft=4,cornerRadiusTopRight=4).encode(
                x=alt.X('기간:O',title=None,axis=alt.Axis(labelAngle=0)),y=alt.Y('영업이익:Q',title=f['unit']),
                color=alt.Color('기간:N',scale=alt.Scale(range=['#CBD5E1','#2563EB']),legend=None),tooltip=['기간',alt.Tooltip('영업이익:Q',format=',.1f')]).properties(height=210))
            margin=f['operating_profit']/f['revenue']*100 if f['revenue']>0 else None
            st.caption(f"{f['basis']} · {f['currency']} {f['unit']}"+(f' · 영업이익률 {margin:.1f}%' if margin is not None else ''))
        else:st.info('같은 기간의 전년·당년 실적이 필요합니다.')
    with c,st.container(border=True):
        st.subheader('가격과 가치의 거리')
        v=r.get('valuation')
        if v:
            df=pd.DataFrame([{'구분':label,'가격':v[k]} for k,label in [('low','낮은 참고가'),('base','기본 참고가'),('high','높은 참고가'),('current_price','비교 주가')]])
            draw(alt.Chart(df).mark_point(filled=True,size=130).encode(x=alt.X('가격:Q',title='원',scale=alt.Scale(zero=False)),y=alt.Y('구분:N',title=None),color=alt.value('#2563EB'),tooltip=['구분','가격']).properties(height=160))
            st.metric('기본 참고가',f"{v['base']:,.0f}원")
            st.caption(f"가격 기준일 {v['price_date']} · 평가 가정은 상세 탭에서 확인")
        else:
            st.write('**평가 근거를 기다리고 있습니다.**')
            st.caption('현재 주가와 실적 전망, 적용 배수의 근거가 모이면 참고가 범위를 표시합니다.')


def peers_chart(peers):
    df=pd.DataFrame(peers['rows']).rename(columns={'name':'기업','operating_profit':'영업이익'})
    draw(alt.Chart(df).mark_bar(color='#2563EB',cornerRadiusEnd=4).encode(x=alt.X('영업이익:Q',title=peers['unit']),y=alt.Y('기업:N',sort='-x',title=None),tooltip=['기업',alt.Tooltip('영업이익:Q',format=',.1f')]).properties(height=max(150,min(400,len(df)*45))))
