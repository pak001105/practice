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
        "생활소음 관리 강화",
        "공동주택 차음 보강",
        "야간 공사시간 제한"
    ],
    "상권지역": [
        "심야 영업구역 시간대별 소음관리",
        "배달 오토바이 소음 저감",
        "보행친화 가로 설계"
    ],
    "교통지역": [
        "30km/h 구간 확대",
        "저소음 포장 적용",
        "화물차·버스 야간운행 관리",
        "방음벽 및 방음창 지원"
    ]
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
# GeoJSON 속 자치구 이름 추출 보조 함수
# -----------------------------
def extract_district_name(properties: dict) -> str:
    candidates = [
        "name",
        "SIG_KOR_NM",
        "SIGUNGU_NM",
        "sggnm",
        "sgg_nm",
        "adm_nm",
    ]
    for key in candidates:
        if key in properties and properties[key]:
            return str(properties[key]).strip()
    return "알 수 없음"

# -----------------------------
# 각 feature에 팝업 정보 붙이기
# -----------------------------
for feature in geojson_data["features"]:
    props = feature.get("properties", {})
    district_name = extract_district_name(props)

    if district_name in district_info:
        row = district_info[district_name]
        policies = "<br>".join([f"- {p}" for p in policy_map[row["지역유형"]]])

        popup_html = f"""
        <div style="width:260px;">
            <h4 style="margin-bottom:8px;">{district_name}</h4>
            <b>지역유형:</b> {row['지역유형']}<br>
            <b>주간소음:</b> {row['주간소음(dB)']:.2f} dB<br>
            <b>야간소음:</b> {row['야간소음(dB)']:.2f} dB<br>
            <b>스트레스점수:</b> {row['스트레스점수']:.2f}<br>
            <b>PSQI:</b> {row['PSQI']:.2f}<br>
            <b>수면시간:</b> {row['수면시간(시간)']:.2f} 시간<br><br>
            <b>정책 제안</b><br>
            {policies}
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
    if region_type == "주거지역":
        return "#74c69d"
    if region_type == "상권지역":
        return "#ffd166"
    if region_type == "교통지역":
        return "#ef476f"
    return "#adb5bd"

def style_function(feature):
    region_type = feature["properties"].get("region_type", "미분류")
    return {
        "fillColor": get_fill_color(region_type),
        "color": "#333333",
        "weight": 1.2,
        "fillOpacity": 0.65,
    }

def highlight_function(feature):
    return {
        "fillOpacity": 0.9,
        "weight": 2.5,
        "color": "#111111",
    }

# -----------------------------
# 제목
# -----------------------------
st.title("서울시 자치구별 소음과 건강영향 지도")
st.markdown("""
서울 지도에서 **자치구를 클릭하면 팝업창으로 소음, 스트레스, 수면지표, 정책 제안**을 볼 수 있습니다.  
현재 수치는 보고서 기반의 **시나리오형 자치구 대표값**입니다.
""")

# -----------------------------
# 지도 생성
# -----------------------------
m = folium.Map(
    location=[37.5665, 126.9780],
    zoom_start=11,
    tiles="CartoDB positron"
)

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
        max_width=300
    )
)

geojson_layer.add_to(m)
folium.LayerControl().add_to(m)

# 지도 출력
map_data = st_folium(m, width=None, height=700)

# -----------------------------
# 클릭한 자치구 정보 아래에 다시 표시
# -----------------------------
st.markdown("---")
st.subheader("자치구 상세 정보")

clicked = None
if map_data and map_data.get("last_active_drawing"):
    clicked = map_data["last_active_drawing"].get("properties", {}).get("district_name")

if clicked and clicked in district_info:
    row = district_info[clicked]

    col1, col2, col3 = st.columns(3)
    col1.metric("주간소음(dB)", f"{row['주간소음(dB)']:.2f}")
    col2.metric("야간소음(dB)", f"{row['야간소음(dB)']:.2f}")
    col3.metric("스트레스점수", f"{row['스트레스점수']:.2f}")

    col4, col5 = st.columns(2)
    col4.metric("PSQI", f"{row['PSQI']:.2f}")
    col5.metric("수면시간(시간)", f"{row['수면시간(시간)']:.2f}")

    st.write(f"**선택한 자치구:** {clicked}")
    st.write(f"**지역유형:** {row['지역유형']}")
    st.write("**정책 제안:**")
    for p in policy_map[row["지역유형"]]:
        st.write(f"- {p}")
else:
    st.info("지도에서 자치구를 클릭하면 여기에도 상세 정보가 표시됩니다.")

# -----------------------------
# 전체 데이터 표
# -----------------------------
with st.expander("전체 자치구 데이터 보기"):
    st.dataframe(district_data, use_container_width=True)
