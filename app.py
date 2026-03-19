import base64
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")
BASE_DIR = Path(__file__).parent
DEFAULT_FILES = [
    BASE_DIR / "movie_recommendation_seed_dataset.csv",
    BASE_DIR / "movie_recommendation_seed_dataset.xlsx",
    BASE_DIR / "country_genre_hit_titles_dataset.csv",
    BASE_DIR / "country_genre_hit_titles_dataset.xlsx",
]

COLUMN_ALIASES = {
    "title": ["title", "movie_title", "영화명"],
    "year": ["year", "release_year", "개봉연도"],
    "decade": ["decade", "era", "시대구분"],
    "country": ["country", "nation", "국가"],
    "genre": ["genre", "장르"],
    "runtime_min": ["runtime_min", "runtime", "상영시간", "상영시간(분)"],
    "audience": ["audience", "audience_count", "관객수"],
    "worldwide_gross": ["worldwide_gross", "global_box_office", "글로벌 흥행액"],
    "rating": ["rating", "score", "평점"],
    "director": ["director", "감독"],
    "emotion_tags": ["emotion_tags", "mood_tags", "감정 태그"],
    "situation_tags": ["situation_tags", "context_tags", "상황 태그"],
    "feature_tags": ["feature_tags", "special_tags", "특징", "특징 태그"],
    "hashtags": ["hashtags", "해시태그"],
    "poster_url": ["poster_url", "poster", "poster_image_url", "포스터URL"],
    "poster_query": ["poster_query", "poster_search_query", "포스터 검색용 쿼리"],
}

REQUIRED_OUTPUT_COLUMNS = list(COLUMN_ALIASES.keys())


def find_existing_file():
    for path in DEFAULT_FILES:
        if path.exists():
            return path
    return None


@st.cache_data
def load_dataset(uploaded_file=None, uploaded_name=None):
    if uploaded_file is not None and uploaded_name:
        suffix = Path(uploaded_name).suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    else:
        path = find_existing_file()
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

    out["title"] = out["title"].fillna("").astype(str)
    out["country"] = out["country"].fillna("미분류").astype(str)
    out["genre"] = out["genre"].fillna("미분류").astype(str)
    out["director"] = out["director"].fillna("").astype(str)

    for col in [
        "emotion_tags",
        "situation_tags",
        "feature_tags",
        "hashtags",
        "poster_url",
        "poster_query",
        "decade",
    ]:
        out[col] = out[col].fillna("").astype(str)

    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["runtime_min"] = pd.to_numeric(out["runtime_min"], errors="coerce")
    out["rating"] = pd.to_numeric(out["rating"], errors="coerce")
    out["audience"] = pd.to_numeric(out["audience"], errors="coerce")
    out["worldwide_gross"] = pd.to_numeric(out["worldwide_gross"], errors="coerce")

    out["decade"] = out.apply(
        lambda r: r["decade"] if str(r["decade"]).strip() else year_to_decade(r["year"]),
        axis=1,
    )
    out = out[out["title"].str.strip() != ""].reset_index(drop=True)
    return out


def year_to_decade(year):
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


def split_tags(text):
    text = str(text or "")
    if not text.strip():
        return []
    separators = [",", "/", "|", ";"]
    for sep in separators[1:]:
        text = text.replace(sep, separators[0])
    return [t.strip() for t in text.split(separators[0]) if t.strip()]


def contains_all_tags(series_text, selected_tags):
    tags = {t.lower() for t in split_tags(series_text)}
    return all(tag.lower() in tags for tag in selected_tags)


def make_poster_data_uri(title, genre, year):
    safe_title = escape(str(title))
    safe_genre = escape(str(genre))
    safe_year = escape("" if pd.isna(year) else str(int(year)))

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
      <text x='50%' y='41%' fill='white' font-size='38' text-anchor='middle' font-family='Arial' font-weight='700'>{safe_title}</text>
      <text x='50%' y='50%' fill='#D1D5DB' font-size='26' text-anchor='middle' font-family='Arial'>{safe_genre}</text>
      <text x='50%' y='57%' fill='#9CA3AF' font-size='24' text-anchor='middle' font-family='Arial'>{safe_year}</text>
      <text x='50%' y='78%' fill='#E5E7EB' font-size='28' text-anchor='middle' font-family='Arial'>MOVIE CARD</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def format_number(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):,}"


def build_card(row, dark_mode):
    title = escape(str(row["title"]))
    country = escape(str(row["country"]))
    genre = escape(str(row["genre"]))
    director = escape(str(row["director"]))
    decade = escape(str(row["decade"]))

    year = "-" if pd.isna(row["year"]) else str(int(row["year"]))
    runtime = "-" if pd.isna(row["runtime_min"]) else f"{int(row['runtime_min'])}분"
    rating = "-" if pd.isna(row["rating"]) else f"{row['rating']:.1f}"
    audience = format_number(row["audience"])

    emotions = ", ".join(split_tags(row["emotion_tags"])) or "-"
    situations = ", ".join(split_tags(row["situation_tags"])) or "-"
    features = ", ".join(split_tags(row["feature_tags"])) or "-"
    hashtags = " ".join(
        [f"#{t}" if not str(t).startswith("#") else str(t) for t in split_tags(row["hashtags"])[:4]]
    ) or ""

    poster = (
        row["poster_url"].strip()
        if str(row["poster_url"]).strip()
        else make_poster_data_uri(title, genre, row["year"])
    )

    text_color = "#F9FAFB" if dark_mode else "#111827"
    sub_color = "#D1D5DB" if dark_mode else "#4B5563"
    bg_card = "#111827" if dark_mode else "#FFFFFF"
    border = "#374151" if dark_mode else "#E5E7EB"

    return f"""
    <div class='movie-card' style='background:{bg_card}; border:1px solid {border};'>
      <div class='poster-wrap'>
        <img src='{poster}' class='poster-img' alt='{title} poster'>
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
        <div class='movie-title' style='color:{text_color};'>{title}</div>
        <div class='movie-meta' style='color:{sub_color};'>{country} · {genre} · {year} · {runtime}</div>
        <div class='movie-meta' style='color:{sub_color};'>감독: {director if director else '-'}</div>
        <div class='movie-meta' style='color:{sub_color};'>관객수: {audience} · 평점: {rating} · {decade}</div>
        <div class='hashtags'>{escape(hashtags)}</div>
      </div>
    </div>
    """


def inject_css(dark_mode):
    bg = "#030712" if dark_mode else "#F3F4F6"
    text = "#F9FAFB" if dark_mode else "#111827"
    sub = "#D1D5DB" if dark_mode else "#4B5563"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {bg};
            color: {text};
        }}
        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }}
        .movie-card {{
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0,0,0,.18);
            margin-bottom: 14px;
        }}
        .poster-wrap {{
            position: relative;
        }}
        .poster-img {{
            width: 100%;
            height: 360px;
            object-fit: cover;
            display: block;
        }}
        .hover-panel {{
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(0,0,0,.02), rgba(0,0,0,.86));
            color: white;
            opacity: 0;
            transition: .2s;
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
        }}
        .movie-meta {{
            font-size: .88rem;
            margin-bottom: 6px;
        }}
        .hashtags {{
            font-size: .82rem;
            color: {sub};
            margin-top: 8px;
        }}
        .hero-box {{
            padding: .4rem 0 1rem 0;
        }}
        .recommend-box {{
            border: 1px solid rgba(148,163,184,.25);
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
        }}
        .small-note {{
            color: {sub};
            font-size: .9rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.title("🎬 영화 추천 탐색기")
    st.caption("해시태그, 기분, 상황, 시대, 국가, 장르로 영화를 탐색하고 같은 장르 작품을 추천받는 앱")

    with st.sidebar:
        st.subheader("설정")
        dark_mode = st.toggle("다크모드", value=True)
        uploaded = st.file_uploader("CSV 또는 XLSX 업로드", type=["csv", "xlsx"])

    inject_css(dark_mode)

    try:
        if uploaded is not None:
            df = load_dataset(uploaded, uploaded.name)
        else:
            df = load_dataset()
    except Exception as e:
        st.error(f"데이터를 불러오지 못했습니다: {e}")
        st.stop()

    countries = sorted(df["country"].dropna().unique().tolist())
    genres = sorted(df["genre"].dropna().unique().tolist())
    decades = [
        d for d in ["1990년대 이전", "1990년대", "2000년대", "2010년대", "2020년대", "시대 미상"]
        if d in df["decade"].unique().tolist()
    ]
    mood_options = sorted({tag for text in df["emotion_tags"] for tag in split_tags(text)})
    situation_options = sorted({tag for text in df["situation_tags"] for tag in split_tags(text)})

    with st.sidebar:
        st.subheader("필터")
        selected_countries = st.multiselect("국가", countries)
        selected_genres = st.multiselect("장르", genres)
        selected_decades = st.multiselect("시대", decades)
        selected_moods = st.multiselect("기분 태그", mood_options)
        selected_situations = st.multiselect("상황 태그", situation_options)
        hashtag_query = st.text_input("해시태그 검색", placeholder="#반전 또는 힐링")
        search_text = st.text_input("제목 / 감독 / 특징 검색")
        sort_key = st.selectbox("정렬", ["평점 높은 순", "최신순", "관객수 높은 순", "제목순"])

    filtered = df.copy()

    if selected_countries:
        filtered = filtered[filtered["country"].isin(selected_countries)]
    if selected_genres:
        filtered = filtered[filtered["genre"].isin(selected_genres)]
    if selected_decades:
        filtered = filtered[filtered["decade"].isin(selected_decades)]
    if selected_moods:
        filtered = filtered[filtered["emotion_tags"].apply(lambda x: contains_all_tags(x, selected_moods))]
    if selected_situations:
        filtered = filtered[filtered["situation_tags"].apply(lambda x: contains_all_tags(x, selected_situations))]
    if hashtag_query.strip():
        query_tags = [t.lstrip("#") for t in split_tags(hashtag_query.replace(" ", ","))]
        filtered = filtered[
            filtered["hashtags"].apply(
                lambda x: any(q.lower() in str(x).lower().replace("#", "") for q in query_tags)
            )
        ]
    if search_text.strip():
        q = search_text.lower()
        filtered = filtered[
            filtered["title"].str.lower().str.contains(q, na=False)
            | filtered["director"].str.lower().str.contains(q, na=False)
            | filtered["feature_tags"].str.lower().str.contains(q, na=False)
        ]

    if sort_key == "평점 높은 순":
        filtered = filtered.sort_values(["rating", "year"], ascending=[False, False], na_position="last")
    elif sort_key == "최신순":
        filtered = filtered.sort_values(["year", "rating"], ascending=[False, False], na_position="last")
    elif sort_key == "관객수 높은 순":
        filtered = filtered.sort_values(["audience", "rating"], ascending=[False, False], na_position="last")
    else:
        filtered = filtered.sort_values("title", ascending=True)

    st.markdown("<div class='hero-box'></div>", unsafe_allow_html=True)
    top1, top2, top3 = st.columns([1, 1, 1])
    top1.metric("전체 영화", len(df))
    top2.metric("검색 결과", len(filtered))
    top3.metric("장르 수", df["genre"].nunique())

    if len(filtered) == 0:
        st.warning("조건에 맞는 영화가 없습니다. 필터를 조금 줄여보세요.")
        st.stop()

    selected_title = st.selectbox("추천 기준으로 볼 영화 선택", filtered["title"].tolist(), index=0)

    st.subheader("영화 카드")
    per_row = 4
    for start in range(0, len(filtered), per_row):
        chunk = filtered.iloc[start:start + per_row]
        cols = st.columns(per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                st.markdown(build_card(row, dark_mode), unsafe_allow_html=True)

    selected_row = df[df["title"] == selected_title].iloc[0]

    st.subheader("선택한 영화 정보")
    info_cols = st.columns([1.2, 1.8])

    with info_cols[0]:
        poster = (
            selected_row["poster_url"].strip()
            if str(selected_row["poster_url"]).strip()
            else make_poster_data_uri(selected_row["title"], selected_row["genre"], selected_row["year"])
        )
        st.image(poster, use_container_width=True)

    with info_cols[1]:
        st.markdown(f"**영화명:** {selected_row['title']}")
        st.markdown(f"**국가 / 장르:** {selected_row['country']} / {selected_row['genre']}")
        st.markdown(
            f"**개봉연도 / 시대:** {('-' if pd.isna(selected_row['year']) else int(selected_row['year']))} / {selected_row['decade']}"
        )
        st.markdown(
            f"**상영시간:** {('-' if pd.isna(selected_row['runtime_min']) else str(int(selected_row['runtime_min'])) + '분')}"
        )
        st.markdown(
            f"**평점:** {('-' if pd.isna(selected_row['rating']) else round(float(selected_row['rating']), 1))}"
        )
        st.markdown(f"**감정 태그:** {', '.join(split_tags(selected_row['emotion_tags'])) or '-'}")
        st.markdown(f"**상황 태그:** {', '.join(split_tags(selected_row['situation_tags'])) or '-'}")
        st.markdown(f"**특징:** {', '.join(split_tags(selected_row['feature_tags'])) or '-'}")
        st.markdown(
            f"**해시태그:** {' '.join(['#' + t.lstrip('#') for t in split_tags(selected_row['hashtags'])]) or '-'}"
        )

    st.subheader("같은 장르 추천")
    recs = df[(df["genre"] == selected_row["genre"]) & (df["title"] != selected_row["title"])].copy()
    recs = recs.sort_values(["rating", "year"], ascending=[False, False], na_position="last").head(6)

    rec_cols = st.columns(3)
    for idx, (_, rec) in enumerate(recs.iterrows()):
        with rec_cols[idx % 3]:
            st.markdown(
                f"""
                <div class='recommend-box'>
                    <b>{escape(str(rec['title']))}</b><br>
                    <span class='small-note'>{escape(str(rec['country']))} · {escape(str(rec['genre']))} · {('-' if pd.isna(rec['year']) else int(rec['year']))}</span><br>
                    <span class='small-note'>평점 {('-' if pd.isna(rec['rating']) else round(float(rec['rating']),1))} · 특징 {escape(', '.join(split_tags(rec['feature_tags'])[:2]) or '-')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    source_file = find_existing_file()
    st.subheader("데이터 다운로드")
    if source_file and source_file.exists():
        st.download_button(
            label=f"현재 기본 데이터 다운로드 ({source_file.name})",
            data=source_file.read_bytes(),
            file_name=source_file.name,
            mime="application/octet-stream",
        )

    st.dataframe(filtered[REQUIRED_OUTPUT_COLUMNS], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
