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


def 연도별시대구분(year):
    if pd.isna(year):
        return "시대 미상"
    year = int(year)
    if year < 1990:
        return "1990년대 이전"
    if year <= 1999:
        return "1990년대"
    if year <= 2009:
        return "2000년대"
    if year <= 2019:
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


def 금액표시(value):
    if pd.isna(value):
        return "-"
    try:
        return f"${int(value):,}"
    except Exception:
        return "-"


def 장르태그만들기(장르):
    mapping = {
        "액션": ("전율,쾌감,몰입", "친구와,주말,액션좋아할때", "블록버스터,속도감,카타르시스", "액션,몰입,대작"),
        "드라마": ("감동,여운,몰입", "혼자,조용한밤,깊게보고싶을때", "인생,서사,감정선", "드라마,감동,여운"),
        "스릴러": ("긴장,불안,몰입", "밤,혼자,반전좋아할때", "반전,심리,서스펜스", "스릴러,반전,몰입"),
        "로맨스": ("설렘,감성,여운", "연인과,밤,감성적인날", "사랑,청춘,관계", "로맨스,감성,설렘"),
        "애니메이션": ("따뜻함,힐링,감동", "가족과,주말오후,가볍게", "성장,가족,모험", "애니메이션,힐링,가족"),
        "판타지": ("신비로움,몰입,경이로움", "주말,혼자,세계관좋아할때", "세계관,마법,모험", "판타지,모험,세계관"),
        "코미디": ("유쾌함,웃김,가벼움", "친구와,주말,웃고싶을때", "웃음,기분전환,템포", "코미디,웃김,가볍게"),
        "SF": ("경이로움,몰입,사색", "혼자,주말밤,생각하고싶을때", "우주,미래,설정", "SF,우주,세계관"),
    }
    return mapping.get(장르, ("몰입,감상", "혼자,주말", "영화,스토리", "영화,추천"))


def 기본데이터생성():
    movie_map = {
        "미국": [
            ("아바타", 2009, "SF", 162, 7.9, "제임스 카메론", "Avatar"),
            ("아바타: 물의 길", 2022, "SF", 192, 7.6, "제임스 카메론", "Avatar The Way of Water"),
            ("어벤져스: 엔드게임", 2019, "액션", 181, 8.4, "안소니 루소, 조 루소", "Avengers Endgame"),
            ("어벤져스: 인피니티 워", 2018, "액션", 149, 8.4, "안소니 루소, 조 루소", "Avengers Infinity War"),
            ("스파이더맨: 노 웨이 홈", 2021, "액션", 148, 8.2, "존 왓츠", "Spider-Man No Way Home"),
            ("타이타닉", 1997, "로맨스", 194, 7.9, "제임스 카메론", "Titanic"),
            ("인터스텔라", 2014, "SF", 169, 8.7, "크리스토퍼 놀란", "Interstellar"),
            ("인셉션", 2010, "스릴러", 148, 8.8, "크리스토퍼 놀란", "Inception"),
            ("다크 나이트", 2008, "액션", 152, 9.0, "크리스토퍼 놀란", "The Dark Knight"),
            ("조커", 2019, "드라마", 122, 8.4, "토드 필립스", "Joker"),
            ("라라랜드", 2016, "로맨스", 128, 8.0, "데이미언 셔젤", "La La Land"),
            ("겨울왕국", 2013, "애니메이션", 102, 7.4, "크리스 벅, 제니퍼 리", "Frozen"),
            ("겨울왕국 2", 2019, "애니메이션", 103, 6.8, "크리스 벅, 제니퍼 리", "Frozen II"),
            ("인사이드 아웃", 2015, "애니메이션", 95, 8.1, "피트 닥터", "Inside Out"),
            ("토이 스토리 3", 2010, "애니메이션", 103, 8.3, "리 언크리치", "Toy Story 3"),
        ],
        "한국": [
            ("명량", 2014, "액션", 128, 7.1, "김한민", "The Admiral Roaring Currents"),
            ("극한직업", 2019, "코미디", 111, 7.1, "이병헌", "Extreme Job"),
            ("신과함께-죄와 벌", 2017, "판타지", 139, 7.2, "김용화", "Along with the Gods The Two Worlds"),
            ("국제시장", 2014, "드라마", 126, 7.8, "윤제균", "Ode to My Father"),
            ("베테랑", 2015, "액션", 123, 7.0, "류승완", "Veteran 2015"),
            ("서울의 봄", 2023, "드라마", 141, 8.3, "김성수", "12.12 The Day"),
            ("암살", 2015, "액션", 139, 7.3, "최동훈", "Assassination 2015"),
            ("범죄도시 2", 2022, "액션", 106, 7.2, "이상용", "The Roundup"),
            ("7번방의 선물", 2013, "코미디", 127, 8.2, "이환경", "Miracle in Cell No 7"),
            ("도둑들", 2012, "액션", 135, 6.8, "최동훈", "The Thieves"),
            ("변호인", 2013, "드라마", 127, 7.7, "양우석", "The Attorney"),
            ("부산행", 2016, "스릴러", 118, 7.6, "연상호", "Train to Busan"),
            ("기생충", 2019, "스릴러", 132, 8.5, "봉준호", "Parasite"),
            ("올드보이", 2003, "스릴러", 120, 8.4, "박찬욱", "Oldboy"),
            ("태극기 휘날리며", 2004, "드라마", 148, 8.0, "강제규", "Tae Guk Gi The Brotherhood of War"),
            ("왕의 남자", 2005, "드라마", 119, 7.4, "이준익", "The King and the Clown"),
            ("실미도", 2003, "액션", 135, 7.1, "강우석", "Silmido"),
            ("괴물", 2006, "스릴러", 119, 7.1, "봉준호", "The Host 2006"),
            ("헤어질 결심", 2022, "로맨스", 138, 7.3, "박찬욱", "Decision to Leave"),
            ("과속스캔들", 2008, "코미디", 108, 7.2, "강형철", "Scandal Makers"),
            ("광해, 왕이 된 남자", 2012, "드라마", 131, 7.8, "추창민", "Masquerade"),
            ("변신", 2019, "스릴러", 113, 6.0, "김홍선", "Metamorphosis"),
            ("엑시트", 2019, "액션", 103, 7.0, "이상근", "Exit"),
            ("내부자들", 2015, "드라마", 130, 7.8, "우민호", "Inside Men"),
            ("1987", 2017, "드라마", 129, 7.8, "장준환", "1987 When the Day Comes"),
            ("건축학개론", 2012, "로맨스", 118, 7.2, "이용주", "Architecture 101"),
            ("늑대소년", 2012, "판타지", 125, 7.2, "조성희", "A Werewolf Boy"),
            ("한산: 용의 출현", 2022, "액션", 129, 6.6, "김한민", "Hansan Rising Dragon"),
            ("범죄도시 3", 2023, "액션", 105, 6.6, "이상용", "The Roundup No Way Out"),
            ("검사외전", 2016, "코미디", 126, 6.7, "이일형", "A Violent Prosecutor"),
            ("신과함께-인과 연", 2018, "판타지", 141, 7.1, "김용화", "Along with the Gods The Last 49 Days"),
            ("말아톤", 2005, "드라마", 117, 7.7, "정윤철", "Marathon"),
            ("써니", 2011, "코미디", 124, 7.8, "강형철", "Sunny"),
            ("부당거래", 2010, "스릴러", 119, 7.2, "류승완", "The Unjust"),
            ("마더", 2009, "스릴러", 129, 7.8, "봉준호", "Mother 2009"),
        ],
        "영국": [
            ("007 스카이폴", 2012, "액션", 143, 7.8, "샘 멘데스", "Skyfall"),
            ("해리 포터와 죽음의 성물 2", 2011, "판타지", 130, 8.1, "데이비드 예이츠", "Harry Potter and the Deathly Hallows Part 2"),
            ("킹스 스피치", 2010, "드라마", 118, 8.0, "톰 후퍼", "The King's Speech"),
            ("노팅 힐", 1999, "로맨스", 124, 7.2, "로저 미첼", "Notting Hill"),
            ("패딩턴 2", 2017, "애니메이션", 103, 7.8, "폴 킹", "Paddington 2"),
            ("28일 후", 2002, "스릴러", 113, 7.5, "대니 보일", "28 Days Later"),
            ("브리짓 존스의 일기", 2001, "코미디", 97, 6.8, "샤론 맥과이어", "Bridget Jones's Diary"),
            ("보헤미안 랩소디", 2018, "드라마", 134, 8.0, "브라이언 싱어", "Bohemian Rhapsody"),
            ("1917", 2019, "드라마", 119, 8.2, "샘 멘데스", "1917"),
            ("킹스맨: 시크릿 에이전트", 2014, "액션", 129, 7.7, "매튜 본", "Kingsman The Secret Service"),
        ],
        "스페인": [
            ("판의 미로", 2006, "판타지", 118, 8.2, "기예르모 델 토로", "Pan's Labyrinth"),
            ("더 임파서블", 2012, "드라마", 114, 7.6, "후안 안토니오 바요나", "The Impossible"),
            ("줄리아의 눈", 2010, "스릴러", 118, 6.7, "기옘 모랄레스", "Julia's Eyes"),
            ("오픈 유어 아이즈", 1997, "SF", 119, 7.7, "알레한드로 아메나바르", "Open Your Eyes"),
            ("토렌테", 1998, "코미디", 97, 6.8, "산티아고 세구라", "Torrente"),
            ("타데오 존스", 2012, "애니메이션", 92, 6.1, "엔리케 가토", "Tad The Lost Explorer"),
            ("더 바디", 2012, "스릴러", 112, 7.6, "오리올 파울로", "The Body 2012"),
            ("인비저블 게스트", 2016, "스릴러", 106, 8.0, "오리올 파울로", "The Invisible Guest"),
            ("볼베르", 2006, "드라마", 121, 7.6, "페드로 알모도바르", "Volver"),
            ("클라우스", 2019, "애니메이션", 97, 8.2, "세르히오 파블로스", "Klaus"),
        ],
        "인도": [
            ("세 얼간이", 2009, "코미디", 170, 8.4, "라지쿠마르 히라니", "3 Idiots"),
            ("당갈", 2016, "드라마", 161, 8.3, "니테시 티와리", "Dangal"),
            ("바후발리: 더 비기닝", 2015, "액션", 159, 8.0, "S. S. 라자몰리", "Baahubali The Beginning"),
            ("런치박스", 2013, "로맨스", 104, 7.8, "리테쉬 바트라", "The Lunchbox"),
            ("안다둔", 2018, "스릴러", 139, 8.2, "스리람 라가반", "Andhadhun"),
            ("RRR", 2022, "액션", 182, 7.8, "S. S. 라자몰리", "RRR"),
            ("PK", 2014, "코미디", 153, 8.1, "라지쿠마르 히라니", "PK"),
            ("쇼레이", 1975, "액션", 204, 8.1, "라메쉬 시피", "Sholay"),
            ("드리시얌", 2015, "스릴러", 163, 8.2, "니시칸트 카마트", "Drishyam"),
            ("퀸", 2013, "드라마", 146, 8.1, "비카스 발", "Queen 2013"),
        ],
        "일본": [
            ("센과 치히로의 행방불명", 2001, "애니메이션", 125, 8.6, "미야자키 하야오", "Spirited Away"),
            ("너의 이름은", 2016, "로맨스", 106, 8.4, "신카이 마코토", "Your Name"),
            ("고질라 마이너스 원", 2023, "액션", 124, 8.0, "야마자키 타카시", "Godzilla Minus One"),
            ("링", 1998, "스릴러", 96, 7.2, "나카타 히데오", "Ringu"),
            ("어느 가족", 2018, "드라마", 121, 7.9, "고레에다 히로카즈", "Shoplifters"),
            ("하울의 움직이는 성", 2004, "판타지", 119, 8.2, "미야자키 하야오", "Howl's Moving Castle"),
            ("모노노케 히메", 1997, "판타지", 134, 8.3, "미야자키 하야오", "Princess Mononoke"),
            ("날씨의 아이", 2019, "로맨스", 114, 7.5, "신카이 마코토", "Weathering with You"),
            ("스즈메의 문단속", 2022, "애니메이션", 122, 7.7, "신카이 마코토", "Suzume"),
            ("러브레터", 1995, "로맨스", 117, 7.9, "이와이 슌지", "Love Letter 1995"),
        ],
        "중국": [
            ("와호장룡", 2000, "액션", 120, 7.9, "이안", "Crouching Tiger Hidden Dragon"),
            ("영웅", 2002, "드라마", 99, 7.9, "장이머우", "Hero 2002"),
            ("유랑지구", 2019, "SF", 125, 6.0, "궈판", "The Wandering Earth"),
            ("안녕 리", 2021, "코미디", 128, 7.7, "자 링", "Hi Mom 2021"),
            ("소시대", 2013, "로맨스", 116, 5.0, "궈징밍", "Tiny Times"),
            ("장진호", 2021, "스릴러", 176, 5.5, "천카이거 외", "The Battle at Lake Changjin"),
            ("봉신연의: 조가풍운", 2023, "판타지", 148, 6.7, "우얼샨", "Creation of the Gods I Kingdom of Storms"),
            ("만리장성", 2016, "액션", 103, 6.0, "장이머우", "The Great Wall"),
            ("적벽대전", 2008, "액션", 148, 7.3, "오우삼", "Red Cliff"),
            ("쿵푸허슬", 2004, "코미디", 99, 7.7, "주성치", "Kung Fu Hustle"),
        ],
        "대만": [
            ("말할 수 없는 비밀", 2007, "로맨스", 101, 7.5, "주걸륜", "Secret 2007"),
            ("그 시절, 우리가 좋아했던 소녀", 2011, "드라마", 109, 7.6, "구파도", "You Are the Apple of My Eye"),
            ("카페 6", 2016, "코미디", 103, 6.4, "오자운", "At Cafe 6"),
            ("더 새드니스", 2021, "스릴러", 99, 6.4, "롭 자바즈", "The Sadness"),
            ("실크", 2006, "판타지", 108, 6.4, "수 차오빈", "Silk 2006"),
            ("청설", 2009, "드라마", 109, 7.5, "정펀펀", "Hear Me 2009"),
            ("해피 투게더", 1997, "드라마", 96, 7.7, "왕가위", "Happy Together"),
            ("아비정전", 1990, "드라마", 94, 7.4, "왕가위", "Days of Being Wild"),
            ("메리 마이 데드 바디", 2023, "코미디", 130, 7.3, "청웨이하오", "Marry My Dead Body"),
            ("나의 소녀시대", 2015, "로맨스", 134, 7.4, "천옥산", "Our Times"),
        ],
    }

    rows = []
    idx = 1
    for 국가, movies in movie_map.items():
        for 영화명, 개봉연도, 장르, 상영시간, 평점, 감독, 포스터검색어 in movies:
            감정태그, 상황태그, 특징태그, 해시태그 = 장르태그만들기(장르)
            rows.append({
                "영화명": 영화명,
                "개봉연도": 개봉연도,
                "국가": 국가,
                "장르": 장르,
                "상영시간": 상영시간,
                "관객수": 500000 + idx * 9321,
                "글로벌흥행액": 25000000 + idx * 1750000,
                "평점": 평점,
                "감독": 감독,
                "감정태그": 감정태그,
                "상황태그": 상황태그,
                "특징태그": 특징태그,
                "해시태그": 해시태그,
                "포스터URL": "",
                "포스터검색어": 포스터검색어,
            })
            idx += 1

    df = pd.DataFrame(rows)
    df["시대구분"] = df["개봉연도"].apply(연도별시대구분)
    return df


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
            df = 기본데이터생성()
        else:
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


def 대체포스터생성(title, genre, year):
    safe_title = escape(str(title))
    safe_genre = escape(str(genre))
    safe_year = "" if pd.isna(year) else str(int(year))

    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='600' height='900'>
      <defs>
        <linearGradient id='g' x1='0' x2='1' y1='0' y2='1'>
          <stop offset='0%' stop-color='#0f172a'/>
          <stop offset='100%' stop-color='#1e293b'/>
        </linearGradient>
      </defs>
      <rect width='100%' height='100%' fill='url(#g)'/>
      <rect x='28' y='28' width='544' height='844' rx='32' fill='none' stroke='#64748b' stroke-width='3'/>
      <text x='50%' y='42%' fill='white' font-size='34' text-anchor='middle' font-family='Arial' font-weight='700'>{safe_title}</text>
      <text x='50%' y='50%' fill='#cbd5e1' font-size='24' text-anchor='middle' font-family='Arial'>{safe_genre}</text>
      <text x='50%' y='57%' fill='#94a3b8' font-size='22' text-anchor='middle' font-family='Arial'>{safe_year}</text>
      <text x='50%' y='78%' fill='#e2e8f0' font-size='28' text-anchor='middle' font-family='Arial'>MOOD PICK</text>
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
    bg = "#070b14" if 다크모드 else "#f4f6fb"
    main_text = "#ffffff" if 다크모드 else "#111827"
    sub = "#cbd5e1" if 다크모드 else "#4b5563"
    card_bg = "#111827" if 다크모드 else "#ffffff"
    border = "#243041" if 다크모드 else "#e5e7eb"
    sidebar_text = "#111827"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(59,130,246,.12), transparent 28%),
                radial-gradient(circle at top left, rgba(236,72,153,.10), transparent 24%),
                {bg};
            color: {main_text};
        }}
        .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1480px;
        }}
        section.main h1, section.main h2, section.main h3, section.main h4,
        section.main p, section.main label, section.main div, section.main span {{
            color: {main_text};
        }}
        .stMarkdown, .stCaption {{
            color: {main_text} !important;
        }}
        section[data-testid="stSidebar"] * {{
            color: {sidebar_text} !important;
        }}
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {{
            color: {sidebar_text} !important;
            -webkit-text-fill-color: {sidebar_text} !important;
        }}
        .hero-wrap {{
            position: relative;
            min-height: 470px;
            border-radius: 30px;
            overflow: hidden;
            margin-bottom: 26px;
            border: 1px solid rgba(255,255,255,.08);
            box-shadow: 0 20px 60px rgba(0,0,0,.35);
            background: #0f172a;
        }}
        .hero-bg {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .hero-overlay {{
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, rgba(3,7,18,.94) 0%, rgba(3,7,18,.78) 35%, rgba(3,7,18,.30) 70%, rgba(3,7,18,.15) 100%),
                linear-gradient(0deg, rgba(3,7,18,.82) 0%, rgba(3,7,18,.15) 55%, rgba(3,7,18,.05) 100%);
        }}
        .hero-content {{
            position: relative;
            z-index: 2;
            padding: 42px;
            max-width: 700px;
        }}
        .hero-badge {{
            display: inline-block;
            padding: 7px 14px;
            border-radius: 999px;
            background: rgba(255,255,255,.12);
            border: 1px solid rgba(255,255,255,.14);
            color: #fff;
            font-size: .82rem;
            margin-bottom: 16px;
        }}
        .hero-title {{
            font-size: 3rem;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 12px;
            color: #fff;
        }}
        .hero-meta {{
            font-size: .96rem;
            color: #dbe4f0;
            margin-bottom: 18px;
        }}
        .hero-desc {{
            font-size: 1rem;
            color: #d4dbe5;
            line-height: 1.7;
            margin-bottom: 22px;
        }}
        .chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 22px;
        }}
        .chip {{
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(255,255,255,.09);
            color: #fff;
            font-size: .85rem;
            border: 1px solid rgba(255,255,255,.10);
        }}
        .hero-stats {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .hero-stat {{
            min-width: 120px;
            padding: 14px 16px;
            border-radius: 18px;
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.10);
        }}
        .hero-stat-label {{
            color: #d1d5db;
            font-size: .78rem;
            margin-bottom: 4px;
        }}
        .hero-stat-value {{
            color: #fff;
            font-size: 1.05rem;
            font-weight: 700;
        }}
        .section-title {{
            font-size: 1.28rem;
            font-weight: 800;
            margin: 8px 0 16px 0;
            letter-spacing: -0.02em;
        }}
        .movie-card {{
            position: relative;
            border-radius: 22px;
            overflow: hidden;
            margin-bottom: 18px;
            background: {card_bg};
            border: 1px solid {border};
            box-shadow: 0 12px 30px rgba(0,0,0,.18);
            transition: transform .18s ease, box-shadow .18s ease;
        }}
        .movie-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 16px 36px rgba(0,0,0,.28);
        }}
        .poster-wrap {{
            position: relative;
        }}
        .poster-img {{
            width: 100%;
            height: 360px;
            object-fit: cover;
            display: block;
            background: #0f172a;
        }}
        .card-gradient {{
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(0,0,0,.02), rgba(0,0,0,.82));
        }}
        .card-hover {{
            position: absolute;
            inset: 0;
            opacity: 0;
            transition: .18s ease;
            background: linear-gradient(180deg, rgba(0,0,0,.18), rgba(0,0,0,.92));
            color: #fff;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            font-size: .9rem;
        }}
        .movie-card:hover .card-hover {{
            opacity: 1;
        }}
        .card-bottom {{
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            padding: 16px;
            z-index: 2;
        }}
        .card-title {{
            font-size: 1rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
            line-height: 1.3;
        }}
        .card-sub {{
            font-size: .84rem;
            color: #dbe3ee;
        }}
        .detail-panel {{
            background: linear-gradient(180deg, rgba(17,24,39,.88), rgba(17,24,39,.78));
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 26px;
            padding: 26px;
            box-shadow: 0 16px 40px rgba(0,0,0,.24);
        }}
        .detail-head {{
            font-size: 1.55rem;
            font-weight: 800;
            margin-bottom: 8px;
        }}
        .detail-meta {{
            color: {sub};
            font-size: .96rem;
            margin-bottom: 16px;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            margin-top: 18px;
        }}
        .detail-box {{
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 18px;
            padding: 14px 16px;
        }}
        .detail-box-label {{
            font-size: .78rem;
            color: #cbd5e1;
            margin-bottom: 5px;
        }}
        .detail-box-value {{
            font-size: .95rem;
            color: #fff;
            font-weight: 600;
            line-height: 1.45;
        }}
        .rail-card {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 10px 24px rgba(0,0,0,.12);
        }}
        .rail-title {{
            font-size: .98rem;
            font-weight: 700;
            margin-bottom: 5px;
            color: {main_text};
        }}
        .rail-sub {{
            font-size: .84rem;
            color: {sub};
            line-height: 1.5;
        }}
        .page-box {{
            padding: 12px 14px;
            border-radius: 18px;
            border: 1px solid {border};
            background: rgba(17,24,39,.65);
            margin-bottom: 20px;
            box-shadow: 0 12px 28px rgba(0,0,0,.14);
        }}
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
            color: {main_text} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def 포스터주소_html(url):
    return escape(url, quote=True)


def 카드HTML생성(row, tmdb_api_key):
    title = escape(str(row["영화명"]))
    country = escape(str(row["국가"]))
    genre = escape(str(row["장르"]))
    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{float(row['평점']):.1f}"
    emotions = ", ".join(태그분리(row["감정태그"])) or "-"
    situations = ", ".join(태그분리(row["상황태그"])) or "-"
    features = ", ".join(태그분리(row["특징태그"])) or "-"
    poster = 포스터주소가져오기(row, tmdb_api_key)

    return f"""
    <div class='movie-card'>
        <div class='poster-wrap'>
            <img src='{포스터주소_html(poster)}' class='poster-img' alt='{title} 포스터'>
            <div class='card-gradient'></div>
            <div class='card-bottom'>
                <div class='card-title'>{title}</div>
                <div class='card-sub'>{country} · {genre} · {year} · {runtime} · ★ {rating}</div>
            </div>
            <div class='card-hover'>
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
    </div>
    """


def 히어로HTML생성(row, tmdb_api_key):
    title = escape(str(row["영화명"]))
    country = escape(str(row["국가"]))
    genre = escape(str(row["장르"]))
    director = escape(str(row["감독"]))
    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{float(row['평점']):.1f}"
    audience = 숫자표시(row["관객수"])
    gross = 금액표시(row["글로벌흥행액"])
    poster = 포스터주소가져오기(row, tmdb_api_key)

    감정칩 = "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(row["감정태그"])[:3]])
    특징칩 = "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(row["특징태그"])[:3]])

    return f"""
    <div class='hero-wrap'>
        <img src='{포스터주소_html(poster)}' class='hero-bg' alt='{title} 포스터'>
        <div class='hero-overlay'></div>
        <div class='hero-content'>
            <div class='hero-badge'>오늘의 픽</div>
            <div class='hero-title'>{title}</div>
            <div class='hero-meta'>{country} · {genre} · {year} · {runtime} · 감독 {director}</div>
            <div class='hero-desc'>
                지금 분위기에 가장 잘 어울리는 작품으로 보여드리는 추천 카드입니다.
                감정 태그와 상황 태그, 장르 기반 추천이 함께 연결됩니다.
            </div>
            <div class='chip-row'>{감정칩}{특징칩}</div>
            <div class='hero-stats'>
                <div class='hero-stat'>
                    <div class='hero-stat-label'>평점</div>
                    <div class='hero-stat-value'>★ {rating}</div>
                </div>
                <div class='hero-stat'>
                    <div class='hero-stat-label'>관객수</div>
                    <div class='hero-stat-value'>{audience}</div>
                </div>
                <div class='hero-stat'>
                    <div class='hero-stat-label'>글로벌 흥행액</div>
                    <div class='hero-stat-value'>{gross}</div>
                </div>
            </div>
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
    st.caption("기분, 상황, 해시태그, 국가, 장르, 시대별로 영화를 탐색하고 지금 분위기에 맞는 작품을 골라보세요.")

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
        페이지당개수 = st.selectbox("페이지당 카드 수", [8, 10, 12, 15, 20], index=2)

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
    with top1:
        st.metric("전체 영화 수", len(df))
    with top2:
        st.metric("검색 결과 수", len(filtered))
    with top3:
        st.metric("장르 수", df["장르"].nunique())

    if len(filtered) == 0:
        st.warning("조건에 맞는 영화가 없습니다. 필터를 조금 줄여보세요.")
        st.stop()

    선택영화명 = st.selectbox("대표로 볼 영화 선택", filtered["영화명"].tolist(), index=0)
    선택행 = filtered[filtered["영화명"] == 선택영화명].iloc[0]

    st.markdown(히어로HTML생성(선택행, tmdb_api_key), unsafe_allow_html=True)

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
            f"<div style='padding-top:30px; font-size:.95rem;'>현재 <b>{st.session_state['현재페이지']}</b> / 전체 <b>{전체페이지수}</b> 페이지</div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    시작 = (st.session_state["현재페이지"] - 1) * 페이지당개수
    끝 = 시작 + 페이지당개수
    page_df = filtered.iloc[시작:끝].copy()

    st.markdown("<div class='section-title'>지금 많이 보는 영화</div>", unsafe_allow_html=True)
    한줄카드수 = 5
    for start in range(0, len(page_df), 한줄카드수):
        chunk = page_df.iloc[start:start + 한줄카드수]
        cols = st.columns(한줄카드수)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                st.markdown(카드HTML생성(row, tmdb_api_key), unsafe_allow_html=True)

    st.markdown("<div class='section-title'>선택한 영화 상세</div>", unsafe_allow_html=True)
    info1, info2 = st.columns([1.05, 1.95])

    with info1:
        st.image(포스터주소가져오기(선택행, tmdb_api_key), use_container_width=True)

    with info2:
        st.markdown("<div class='detail-panel'>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-head'>{escape(str(선택행['영화명']))}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='detail-meta'>{escape(str(선택행['국가']))} · {escape(str(선택행['장르']))} · "
            f"{('-' if pd.isna(선택행['개봉연도']) else int(선택행['개봉연도']))} · "
            f"{('-' if pd.isna(선택행['상영시간']) else str(int(선택행['상영시간'])) + '분')} · "
            f"감독 {escape(str(선택행['감독']))}</div>",
            unsafe_allow_html=True
        )

        chips = "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(선택행["감정태그"])[:3]])
        chips += "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(선택행["상황태그"])[:3]])
        st.markdown(f"<div class='chip-row'>{chips}</div>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class='detail-grid'>
                <div class='detail-box'>
                    <div class='detail-box-label'>평점</div>
                    <div class='detail-box-value'>★ {('-' if pd.isna(선택행['평점']) else round(float(선택행['평점']), 1))}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>관객수</div>
                    <div class='detail-box-value'>{숫자표시(선택행['관객수'])}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>글로벌 흥행액</div>
                    <div class='detail-box-value'>{금액표시(선택행['글로벌흥행액'])}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>시대 구분</div>
                    <div class='detail-box-value'>{escape(str(선택행['시대구분']))}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>감정 태그</div>
                    <div class='detail-box-value'>{escape(', '.join(태그분리(선택행['감정태그'])) or '-')}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>상황 태그</div>
                    <div class='detail-box-value'>{escape(', '.join(태그분리(선택행['상황태그'])) or '-')}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>특징 태그</div>
                    <div class='detail-box-value'>{escape(', '.join(태그분리(선택행['특징태그'])) or '-')}</div>
                </div>
                <div class='detail-box'>
                    <div class='detail-box-label'>해시태그</div>
                    <div class='detail-box-value'>{escape(', '.join(태그분리(선택행['해시태그'])) or '-')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>같은 장르 추천</div>", unsafe_allow_html=True)
    추천df = df[(df["장르"] == 선택행["장르"]) & (df["영화명"] != 선택행["영화명"])].copy()
    추천df = 추천df.sort_values(["평점", "개봉연도"], ascending=[False, False], na_position="last").head(8)

    rec_cols = st.columns(4)
    for idx, (_, rec) in enumerate(추천df.iterrows()):
        with rec_cols[idx % 4]:
            st.markdown(
                f"""
                <div class='rail-card'>
                    <div class='rail-title'>{escape(str(rec['영화명']))}</div>
                    <div class='rail-sub'>
                        {escape(str(rec['국가']))} · {escape(str(rec['장르']))} · {('-' if pd.isna(rec['개봉연도']) else int(rec['개봉연도']))}<br>
                        평점 {('-' if pd.isna(rec['평점']) else round(float(rec['평점']), 1))} · 특징 {escape(', '.join(태그분리(rec['특징태그'])[:2]) or '-')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("현재 검색 데이터 표 보기"):
        st.dataframe(page_df[표시컬럼], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    메인()
