import math
import base64
from pathlib import Path
from html import escape
from typing import Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="무드픽", page_icon="🎬", layout="wide")

BASE_DIR = Path(__file__).parent
DEFAULT_FILES = [
    BASE_DIR / "movie_recommendation_korean_dataset.csv",
    BASE_DIR / "movie_recommendation_korean_dataset.xlsx",
    BASE_DIR / "movie_recommendation_seed_dataset.csv",
    BASE_DIR / "movie_recommendation_seed_dataset.xlsx",
]

사용가능국가 = ["미국", "한국", "영국", "스페인", "인도", "일본", "중국", "대만"]

COLUMN_ALIASES = {
    "영화명": ["영화명", "title", "movie_title"],
    "개봉연도": ["개봉연도", "year", "release_year"],
    "시대구분": ["시대구분", "decade", "era"],
    "국가": ["국가", "country", "nation"],
    "장르": ["장르", "genre"],
    "상영시간": ["상영시간", "runtime_min", "runtime", "상영시간(분)"],
    "관객수": ["관객수", "audience", "audience_count"],
    "글로벌흥행액": ["글로벌흥행액", "worldwide_gross", "global_box_office"],
    "평점": ["평점", "rating", "score"],
    "감독": ["감독", "director"],
    "감정태그": ["감정태그", "emotion_tags", "mood_tags", "감정 태그"],
    "상황태그": ["상황태그", "situation_tags", "context_tags", "상황 태그"],
    "특징태그": ["특징태그", "feature_tags", "special_tags", "특징", "특징 태그"],
    "해시태그": ["해시태그", "hashtags"],
    "포스터URL": ["포스터URL", "poster_url", "poster", "poster_image_url"],
    "포스터검색어": ["포스터검색어", "poster_query", "poster_search_query"],
}

표시컬럼 = list(COLUMN_ALIASES.keys())
시대순서 = ["1990년대 이전", "1990년대", "2000년대", "2010년대", "2020년대", "시대 미상"]


def 기존파일찾기():
    for path in DEFAULT_FILES:
        if path.exists():
            return path
    return None


@st.cache_data
def 데이터불러오기(uploaded_file=None, uploaded_name=None):
    if uploaded_file is not None and uploaded_name:
        suffix = Path(uploaded_name).suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    else:
        path = 기존파일찾기()
        if path is None:
            raise FileNotFoundError("데이터 파일을 찾지 못했습니다.")
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    normalized = {}
    for target, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            if alias in df.columns:
                found = alias
                break
        if found is not None:
            normalized[target] = df[found]
        else:
            normalized[target] = ""

    out = pd.DataFrame(normalized)

    문자컬럼 = [
        "영화명", "시대구분", "국가", "장르", "감독",
        "감정태그", "상황태그", "특징태그", "해시태그",
        "포스터URL", "포스터검색어"
    ]
    for col in 문자컬럼:
        out[col] = out[col].fillna("").astype(str).str.strip()

    숫자컬럼 = ["개봉연도", "상영시간", "관객수", "글로벌흥행액", "평점"]
    for col in 숫자컬럼:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["시대구분"] = out.apply(
        lambda r: r["시대구분"] if str(r["시대구분"]).strip() else 연도별시대구분(r["개봉연도"]),
        axis=1,
    )

    out = out[out["영화명"].str.strip() != ""].copy()
    out = out[out["국가"].isin(사용가능국가)].reset_index(drop=True)
    return out


def 연도별시대구분(year):
    if pd.isna(year):
        return "시대 미상"
    year = int(year)
    if year < 1990:
        return "1990년대 이전"
    if 1990 <= year <= 1999:
        return "1990년대"
    if 2000 <= year <= 2009:
        return "2000년대"
    if 2010 <= year <= 2019:
        return "2010년대"
    return "2020년대"


def 태그분리(text):
    text = str(text or "").strip()
    if not text:
        return []
    for sep in ["/", "|", ";"]:
        text = text.replace(sep, ",")
    return [t.strip() for t in text.split(",") if t.strip()]


def 모든태그포함여부(text, selected_tags):
    tag_set = {t.lower() for t in 태그분리(text)}
    return all(tag.lower() in tag_set for tag in selected_tags)


def 숫자표시(value):
    if pd.isna(value):
        return "-"
    try:
        return f"{int(value):,}"
    except Exception:
        return "-"


def 대체포스터생성(title, genre, year):
    safe_title = escape(str(title))
    safe_genre = escape(str(genre))
    safe_year = "" if pd.isna(year) else str(int(year))

    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='600' height='900'>
      <defs>
        <linearGradient id='g' x1='0' x2='1' y1='0' y2='1'>
          <stop offset='0%' stop-color='#111827'/>
          <stop offset='100%' stop-color='#374151'/>
        </linearGradient>
      </defs>
      <rect width='100%' height='100%' fill='url(#g)'/>
      <rect x='30' y='30' width='540' height='840' rx='28' fill='none' stroke='#9CA3AF' stroke-width='4' stroke-dasharray='10 10'/>
      <text x='50%' y='40%' fill='white' font-size='34' text-anchor='middle' font-family='Arial' font-weight='700'>{safe_title}</text>
      <text x='50%' y='49%' fill='#D1D5DB' font-size='24' text-anchor='middle' font-family='Arial'>{safe_genre}</text>
      <text x='50%' y='56%' fill='#9CA3AF' font-size='22' text-anchor='middle' font-family='Arial'>{safe_year}</text>
      <text x='50%' y='76%' fill='#E5E7EB' font-size='26' text-anchor='middle' font-family='Arial'>MOVIE POSTER</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


@st.cache_data(show_spinner=False)
def tmdb포스터가져오기(제목: str, 연도: Optional[float], api_key: Optional[str]) -> Optional[str]:
    if not api_key or not str(제목).strip():
        return None

    try:
        params = {
            "api_key": api_key,
            "query": 제목,
            "language": "ko-KR",
            "include_adult": "false",
        }
        if pd.notna(연도):
            params["year"] = int(연도)

        resp = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        poster_path = results[0].get("poster_path")
        if not poster_path:
            return None

        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        return None


def 포스터주소가져오기(row, tmdb_api_key):
    direct_url = str(row.get("포스터URL", "")).strip()
    if direct_url:
        return direct_url

    query = str(row.get("포스터검색어", "")).strip()
    title = query if query else str(row.get("영화명", "")).strip()
    year = row.get("개봉연도", None)

    tmdb_url = tmdb포스터가져오기(title, year, tmdb_api_key)
    if tmdb_url:
        return tmdb_url

    return 대체포스터생성(
        title=row.get("영화명", ""),
        genre=row.get("장르", ""),
        year=row.get("개봉연도", None),
    )


def 스타일적용(다크모드=True):
    bg = "#030712" if 다크모드 else "#F3F4F6"
    main_text = "#FFFFFF" if 다크모드 else "#111827"
    sub = "#E5E7EB" if 다크모드 else "#4B5563"
    card_bg = "#111827" if 다크모드 else "#FFFFFF"
    border = "#374151" if 다크모드 else "#E5E7EB"

    sidebar_text = "#111827"
    sidebar_label = "#111827"
    sidebar_input_text = "#111827"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {bg};
            color: {main_text};
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }}

        /* 메인 본문 글씨 */
        section.main h1, section.main h2, section.main h3, section.main h4, section.main h5, section.main h6,
        section.main p, section.main label, section.main div, section.main span {{
            color: {main_text};
        }}

        .stMarkdown, .stCaption {{
            color: {main_text} !important;
        }}

        /* 사이드바는 항상 검은 글씨 */
        section[data-testid="stSidebar"] {{
            color: {sidebar_text} !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: {sidebar_text} !important;
        }}

        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div {{
            color: {sidebar_label} !important;
        }}

        /* input/select 내부 글자 검은색 */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {{
            color: {sidebar_input_text} !important;
            -webkit-text-fill-color: {sidebar_input_text} !important;
        }}

        section[data-testid="stSidebar"] [data-baseweb="select"] *,
        section[data-testid="stSidebar"] [data-baseweb="input"] *,
        section[data-testid="stSidebar"] [data-baseweb="tag"] *,
        section[data-testid="stSidebar"] .stMultiSelect *,
        section[data-testid="stSidebar"] .stSelectbox *,
        section[data-testid="stSidebar"] .stTextInput *,
        section[data-testid="stSidebar"] .stNumberInput * {{
            color: {sidebar_input_text} !important;
        }}

        .movie-card {{
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0,0,0,.18);
            margin-bottom: 16px;
            background: {card_bg};
            border: 1px solid {border};
        }}

        .poster-wrap {{
            position: relative;
        }}

        .poster-img {{
            width: 100%;
            height: 420px;
            object-fit: cover;
            display: block;
            background: #111827;
        }}

        .hover-panel {{
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(0,0,0,.04), rgba(0,0,0,.88));
            color: white;
            opacity: 0;
            transition: .2s ease-in-out;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            font-size: .92rem;
        }}

        .poster-wrap:hover .hover-panel {{
            opacity: 1;
        }}

        .movie-body {{
            padding: 14px 16px 18px 16px;
        }}

        .movie-title {{
            font-size: 1.08rem;
            font-weight: 700;
            margin-bottom: 6px;
            color: {main_text} !important;
        }}

        .movie-meta {{
            font-size: .88rem;
            margin-bottom: 6px;
            color: {sub} !important;
        }}

        .hashtags {{
            font-size: .82rem;
            color: {sub} !important;
            margin-top: 8px;
        }}

        .recommend-box {{
            border: 1px solid rgba(148,163,184,.25);
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
            background: {card_bg};
            color: {main_text};
        }}

        .small-note {{
            color: {sub} !important;
            font-size: .9rem;
        }}

        .page-box {{
            padding: 10px 14px;
            border-radius: 14px;
            border: 1px solid {border};
            background: {card_bg};
            margin-bottom: 18px;
            color: {main_text};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def 카드HTML생성(row, tmdb_api_key):
    title = escape(str(row["영화명"]))
    country = escape(str(row["국가"]))
    genre = escape(str(row["장르"]))
    director = escape(str(row["감독"]))
    decade = escape(str(row["시대구분"]))

    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{row['평점']:.1f}"
    audience = 숫자표시(row["관객수"])
    emotions = ", ".join(태그분리(row["감정태그"])) or "-"
    situations = ", ".join(태그분리(row["상황태그"])) or "-"
    features = ", ".join(태그분리(row["특징태그"])) or "-"
    hashtags = " ".join([f"#{t.lstrip('#')}" for t in 태그분리(row["해시태그"])[:4]]) or ""

    poster = 포스터주소가져오기(row, tmdb_api_key)

    return f"""
    <div class='movie-card'>
      <div class='poster-wrap'>
        <img src='{poster}' class='poster-img' alt='{title} 포스터'>
        <div class='hover-panel'>
          <div><b>{title}</b> ({year})</div>
          <div>국가: {country}</div>
          <div>장르: {genre}</div>
          <div>상영시간: {runtime}</div>
          <div>평점: {rating}</div>
          <div>감정 태그: {escape(emotions)}</div>
          <div>상황 태그: {escape(situations)}</div>
          <div>특징: {escape(features)}</div>
        </div>
      </div>
      <div class='movie-body'>
        <div class='movie-title'>{title}</div>
        <div class='movie-meta'>{country} · {genre} · {year} · {runtime}</div>
        <div class='movie-meta'>감독: {director if director else '-'}</div>
        <div class='movie-meta'>관객수: {audience} · 평점: {rating} · {decade}</div>
        <div class='hashtags'>{escape(hashtags)}</div>
      </div>
    </div>
    """


def 메인():
    with st.sidebar:
        st.subheader("설정")
        다크모드 = st.toggle("다크모드", value=True)
        uploaded = st.file_uploader("CSV 또는 XLSX 업로드", type=["csv", "xlsx"])

    스타일적용(다크모드)

    st.title("🎬 무드픽")
    st.caption("기분, 상황, 해시태그, 국가, 장르, 시대별로 영화를 탐색하고 지금 분위기에 맞는 작품을 추천받아보세요.")

    tmdb_api_key = None
    if "TMDB_API_KEY" in st.secrets:
        tmdb_api_key = st.secrets["TMDB_API_KEY"]

    with st.sidebar:
        st.caption("실제 포스터를 자동으로 불러오려면 TMDb API Key를 넣어주세요.")
        manual_tmdb = st.text_input(
            "TMDb API Key",
            type="password",
            value=tmdb_api_key or "",
            help="없으면 포스터URL 또는 대체 포스터를 사용합니다."
        )
        if manual_tmdb.strip():
            tmdb_api_key = manual_tmdb.strip()

    try:
        if uploaded is not None:
            df = 데이터불러오기(uploaded, uploaded.name)
        else:
            df = 데이터불러오기()
    except Exception as e:
        st.error(f"데이터를 불러오지 못했습니다: {e}")
        st.stop()

    국가목록 = [x for x in 사용가능국가 if x in df["국가"].unique().tolist()]
    장르목록 = sorted(df["장르"].dropna().unique().tolist())
    시대목록 = [x for x in 시대순서 if x in df["시대구분"].unique().tolist()]
    감정목록 = sorted({tag for text in df["감정태그"] for tag in 태그분리(text)})
    상황목록 = sorted({tag for text in df["상황태그"] for tag in 태그분리(text)})

    with st.sidebar:
        st.subheader("필터")
        선택국가 = st.multiselect("국가", 국가목록)
        선택장르 = st.multiselect("장르", 장르목록)
        선택시대 = st.multiselect("시대", 시대목록)
        선택감정 = st.multiselect("기분 태그", 감정목록)
        선택상황 = st.multiselect("상황 태그", 상황목록)
        해시태그검색 = st.text_input("해시태그 검색", placeholder="#반전, #힐링")
        일반검색 = st.text_input("영화명 / 감독 / 특징 검색")
        정렬기준 = st.selectbox("정렬", ["평점 높은 순", "최신순", "관객수 높은 순", "영화명순"])
        페이지당개수 = st.selectbox("페이지당 카드 수", [8, 12, 16, 20], index=1)

    filtered = df.copy()

    if 선택국가:
        filtered = filtered[filtered["국가"].isin(선택국가)]
    if 선택장르:
        filtered = filtered[filtered["장르"].isin(선택장르)]
    if 선택시대:
        filtered = filtered[filtered["시대구분"].isin(선택시대)]
    if 선택감정:
        filtered = filtered[filtered["감정태그"].apply(lambda x: 모든태그포함여부(x, 선택감정))]
    if 선택상황:
        filtered = filtered[filtered["상황태그"].apply(lambda x: 모든태그포함여부(x, 선택상황))]
    if 해시태그검색.strip():
        query_tags = [t.lstrip("#") for t in 태그분리(해시태그검색.replace(" ", ","))]
        filtered = filtered[
            filtered["해시태그"].apply(
                lambda x: any(q.lower() in str(x).lower().replace("#", "") for q in query_tags)
            )
        ]
    if 일반검색.strip():
        q = 일반검색.lower()
        filtered = filtered[
            filtered["영화명"].str.lower().str.contains(q, na=False)
            | filtered["감독"].str.lower().str.contains(q, na=False)
            | filtered["특징태그"].str.lower().str.contains(q, na=False)
        ]

    if 정렬기준 == "평점 높은 순":
        filtered = filtered.sort_values(["평점", "개봉연도"], ascending=[False, False], na_position="last")
    elif 정렬기준 == "최신순":
        filtered = filtered.sort_values(["개봉연도", "평점"], ascending=[False, False], na_position="last")
    elif 정렬기준 == "관객수 높은 순":
        filtered = filtered.sort_values(["관객수", "평점"], ascending=[False, False], na_position="last")
    else:
        filtered = filtered.sort_values("영화명", ascending=True)

    top1, top2, top3 = st.columns(3)
    top1.metric("전체 영화 수", len(df))
    top2.metric("검색 결과 수", len(filtered))
    top3.metric("장르 수", df["장르"].nunique())

    if len(filtered) == 0:
        st.warning("조건에 맞는 영화가 없습니다. 필터를 조금 줄여보세요.")
        st.stop()

    전체페이지수 = max(1, math.ceil(len(filtered) / 페이지당개수))

    if "현재페이지" not in st.session_state:
        st.session_state["현재페이지"] = 1

    if st.session_state["현재페이지"] > 전체페이지수:
        st.session_state["현재페이지"] = 전체페이지수

    st.markdown("<div class='page-box'>", unsafe_allow_html=True)
    pcol1, pcol2, pcol3, pcol4 = st.columns([1, 1, 2, 2])

    with pcol1:
        if st.button("◀ 이전 페이지", use_container_width=True):
            st.session_state["현재페이지"] = max(1, st.session_state["현재페이지"] - 1)

    with pcol2:
        if st.button("다음 페이지 ▶", use_container_width=True):
            st.session_state["현재페이지"] = min(전체페이지수, st.session_state["현재페이지"] + 1)

    with pcol3:
        현재페이지입력 = st.number_input(
            "페이지 번호",
            min_value=1,
            max_value=전체페이지수,
            value=st.session_state["현재페이지"],
            step=1,
        )
        st.session_state["현재페이지"] = 현재페이지입력

    with pcol4:
        st.markdown(
            f"<div style='padding-top:30px; font-size:0.95rem;'>현재 <b>{st.session_state['현재페이지']}</b> / 전체 <b>{전체페이지수}</b> 페이지</div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    시작 = (st.session_state["현재페이지"] - 1) * 페이지당개수
    끝 = 시작 + 페이지당개수
    page_df = filtered.iloc[시작:끝].copy()

    선택영화명 = st.selectbox("추천 기준으로 볼 영화 선택", filtered["영화명"].tolist(), index=0)

    st.subheader("영화 카드")
    한줄카드수 = 4
    for start in range(0, len(page_df), 한줄카드수):
        chunk = page_df.iloc[start:start + 한줄카드수]
        cols = st.columns(한줄카드수)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                st.markdown(카드HTML생성(row, tmdb_api_key), unsafe_allow_html=True)

    선택행 = df[df["영화명"] == 선택영화명].iloc[0]

    st.subheader("선택한 영화 정보")
    info1, info2 = st.columns([1.1, 1.9])

    with info1:
        st.image(포스터주소가져오기(선택행, tmdb_api_key), use_container_width=True)

    with info2:
        st.markdown(f"**영화명:** {선택행['영화명']}")
        st.markdown(f"**국가 / 장르:** {선택행['국가']} / {선택행['장르']}")
        st.markdown(f"**개봉연도 / 시대:** {('-' if pd.isna(선택행['개봉연도']) else int(선택행['개봉연도']))} / {선택행['시대구분']}")
        st.markdown(f"**상영시간:** {('-' if pd.isna(선택행['상영시간']) else str(int(선택행['상영시간'])) + '분')}")
        st.markdown(f"**평점:** {('-' if pd.isna(선택행['평점']) else round(float(선택행['평점']), 1))}")
        st.markdown(f"**감독:** {선택행['감독'] or '-'}")
        st.markdown(f"**관객수:** {숫자표시(선택행['관객수'])}")
        st.markdown(f"**감정 태그:** {', '.join(태그분리(선택행['감정태그'])) or '-'}")
        st.markdown(f"**상황 태그:** {', '.join(태그분리(선택행['상황태그'])) or '-'}")
        st.markdown(f"**특징:** {', '.join(태그분리(선택행['특징태그'])) or '-'}")
        st.markdown(f"**해시태그:** {' '.join(['#' + t.lstrip('#') for t in 태그분리(선택행['해시태그'])]) or '-'}")

    st.subheader("같은 장르 추천")
    추천df = df[(df["장르"] == 선택행["장르"]) & (df["영화명"] != 선택행["영화명"])].copy()
    추천df = 추천df.sort_values(["평점", "개봉연도"], ascending=[False, False], na_position="last").head(6)

    rec_cols = st.columns(3)
    for idx, (_, rec) in enumerate(추천df.iterrows()):
        with rec_cols[idx % 3]:
            st.markdown(
                f"""
                <div class='recommend-box'>
                    <b>{escape(str(rec['영화명']))}</b><br>
                    <span class='small-note'>{escape(str(rec['국가']))} · {escape(str(rec['장르']))} · {('-' if pd.isna(rec['개봉연도']) else int(rec['개봉연도']))}</span><br>
                    <span class='small-note'>평점 {('-' if pd.isna(rec['평점']) else round(float(rec['평점']),1))} · 특징 {escape(', '.join(태그분리(rec['특징태그'])[:2]) or '-')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("현재 검색 데이터 표")
    st.dataframe(page_df[표시컬럼], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    메인()
