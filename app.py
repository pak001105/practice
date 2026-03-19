import json
import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="서울시 자치구별 소음과 건강영향 지도",
    page_icon="🗺️",
    layout="wide"
)

# -----------------------------
# 커스텀 CSS
# -----------------------------
st.markdown("""
<style>
/* 카드형 메트릭 */
.metric-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px 20px;
    border-left: 5px solid #ccc;
    margin-bottom: 8px;
}
.metric-card.danger  { border-left-color: #ef476f; background: #fff5f7; }
.metric-card.warning { border-left-color: #ffd166; background: #fffdf0; }
.metric-card.ok      { border-left-color: #74c69d; background: #f0faf5; }

.metric-label { font-size: 0.78rem; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.metric-value { font-size: 1.7rem; font-weight: 800; color: #212529; line-height: 1.1; }
.metric-unit  { font-size: 0.85rem; color: #6c757d; font-weight: 400; margin-left: 3px; }
.metric-desc  { font-size: 0.78rem; color: #868e96; margin-top: 4px; }

/* 지역 뱃지 */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 12px;
}
.badge-주거지역 { background: #d3f9d8; color: #2f9e44; }
.badge-상권지역 { background: #fff3bf; color: #e67700; }
.badge-교통지역 { background: #ffe0e9; color: #c2255c; }

/* 정책 카드 */
.policy-card {
    background: white;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.policy-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }
.policy-text { font-size: 0.9rem; color: #343a40; line-height: 1.5; }

/* 구분선 */
.section-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #adb5bd;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 20px 0 10px 0;
}

/* 해석 박스 */
.interpret-box {
    background: #e7f5ff;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #1971c2;
    line-height: 1.7;
    margin-top: 8px;
}
.interpret-box b { color: #1864ab; }

/* 비교 바 */
.bar-wrap { margin: 4px 0 2px 0; }
.bar-bg { background: #e9ecef; border-radius: 4px; height: 8px; width: 100%; }
.bar-fill { height: 8px; border-radius: 4px; }
.bar-label { font-size: 0.75rem; color: #868e96; display: flex; justify-content: space-between; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 기본 데이터
# -----------------------------
district_data = pd.DataFrame([
    # 주거지역
    {"자치구": "노원구", "지역유형": "주거지역", "주간소음(dB)": 55.40, "야간소음(dB)": 47.30, "스트레스점수": 19.10, "PSQI": 6.30, "수면시간(시간)": 6.62},
    {"자치구": "은평구", "지역유형": "주거지역", "주간소음(dB)": 55.40, "야간소음(dB)": 47.30, "스트레스점수": 19.10, "PSQI": 6.30, "수면시간(시간)": 6.62},
    {"자치구": "양천구", "지역유형": "주거지역", "주간소음(dB)": 55.40, "야간소음(dB)": 47.30, "스트레스점수": 19.10, "PSQI": 6.30, "수면시간(시간)": 6.62},
    {"자치구": "도봉구", "지역유형": "주거지역", "주간소음(dB)": 55.40, "야간소음(dB)": 47.30, "스트레스점수": 19.10, "PSQI": 6.30, "수면시간(시간)": 6.62},
    {"자치구": "성북구", "지역유형": "주거지역", "주간소음(dB)": 55.40, "야간소음(dB)": 47.30, "스트레스점수": 19.10, "PSQI": 6.30, "수면시간(시간)": 6.62},

    # 상권지역
    {"자치구": "강남구", "지역유형": "상권지역", "주간소음(dB)": 63.86, "야간소음(dB)": 56.14, "스트레스점수": 23.86, "PSQI": 8.23, "수면시간(시간)": 5.93},
    {"자치구": "중구", "지역유형": "상권지역", "주간소음(dB)": 63.86, "야간소음(dB)": 56.14, "스트레스점수": 23.86, "PSQI": 8.23, "수면시간(시간)": 5.93},
    {"자치구": "마포구", "지역유형": "상권지역", "주간소음(dB)": 63.86, "야간소음(dB)": 56.14, "스트레스점수": 23.86, "PSQI": 8.23, "수면시간(시간)": 5.93},
    {"자치구": "영등포구", "지역유형": "상권지역", "주간소음(dB)": 63.86, "야간소음(dB)": 56.14, "스트레스점수": 23.86, "PSQI": 8.23, "수면시간(시간)": 5.93},
    {"자치구": "송파구", "지역유형": "상권지역", "주간소음(dB)": 63.86, "야간소음(dB)": 56.14, "스트레스점수": 23.86, "PSQI": 8.23, "수면시간(시간)": 5.93},

    # 교통지역
    {"자치구": "서초구", "지역유형": "교통지역", "주간소음(dB)": 76.22, "야간소음(dB)": 68.04, "스트레스점수": 32.30, "PSQI": 11.74, "수면시간(시간)": 4.99},
    {"자치구": "강서구", "지역유형": "교통지역", "주간소음(dB)": 76.22, "야간소음(dB)": 68.04, "스트레스점수": 32.30, "PSQI": 11.74, "수면시간(시간)": 4.99},
    {"자치구": "동대문구", "지역유형": "교통지역", "주간소음(dB)": 76.22, "야간소음(dB)": 68.04, "스트레스점수": 32.30, "PSQI": 11.74, "수면시간(시간)": 4.99},
    {"자치구": "광진구", "지역유형": "교통지역", "주간소음(dB)": 76.22, "야간소음(dB)": 68.04, "스트레스점수": 32.30, "PSQI": 11.74, "수면시간(시간)": 4.99},
    {"자치구": "구로구", "지역유형": "교통지역", "주간소음(dB)": 76.22, "야간소음(dB)": 68.04, "스트레스점수": 32.30, "PSQI": 11.74, "수면시간(시간)": 4.99},
])

policy_map = {
    "주거지역": [
        ("🏠", "생활소음 관리 강화", "층간소음·생활소음 민원 대응 체계 고도화 및 공동주택 관리 기준 강화"),
        ("🧱", "공동주택 차음 보강", "노후 공동주택 차음재 교체 지원 및 신축 건물 차음 성능 기준 상향"),
        ("🌙", "야간 공사시간 제한", "오후 10시 이후 공사 금지 구역 지정 및 소음 초과 업체 즉시 행정조치"),
    ],
    "상권지역": [
        ("🕐", "심야 영업구역 시간대별 소음관리", "업종별 심야 음향 출력 제한치 설정 및 자정 이후 클럽·주점 소음 집중 단속"),
        ("🛵", "배달 오토바이 소음 저감", "전기 이륜차 전환 인센티브 제공 및 이면도로 야간 저속 운행 구역 확대"),
        ("🚶", "보행친화 가로 설계", "차량 진입 제한 보행자 전용 시간대 운영 및 노상 소음 저감 식재·방음 벤치 설치"),
    ],
    "교통지역": [
        ("🚗", "30km/h 구간 확대", "간선도로 인접 이면도로 및 스쿨존 중심으로 제한속도 구간 단계적 확대"),
        ("🛣️", "저소음 포장 적용", "교통량 상위 도로 우선으로 흡음·저소음 포장재 교체 및 정기 유지보수 실시"),
        ("🚛", "화물차·버스 야간운행 관리", "오후 11시~오전 6시 대형차 특정 구간 통행 제한 및 우회경로 안내 시스템 운영"),
        ("🔇", "방음벽 및 방음창 지원", "소음 취약 주거지역 방음벽 설치 우선 지원 및 저소득 가구 방음창 교체 보조금 지급"),
    ]
}

# 지역유형별 해석 텍스트
region_interpret = {
    "주거지역": {
        "소음해석": "주간 <b>55 dB</b>는 WHO 권고 기준(<b>53 dB</b>)을 소폭 초과하는 수준입니다. 야간 소음도 기준치(<b>45 dB</b>)를 넘어 수면 방해 가능성이 있습니다.",
        "건강해석": "PSQI <b>6.3점</b>은 수면의 질 '경계' 구간(5점 초과 시 불량)에 해당합니다. 스트레스 지수는 세 유형 중 가장 낮으나 꾸준한 관리가 필요합니다.",
        "emoji": "🟢"
    },
    "상권지역": {
        "소음해석": "주간 <b>63.9 dB</b>는 일상 대화 수준을 넘어서는 소음입니다. 야간에도 <b>56 dB</b>로 수면 장애 위험이 높은 편입니다.",
        "건강해석": "PSQI <b>8.2점</b>은 수면 장애 구간입니다. 평균 수면시간이 <b>5.9시간</b>으로 권장 수면 7~9시간에 크게 미치지 못합니다.",
        "emoji": "🟡"
    },
    "교통지역": {
        "소음해석": "주간 <b>76.2 dB</b>는 전동공구 수준의 고소음입니다. 야간 <b>68 dB</b>는 WHO 야간 소음 권고치(<b>40 dB</b>)의 약 <b>1.7배</b>에 달합니다.",
        "건강해석": "PSQI <b>11.7점</b>은 심각한 수면 장애 구간입니다. 평균 수면시간이 <b>4.99시간</b>으로 만성 수면 부족 상태이며, 심혈관계 질환 위험이 높아집니다.",
        "emoji": "🔴"
    }
}

district_info = district_data.set_index("자치구").to_dict(orient="index")

# -----------------------------
# 서울 자치구 GeoJSON 불러오기
# -----------------------------
@st.cache_data(show_spinner=False)
def load_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()

geojson_data = load_seoul_geojson()

# -----------------------------
# GeoJSON 속 자치구 이름 추출
# -----------------------------
def extract_district_name(properties: dict) -> str:
    candidates = ["name","SIG_KOR_NM","SIGUNGU_NM","sggnm","sgg_nm","adm_nm"]
    for key in candidates:
        if key in properties and properties[key]:
            return str(properties[key]).strip()
    return "알 수 없음"

# -----------------------------
# 팝업 HTML 구성
# -----------------------------
for feature in geojson_data["features"]:
    props = feature.get("properties", {})
    district_name = extract_district_name(props)

    if district_name in district_info:
        row = district_info[district_name]
        policies = "<br>".join([f"• {p[1]}" for p in policy_map[row["지역유형"]]])

        color_map = {"주거지역": "#74c69d", "상권지역": "#ffd166", "교통지역": "#ef476f"}
        badge_color = color_map.get(row["지역유형"], "#adb5bd")

        popup_html = f"""
        <div style="width:280px; font-family: 'Noto Sans KR', sans-serif;">
            <div style="background:{badge_color}22; border-left:4px solid {badge_color}; padding:10px 12px; border-radius:6px; margin-bottom:10px;">
                <div style="font-size:1.1rem; font-weight:800; color:#212529;">{district_name}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">{row['지역유형']}</div>
            </div>
            <table style="width:100%; font-size:0.82rem; border-collapse:collapse;">
                <tr style="background:#f8f9fa;"><td style="padding:5px 8px; color:#6c757d;">🌞 주간소음</td><td style="padding:5px 8px; font-weight:700;">{row['주간소음(dB)']:.1f} dB</td></tr>
                <tr><td style="padding:5px 8px; color:#6c757d;">🌙 야간소음</td><td style="padding:5px 8px; font-weight:700;">{row['야간소음(dB)']:.1f} dB</td></tr>
                <tr style="background:#f8f9fa;"><td style="padding:5px 8px; color:#6c757d;">😰 스트레스</td><td style="padding:5px 8px; font-weight:700;">{row['스트레스점수']:.1f}점</td></tr>
                <tr><td style="padding:5px 8px; color:#6c757d;">😴 수면질(PSQI)</td><td style="padding:5px 8px; font-weight:700;">{row['PSQI']:.1f}점</td></tr>
                <tr style="background:#f8f9fa;"><td style="padding:5px 8px; color:#6c757d;">⏰ 수면시간</td><td style="padding:5px 8px; font-weight:700;">{row['수면시간(시간)']:.2f}시간</td></tr>
            </table>
            <div style="margin-top:10px; font-size:0.78rem; color:#6c757d; font-weight:600;">📋 정책 제안</div>
            <div style="font-size:0.8rem; color:#343a40; margin-top:4px; line-height:1.7;">{policies}</div>
        </div>
        """
        props["popup_html"] = popup_html
        props["district_name"] = district_name
        props["region_type"] = row["지역유형"]
    else:
        props["popup_html"] = f"""
        <div style="width:220px;">
            <h4>{district_name}</h4>
            연결된 데이터가 없습니다.
        </div>
        """
        props["district_name"] = district_name
        props["region_type"] = "미분류"

# -----------------------------
# 지도 색상
# -----------------------------
def get_fill_color(region_type: str) -> str:
    if region_type == "주거지역": return "#74c69d"
    if region_type == "상권지역": return "#ffd166"
    if region_type == "교통지역": return "#ef476f"
    return "#adb5bd"

def style_function(feature):
    region_type = feature["properties"].get("region_type", "미분류")
    return {"fillColor": get_fill_color(region_type), "color": "#333333", "weight": 1.2, "fillOpacity": 0.65}

def highlight_function(feature):
    return {"fillOpacity": 0.9, "weight": 2.5, "color": "#111111"}

# -----------------------------
# 제목
# -----------------------------
st.title("서울시 자치구별 소음과 건강영향 지도")
st.markdown("""
서울 지도에서 **자치구를 클릭하면 팝업창으로 소음, 스트레스, 수면지표, 정책 제안**을 볼 수 있습니다.  
현재 수치는 보고서 기반의 **시나리오형 자치구 대표값**입니다.
""")

# 범례
col_leg1, col_leg2, col_leg3, _ = st.columns([1, 1, 1, 3])
col_leg1.markdown("🟢 **주거지역** — 소음 낮음")
col_leg2.markdown("🟡 **상권지역** — 소음 보통")
col_leg3.markdown("🔴 **교통지역** — 소음 높음")

# -----------------------------
# 지도 생성
# -----------------------------
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB positron")

geojson_layer = folium.GeoJson(
    geojson_data,
    name="서울 자치구",
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["district_name", "region_type"],
        aliases=["자치구", "지역유형"],
        sticky=False
    ),
    popup=folium.GeoJsonPopup(
        fields=["popup_html"],
        labels=False,
        parse_html=True,
        max_width=320
    )
)

geojson_layer.add_to(m)
folium.LayerControl().add_to(m)

map_data = st_folium(m, width=None, height=700)

# -----------------------------
# 클릭한 자치구 상세 정보 (개선)
# -----------------------------
st.markdown("---")
st.subheader("📍 자치구 상세 분석")

clicked = None
if map_data and map_data.get("last_active_drawing"):
    clicked = map_data["last_active_drawing"].get("properties", {}).get("district_name")

if clicked and clicked in district_info:
    row = district_info[clicked]
    rtype = row["지역유형"]
    interp = region_interpret[rtype]

    # 자치구명 + 지역유형 뱃지
    st.markdown(f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.4rem; font-weight:800; color:#212529;">{clicked}</span>
        <span class="badge badge-{rtype}" style="margin-left:10px;">{rtype}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 소음 지표 ──────────────────────────────────
    st.markdown('<div class="section-title">🔊 소음 지표</div>', unsafe_allow_html=True)

    noise_col1, noise_col2 = st.columns(2)

    # 주간소음 바
    day_db = row["주간소음(dB)"]
    day_pct = min(int((day_db - 40) / (85 - 40) * 100), 100)
    day_cls = "danger" if day_db >= 70 else "warning" if day_db >= 60 else "ok"
    day_standard = "⚠️ WHO 기준 53 dB 초과" if day_db > 53 else "✅ WHO 기준 이하"

    with noise_col1:
        st.markdown(f"""
        <div class="metric-card {day_cls}">
            <div class="metric-label">🌞 주간소음</div>
            <div><span class="metric-value">{day_db:.1f}</span><span class="metric-unit">dB</span></div>
            <div class="bar-wrap">
                <div class="bar-bg"><div class="bar-fill" style="width:{day_pct}%; background:{'#ef476f' if day_cls=='danger' else '#ffd166' if day_cls=='warning' else '#74c69d'};"></div></div>
                <div class="bar-label"><span>40 dB</span><span>85 dB</span></div>
            </div>
            <div class="metric-desc">{day_standard}</div>
        </div>
        """, unsafe_allow_html=True)

    # 야간소음 바
    night_db = row["야간소음(dB)"]
    night_pct = min(int((night_db - 30) / (75 - 30) * 100), 100)
    night_cls = "danger" if night_db >= 60 else "warning" if night_db >= 45 else "ok"
    night_standard = "⚠️ WHO 야간 기준 40 dB 초과" if night_db > 40 else "✅ WHO 기준 이하"

    with noise_col2:
        st.markdown(f"""
        <div class="metric-card {night_cls}">
            <div class="metric-label">🌙 야간소음</div>
            <div><span class="metric-value">{night_db:.1f}</span><span class="metric-unit">dB</span></div>
            <div class="bar-wrap">
                <div class="bar-bg"><div class="bar-fill" style="width:{night_pct}%; background:{'#ef476f' if night_cls=='danger' else '#ffd166' if night_cls=='warning' else '#74c69d'};"></div></div>
                <div class="bar-label"><span>30 dB</span><span>75 dB</span></div>
            </div>
            <div class="metric-desc">{night_standard}</div>
        </div>
        """, unsafe_allow_html=True)

    # 소음 해석
    st.markdown(f'<div class="interpret-box">📌 {interp["소음해석"]}</div>', unsafe_allow_html=True)

    # ── 건강 지표 ──────────────────────────────────
    st.markdown('<div class="section-title">🧠 건강 지표</div>', unsafe_allow_html=True)

    health_col1, health_col2, health_col3 = st.columns(3)

    stress = row["스트레스점수"]
    stress_pct = min(int(stress / 40 * 100), 100)
    stress_cls = "danger" if stress >= 28 else "warning" if stress >= 20 else "ok"

    psqi = row["PSQI"]
    psqi_pct = min(int(psqi / 15 * 100), 100)
    psqi_cls = "danger" if psqi >= 10 else "warning" if psqi >= 5 else "ok"
    psqi_grade = "심각한 수면 장애" if psqi >= 10 else "수면 불량" if psqi >= 5 else "정상"

    sleep = row["수면시간(시간)"]
    sleep_pct = min(int(sleep / 9 * 100), 100)
    sleep_cls = "danger" if sleep < 5.5 else "warning" if sleep < 7 else "ok"
    sleep_grade = "만성 수면 부족" if sleep < 5.5 else "수면 부족" if sleep < 7 else "권장 수면"

    with health_col1:
        st.markdown(f"""
        <div class="metric-card {stress_cls}">
            <div class="metric-label">😰 스트레스 점수</div>
            <div><span class="metric-value">{stress:.1f}</span><span class="metric-unit">점</span></div>
            <div class="bar-wrap">
                <div class="bar-bg"><div class="bar-fill" style="width:{stress_pct}%; background:{'#ef476f' if stress_cls=='danger' else '#ffd166' if stress_cls=='warning' else '#74c69d'};"></div></div>
                <div class="bar-label"><span>0</span><span>40</span></div>
            </div>
            <div class="metric-desc">{'⚠️ 고위험' if stress >= 28 else '⚡ 주의 필요' if stress >= 20 else '✅ 양호'}</div>
        </div>
        """, unsafe_allow_html=True)

    with health_col2:
        st.markdown(f"""
        <div class="metric-card {psqi_cls}">
            <div class="metric-label">😴 수면질 (PSQI)</div>
            <div><span class="metric-value">{psqi:.1f}</span><span class="metric-unit">점</span></div>
            <div class="bar-wrap">
                <div class="bar-bg"><div class="bar-fill" style="width:{psqi_pct}%; background:{'#ef476f' if psqi_cls=='danger' else '#ffd166' if psqi_cls=='warning' else '#74c69d'};"></div></div>
                <div class="bar-label"><span>0</span><span>15</span></div>
            </div>
            <div class="metric-desc">{'⚠️ ' if psqi >= 5 else '✅ '}{psqi_grade}</div>
        </div>
        """, unsafe_allow_html=True)

    with health_col3:
        st.markdown(f"""
        <div class="metric-card {sleep_cls}">
            <div class="metric-label">⏰ 평균 수면시간</div>
            <div><span class="metric-value">{sleep:.2f}</span><span class="metric-unit">시간</span></div>
            <div class="bar-wrap">
                <div class="bar-bg"><div class="bar-fill" style="width:{sleep_pct}%; background:{'#74c69d' if sleep_cls=='ok' else '#ffd166' if sleep_cls=='warning' else '#ef476f'};"></div></div>
                <div class="bar-label"><span>0</span><span>9시간</span></div>
            </div>
            <div class="metric-desc">{'⚠️ ' if sleep < 7 else '✅ '}{sleep_grade}</div>
        </div>
        """, unsafe_allow_html=True)

    # 건강 해석
    st.markdown(f'<div class="interpret-box">📌 {interp["건강해석"]}</div>', unsafe_allow_html=True)

    # ── 정책 제안 ──────────────────────────────────
    st.markdown('<div class="section-title">📋 맞춤 정책 제안</div>', unsafe_allow_html=True)

    for icon, title, desc in policy_map[rtype]:
        st.markdown(f"""
        <div class="policy-card">
            <div class="policy-icon">{icon}</div>
            <div>
                <div style="font-weight:700; font-size:0.9rem; color:#212529; margin-bottom:3px;">{title}</div>
                <div class="policy-text" style="color:#6c757d;">{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("🗺️ 지도에서 자치구를 클릭하면 여기에 소음·건강 상세 분석과 정책 제안이 표시됩니다.")

# -----------------------------
# 전체 데이터 표
# -----------------------------
with st.expander("📊 전체 자치구 데이터 보기"):
    st.dataframe(district_data, use_container_width=True)
