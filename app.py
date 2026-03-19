import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="서울시 소음과 건강영향 분석",
    page_icon="📊",
    layout="wide"
)

# ---------------------------
# 기본 데이터 (보고서 기반 예시값)
# ---------------------------
data = pd.DataFrame({
    "지역유형": ["주거지역", "상권지역", "교통지역"],
    "예시 자치구": [
        "노원구, 은평구, 양천구, 도봉구, 성북구",
        "강남구, 중구, 마포구, 영등포구, 송파구",
        "서초구, 강서구, 동대문구, 광진구, 구로구"
    ],
    "주간소음(dB)": [55.40, 63.86, 76.22],
    "야간소음(dB)": [47.30, 56.14, 68.04],
    "스트레스점수": [19.10, 23.86, 32.30],
    "PSQI": [6.30, 8.23, 11.74],
    "수면시간(시간)": [6.62, 5.93, 4.99]
})

policy_data = {
    "주거지역": {
        "정책": [
            "생활소음 관리 강화",
            "공동주택 차음 보강",
            "야간 공사시간 제한"
        ],
        "기대효과": "주민 체감 소음 감소, 수면 질 개선, 민원 감소"
    },
    "상권지역": {
        "정책": [
            "심야 영업구역 시간대별 소음관리",
            "배달 오토바이 소음 저감",
            "보행친화 가로 설계"
        ],
        "기대효과": "심야 소음 피크 완화, 상권 이용 환경 개선"
    },
    "교통지역": {
        "정책": [
            "30km/h 구간 확대",
            "저소음 포장 적용",
            "화물차·버스 야간운행 관리",
            "방음벽 및 방음창 지원"
        ],
        "기대효과": "야간 도로교통 소음 감소, 스트레스 완화, 수면 회복 가능성 증가"
    }
}

# ---------------------------
# 제목
# ---------------------------
st.title("서울시 지역 특성별 소음과 건강영향 분석")
st.markdown("""
이 앱은 학습한 보고서를 바탕으로 만든 **간단한 Streamlit 시각화 예시**입니다.  
서울시의 **주거지역 / 상권지역 / 교통지역**을 기준으로  
소음 노출과 건강지표의 관계를 확인하고, 정책 방향을 살펴볼 수 있습니다.
""")

# ---------------------------
# 사이드바
# ---------------------------
st.sidebar.header("메뉴")
page = st.sidebar.radio(
    "이동할 화면을 선택하세요",
    ["보고서 개요", "지역별 비교", "정책 제안", "간단 시뮬레이션"]
)

# ---------------------------
# 1. 보고서 개요
# ---------------------------
if page == "보고서 개요":
    st.header("보고서 개요")

    st.subheader("주제")
    st.write("서울시 지역 특성별 소음 노출이 스트레스와 수면에 미치는 영향 분석")

    st.subheader("핵심 결론")
    st.info(
        "교통지역의 야간소음이 가장 높았고, 스트레스 점수와 수면장애 지표(PSQI)도 가장 나쁘게 나타났습니다. "
        "따라서 지역 맞춤형 소음 저감 정책이 필요합니다."
    )

    st.subheader("분석 변수")
    st.write("""
    - 주간소음(dB)  
    - 야간소음(dB)  
    - 스트레스 점수  
    - 수면의 질(PSQI)  
    - 수면시간  
    """)

    st.subheader("원자료 해석 시 주의점")
    st.warning(
        "이 앱은 보고서 기반의 학습용 예시입니다. "
        "실제 행정통계나 측정망 데이터가 아니라, 보고서의 시나리오형 분석값을 기반으로 구성되었습니다."
    )

# ---------------------------
# 2. 지역별 비교
# ---------------------------
elif page == "지역별 비교":
    st.header("지역별 비교")

    st.subheader("기초 데이터")
    st.dataframe(data, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("주간소음 비교")
        st.bar_chart(data.set_index("지역유형")["주간소음(dB)"])

        st.subheader("야간소음 비교")
        st.bar_chart(data.set_index("지역유형")["야간소음(dB)"])

    with col2:
        st.subheader("스트레스 점수 비교")
        st.bar_chart(data.set_index("지역유형")["스트레스점수"])

        st.subheader("수면시간 비교")
        st.bar_chart(data.set_index("지역유형")["수면시간(시간)"])

    st.subheader("해석")
    st.write("""
    - **주거지역**은 상대적으로 소음이 낮고 수면시간이 가장 길게 나타났습니다.  
    - **상권지역**은 주거지역보다 소음과 스트레스 수준이 높았습니다.  
    - **교통지역**은 주간·야간 소음이 가장 높고, 스트레스 점수와 PSQI도 가장 높아 건강영향이 가장 크게 나타났습니다.
    """)

# ---------------------------
# 3. 정책 제안
# ---------------------------
elif page == "정책 제안":
    st.header("지역별 정책 제안")

    selected_region = st.selectbox(
        "지역 유형을 선택하세요",
        ["주거지역", "상권지역", "교통지역"]
    )

    st.subheader(f"{selected_region} 정책")
    for idx, item in enumerate(policy_data[selected_region]["정책"], start=1):
        st.write(f"{idx}. {item}")

    st.subheader("기대효과")
    st.success(policy_data[selected_region]["기대효과"])

    st.subheader("설명")
    if selected_region == "주거지역":
        st.write("주거지역은 생활소음과 야간 생활환경 관리가 중요합니다.")
    elif selected_region == "상권지역":
        st.write("상권지역은 심야 영업과 배달·이동 소음 관리가 중요합니다.")
    else:
        st.write("교통지역은 차량 흐름과 야간 교통소음을 직접 줄이는 정책이 핵심입니다.")

# ---------------------------
# 4. 간단 시뮬레이션
# ---------------------------
elif page == "간단 시뮬레이션":
    st.header("야간소음 저감 시뮬레이션")

    region = st.selectbox("시뮬레이션 지역 선택", data["지역유형"].tolist())
    reduction = st.slider("야간소음 저감량(dB)", min_value=0, max_value=10, value=3)

    row = data[data["지역유형"] == region].iloc[0]

    current_night_noise = row["야간소음(dB)"]
    current_stress = row["스트레스점수"]
    current_psqi = row["PSQI"]
    current_sleep = row["수면시간(시간)"]

    # 보고서 설명용 단순 추정식
    # 야간소음 1dB 감소 시:
    # 스트레스 0.48 감소, PSQI 0.20 감소, 수면시간 0.053시간 증가
    expected_night_noise = max(current_night_noise - reduction, 0)
    expected_stress = max(current_stress - (0.48 * reduction), 0)
    expected_psqi = max(current_psqi - (0.20 * reduction), 0)
    expected_sleep = current_sleep + (0.053 * reduction)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "야간소음(dB)",
            f"{expected_night_noise:.2f}",
            delta=f"{-reduction:.2f}"
        )

    with col2:
        st.metric(
            "예상 스트레스 점수",
            f"{expected_stress:.2f}",
            delta=f"{expected_stress - current_stress:.2f}"
        )

    with col3:
        st.metric(
            "예상 PSQI",
            f"{expected_psqi:.2f}",
            delta=f"{expected_psqi - current_psqi:.2f}"
        )

    st.metric(
        "예상 수면시간(시간)",
        f"{expected_sleep:.2f}",
        delta=f"{expected_sleep - current_sleep:.2f}"
    )

    st.caption(
        "※ 본 시뮬레이션은 보고서의 설명용 추정치를 단순 적용한 예시이며, "
        "실제 정책효과를 정확히 예측하는 모델은 아닙니다."
    )
