import base64
from pathlib import Path
from html import escape
from typing import Optional

import pandas as pd
import requests
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
    "title_ko": ["title_ko", "영화명_한국어", "한글제목"],
    "title_en": ["title_en", "영화명_영어", "영문제목"],
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

UI_TEXT = {
    "ko": {
        "title": "🎬 영화 추천 탐색기",
        "caption": "해시태그, 기분, 상황, 시대, 국가, 장르로 영화를 탐색하고 같은 장르 작품을 추천받는 앱",
        "settings": "설정",
        "dark_mode": "다크모드",
        "language": "언어",
        "upload": "CSV 또는 XLSX 업로드",
        "filter": "필터",
        "country": "국가",
        "genre": "장르",
        "decade": "시대",
        "mood": "기분 태그",
        "situation": "상황 태그",
        "hashtag_search": "해시태그 검색",
        "title_search": "제목 / 감독 / 특징 검색",
        "sort": "정렬",
        "sort_rating": "평점 높은 순",
        "sort_latest": "최신순",
        "sort_audience": "관객수 높은 순",
        "sort_title": "제목순",
        "all_movies": "전체 영화",
        "search_result": "검색 결과",
        "genre_count": "장르 수",
        "no_result": "조건에 맞는 영화가 없습니다. 필터를 조금 줄여보세요.",
        "selected_movie": "추천 기준으로 볼 영화 선택",
        "movie_cards": "영화 카드",
        "movie_info": "선택한 영화 정보",
        "same_genre": "같은 장르 추천",
        "download": "데이터 다운로드",
        "default_download": "현재 기본 데이터 다운로드",
        "runtime": "상영시간",
        "rating": "평점",
        "director": "감독",
        "emotion": "감정 태그",
        "feature": "특징",
        "hashtags": "해시태그",
        "audience": "관객수",
        "info_country_genre": "국가 / 장르",
        "year_decade": "개봉연도 / 시대",
        "poster_api_help": "실제 포스터 자동 검색을 위해 TMDb API Key를 사용하는 것을 권장합니다.",
        "missing_data": "데이터를 불러오지 못했습니다",
    },
    "en": {
        "title": "🎬 Movie Recommender",
        "caption": "Explore movies by hashtag, mood, situation, decade, country, and genre, then get same-genre recommendations.",
        "settings": "Settings",
        "dark_mode": "Dark mode",
        "language": "Language",
        "upload": "Upload CSV or XLSX",
        "filter": "Filters",
        "country": "Country",
        "genre": "Genre",
        "decade": "Decade",
        "mood": "Mood tags",
        "situation": "Situation tags",
        "hashtag_search": "Hashtag search",
        "title_search": "Title / Director / Feature search",
        "sort": "Sort",
        "sort_rating": "Highest rating",
        "sort_latest": "Latest",
        "sort_audience": "Highest audience",
        "sort_title": "Title",
        "all_movies": "All movies",
        "search_result": "Results",
        "genre_count": "Genres",
        "no_result": "No movies matched the current filters.",
        "selected_movie": "Choose a movie for recommendations",
        "movie_cards": "Movie cards",
        "movie_info": "Selected movie info",
        "same_genre": "Similar genre recommendations",
        "download": "Download data",
        "default_download": "Download current default data",
        "runtime": "Runtime",
        "rating": "Rating",
        "director": "Director",
        "emotion": "Emotion tags",
        "feature": "Features",
        "hashtags": "Hashtags",
        "audience": "Audience",
        "info_country_genre": "Country / Genre",
        "year_decade": "Year / Decade",
        "poster_api_help": "For real posters, using a TMDb API key is recommended.",
        "missing_data": "Failed to load data",
    },
}

GENRE_TRANSLATIONS = {
    "Action": {"ko": "액션", "en": "Action"},
    "Drama": {"ko": "드라마", "en": "Drama"},
    "Thriller/Mystery": {"ko": "스릴러/미스터리", "en": "Thriller/Mystery"},
    "Romance": {"ko": "로맨스", "en": "Romance"},
    "Animation/Family": {"ko": "애니메이션/가족", "en": "Animation/Family"},
    "Comedy": {"ko": "코미디", "en": "Comedy"},
    "Sci-Fi": {"ko": "SF", "en": "Sci-Fi"},
    "Fantasy": {"ko": "판타지", "en": "Fantasy"},
    "Crime": {"ko": "범죄", "en": "Crime"},
    "Horror": {"ko": "공포", "en": "Horror"},
}

DECADE_ORDER = ["1990년대 이전", "1990년대", "2000년대", "2010년대", "2020년대", "시대 미상"]


def t(lang: str, key: str) -> str:
    return UI_TEXT.get(lang, UI_TEXT["ko"]).get(key, key)


def translate_genre(genre: str, lang: str) -> str:
    if genre in GENRE_TRANSLATIONS:
        return GENRE_TRANSLATIONS[genre].get(lang, genre)
    return genre


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

    for col in ["title", "title_ko", "title_en", "country", "genre", "director",
                "emotion_tags", "situation_tags", "feature_tags", "hashtags",
                "poster_url", "poster_query", "decade"]:
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
    for sep in ["/", "|", ";"]:
        text = text.replace(sep, ",")
    return [t.strip() for t in text.split(",") if t.strip()]


def contains_all_tags(series_text, selected_tags):
    tags = {t.lower() for t in split_tags(series_text)}
    return all(tag.lower() in tags for tag in selected_tags)


def format_number(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):,}"


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


def get_display_title(row, lang: str) -> str:
    if lang == "ko" and str(row.get("title_ko", "")).strip():
        return str(row["title_ko"]).strip()
    if lang == "en" and str(row.get("title_en", "")).strip():
        return str(row["title_en"]).strip()
    return str(row["title"]).strip()


@st.cache_data(show_spinner=False)
def fetch_tmdb_poster(title: str, year: Optional[float], api_key: Optional[str], language="ko-KR") -> Optional[str]:
    if not api_key or not str(title).strip():
        return None

    try:
        params = {
            "api_key": api_key,
            "query": title,
            "language": language,
            "include_adult": "false",
        }
        if pd.notna(year):
            params["year"] = int(year)

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


def get_poster_url(row, tmdb_api_key: Optional[str], lang: str):
    direct_url = str(row.get("poster_url", "")).strip()
    if direct_url:
        return direct_url

    query = str(row.get("poster_query", "")).strip()
    title = query if query else str(row.get("title", "")).strip()
    year = row.get("year", None)

    tmdb_lang = "ko-KR" if lang == "ko" else "en-US"
    tmdb_poster = fetch_tmdb_poster(title=title, year=year, api_key=tmdb_api_key, language=tmdb_lang)
    if tmdb_poster:
        return tmdb_poster

    return make_poster_data_uri(
        title=get_display_title(row, lang),
        genre=translate_genre(str(row.get("genre", "")), lang),
        year=year,
    )


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
            background: {"#111827" if dark_mode else "#FFFFFF"};
            border: 1px solid {"#374151" if dark_mode else "#E5E7EB"};
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


def build_card(row, dark_mode, lang, tmdb_api_key):
    display_title = escape(get_display_title(row, lang))
    country = escape(str(row["country"]))
    genre = escape(translate_genre(str(row["genre"]), lang))
    director = escape(str(row["director"]))
    decade = escape(str(row["decade"]))

    year = "-" if pd.isna(row["year"]) else str(int(row["year"]))
    runtime = "-" if pd.isna(row["runtime_min"]) else f"{int(row['runtime_min'])}분" if lang == "ko" else f"{int(row['runtime_min'])} min"
    rating = "-" if pd.isna(row["rating"]) else f"{row['rating']:.1f}"
    audience = format_number(row["audience"])

    emotions = ", ".join(split_tags(row["emotion_tags"])) or "-"
    situations = ", ".join(split_tags(row["situation_tags"])) or "-"
    features = ", ".join(split_tags(row["feature_tags"])) or "-"
    hashtags = " ".join(
        [f"#{t}" if not str(t).startswith("#") else str(t) for t in split_tags(row["hashtags"])[:4]]
    ) or ""

    poster = get_poster_url(row, tmdb_api_key, lang)

    text_color = "#F9FAFB" if dark_mode else "#111827"
    sub_color = "#D1D5DB" if dark_mode else "#4B5563"

    runtime_label = t(lang, "runtime")
    rating_label = t(lang, "rating")
    emotion_label = t(lang, "emotion")
    situation_label = t(lang, "situation")
    feature_label = t(lang, "feature")

    return f"""
    <div class='movie-card'>
      <div class='poster-wrap'>
        <img src='{poster}' class='poster-img' alt='{display_title} poster'>
        <div class='hover-panel'>
          <div><b>{display_title}</b> ({year})</div>
          <div>{t(lang, "country")}: {country}</div>
          <div>{t(lang, "genre")}: {genre}</div>
          <div>{runtime_label}: {runtime}</div>
          <div>{rating_label}: {rating}</div>
          <div>{emotion_label}: {escape(emotions)}</div>
          <div>{situation_label}: {escape(situations)}</div>
          <div>{feature_label}: {escape(features)}</div>
        </div>
      </div>
      <div class='movie-body'>
        <div class='movie-title' style='color:{text_color};'>{display_title}</div>
        <div class='movie-meta' style='color:{sub_color};'>{country} · {genre} · {year} · {runtime}</div>
        <div class='movie-meta' style='color:{sub_color};'>{t(lang, "director")}: {director if director else '-'}</div>
        <div class='movie-meta' style='color:{sub_color};'>{t(lang, "audience")}: {audience} · {t(lang, "rating")}: {rating} · {decade}</div>
        <div class='hashtags'>{escape(hashtags)}</div>
      </div>
    </div>
    """


def main():
    with st.sidebar:
        lang_label = st.selectbox("Language / 언어", ["한국어", "English"], index=0)
        lang = "ko" if lang_label == "한국어" else "en"
        dark_mode = st.toggle(t(lang, "dark_mode"), value=True)
        uploaded = st.file_uploader(t(lang, "upload"), type=["csv", "xlsx"])

    inject_css(dark_mode)

    st.title(t(lang, "title"))
    st.caption(t(lang, "caption"))

    tmdb_api_key = None
    if "TMDB_API_KEY" in st.secrets:
        tmdb_api_key = st.secrets["TMDB_API_KEY"]
    else:
        tmdb_api_key = st.session_state.get("TMDB_API_KEY", None)

    with st.sidebar:
        st.caption(t(lang, "poster_api_help"))
        manual_tmdb = st.text_input(
            "TMDb API Key",
            type="password",
            value="" if not tmdb_api_key else tmdb_api_key,
            help="없으면 poster_url 또는 플레이스홀더를 사용합니다."
        )
        if manual_tmdb.strip():
            tmdb_api_key = manual_tmdb.strip()
            st.session_state["TMDB_API_KEY"] = tmdb_api_key

    try:
        if uploaded is not None:
            df = load_dataset(uploaded, uploaded.name)
        else:
            df = load_dataset()
    except Exception as e:
        st.error(f"{t(lang, 'missing_data')}: {e}")
        st.stop()

    countries = sorted(df["country"].dropna().unique().tolist())
    genres = sorted(df["genre"].dropna().unique().tolist())
    decades = [d for d in DECADE_ORDER if d in df["decade"].unique().tolist()]
    mood_options = sorted({tag for text in df["emotion_tags"] for tag in split_tags(text)})
    situation_options = sorted({tag for text in df["situation_tags"] for tag in split_tags(text)})

    sort_options = {
        t(lang, "sort_rating"): "rating",
        t(lang, "sort_latest"): "latest",
        t(lang, "sort_audience"): "audience",
        t(lang, "sort_title"): "title",
    }

    with st.sidebar:
        st.subheader(t(lang, "filter"))
        selected_countries = st.multiselect(t(lang, "country"), countries)
        selected_genres = st.multiselect(t(lang, "genre"), genres, format_func=lambda g: translate_genre(g, lang))
        selected_decades = st.multiselect(t(lang, "decade"), decades)
        selected_moods = st.multiselect(t(lang, "mood"), mood_options)
        selected_situations = st.multiselect(t(lang, "situation"), situation_options)
        hashtag_query = st.text_input(t(lang, "hashtag_search"), placeholder="#반전, #힐링" if lang == "ko" else "#twist, #healing")
        search_text = st.text_input(t(lang, "title_search"))
        sort_key = st.selectbox(t(lang, "sort"), list(sort_options.keys()))

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
        query_tags = [t_.lstrip("#") for t_ in split_tags(hashtag_query.replace(" ", ","))]
        filtered = filtered[
            filtered["hashtags"].apply(
                lambda x: any(q.lower() in str(x).lower().replace("#", "") for q in query_tags)
            )
        ]
    if search_text.strip():
        q = search_text.lower()
        filtered = filtered[
            filtered["title"].str.lower().str.contains(q, na=False)
            | filtered["title_ko"].str.lower().str.contains(q, na=False)
            | filtered["title_en"].str.lower().str.contains(q, na=False)
            | filtered["director"].str.lower().str.contains(q, na=False)
            | filtered["feature_tags"].str.lower().str.contains(q, na=False)
        ]

    sort_mode = sort_options[sort_key]
    if sort_mode == "rating":
        filtered = filtered.sort_values(["rating", "year"], ascending=[False, False], na_position="last")
    elif sort_mode == "latest":
        filtered = filtered.sort_values(["year", "rating"], ascending=[False, False], na_position="last")
    elif sort_mode == "audience":
        filtered = filtered.sort_values(["audience", "rating"], ascending=[False, False], na_position="last")
    else:
        filtered = filtered.sort_values("title", ascending=True)

    top1, top2, top3 = st.columns(3)
    top1.metric(t(lang, "all_movies"), len(df))
    top2.metric(t(lang, "search_result"), len(filtered))
    top3.metric(t(lang, "genre_count"), df["genre"].nunique())

    if len(filtered) == 0:
        st.warning(t(lang, "no_result"))
        st.stop()

    title_options = filtered["title"].tolist()
    selected_title = st.selectbox(
        t(lang, "selected_movie"),
        title_options,
        format_func=lambda x: get_display_title(df[df["title"] == x].iloc[0], lang)
    )

    st.subheader(t(lang, "movie_cards"))
    per_row = 4
    for start in range(0, len(filtered), per_row):
        chunk = filtered.iloc[start:start + per_row]
        cols = st.columns(per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                st.markdown(build_card(row, dark_mode, lang, tmdb_api_key), unsafe_allow_html=True)

    selected_row = df[df["title"] == selected_title].iloc[0]

    st.subheader(t(lang, "movie_info"))
    info_cols = st.columns([1.2, 1.8])

    with info_cols[0]:
        st.image(get_poster_url(selected_row, tmdb_api_key, lang), use_container_width=True)

    with info_cols[1]:
        st.markdown(f"**{t(lang, 'title_search').split('/')[0].strip() if lang == 'en' else '영화명'}:** {get_display_title(selected_row, lang)}")
        st.markdown(f"**{t(lang, 'info_country_genre')}:** {selected_row['country']} / {translate_genre(selected_row['genre'], lang)}")
        st.markdown(f"**{t(lang, 'year_decade')}:** {('-' if pd.isna(selected_row['year']) else int(selected_row['year']))} / {selected_row['decade']}")
        st.markdown(f"**{t(lang, 'runtime')}:** {('-' if pd.isna(selected_row['runtime_min']) else str(int(selected_row['runtime_min'])) + ('분' if lang == 'ko' else ' min'))}")
        st.markdown(f"**{t(lang, 'rating')}:** {('-' if pd.isna(selected_row['rating']) else round(float(selected_row['rating']), 1))}")
        st.markdown(f"**{t(lang, 'director')}:** {selected_row['director'] or '-'}")
        st.markdown(f"**{t(lang, 'emotion')}:** {', '.join(split_tags(selected_row['emotion_tags'])) or '-'}")
        st.markdown(f"**{t(lang, 'situation')}:** {', '.join(split_tags(selected_row['situation_tags'])) or '-'}")
        st.markdown(f"**{t(lang, 'feature')}:** {', '.join(split_tags(selected_row['feature_tags'])) or '-'}")
        st.markdown(f"**{t(lang, 'hashtags')}:** {' '.join(['#' + x.lstrip('#') for x in split_tags(selected_row['hashtags'])]) or '-'}")

    st.subheader(t(lang, "same_genre"))
    recs = df[(df["genre"] == selected_row["genre"]) & (df["title"] != selected_row["title"])].copy()
    recs = recs.sort_values(["rating", "year"], ascending=[False, False], na_position="last").head(6)

    rec_cols = st.columns(3)
    for idx, (_, rec) in enumerate(recs.iterrows()):
        with rec_cols[idx % 3]:
            st.markdown(
                f"""
                <div class='recommend-box'>
                    <b>{escape(get_display_title(rec, lang))}</b><br>
                    <span class='small-note'>{escape(str(rec['country']))} · {escape(translate_genre(str(rec['genre']), lang))} · {('-' if pd.isna(rec['year']) else int(rec['year']))}</span><br>
                    <span class='small-note'>{t(lang, 'rating')} {('-' if pd.isna(rec['rating']) else round(float(rec['rating']),1))} · {t(lang, 'feature')} {escape(', '.join(split_tags(rec['feature_tags'])[:2]) or '-')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    source_file = find_existing_file()
    st.subheader(t(lang, "download"))
    if source_file and source_file.exists():
        st.download_button(
            label=f"{t(lang, 'default_download')} ({source_file.name})",
            data=source_file.read_bytes(),
            file_name=source_file.name,
            mime="application/octet-stream",
        )

    show_df = filtered.copy()
    show_df["display_title"] = show_df.apply(lambda r: get_display_title(r, lang), axis=1)
    show_df["genre_display"] = show_df["genre"].apply(lambda x: translate_genre(x, lang))
    st.dataframe(
        show_df[["display_title", "country", "genre_display", "year", "runtime_min", "rating", "director", "emotion_tags", "situation_tags", "feature_tags", "hashtags"]],
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
