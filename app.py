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
시대순서 = ["1990년대 이전", "1990년대", "2000년대", "2010년대", "2020년대", "시대 미상"]

COLUMN_ALIASES = {
    "영화명": ["영화명", "title"],
    "개봉연도": ["개봉연도", "year"],
    "시대구분": ["시대구분", "decade"],
    "국가": ["국가", "country"],
    "장르": ["장르", "genre"],
    "세부장르": ["세부장르", "subgenre"],
    "상영시간": ["상영시간", "runtime"],
    "관객수": ["관객수", "audience"],
    "글로벌흥행액": ["글로벌흥행액", "worldwide_gross"],
    "평점": ["평점", "rating"],
    "감독": ["감독", "director"],
    "출연진": ["출연진", "cast"],
    "연령등급": ["연령등급", "age_rating"],
    "한줄요약": ["한줄요약", "summary_short"],
    "짧은소개": ["짧은소개", "short_description"],
    "줄거리": ["줄거리", "synopsis"],
    "감정태그": ["감정태그", "emotion_tags"],
    "상황태그": ["상황태그", "situation_tags"],
    "특징태그": ["특징태그", "feature_tags"],
    "해시태그": ["해시태그", "hashtags"],
    "시리즈": ["시리즈", "series_name"],
    "OTT": ["OTT", "ott_platforms"],
    "예고편URL": ["예고편URL", "trailer_url"],
    "포스터URL": ["포스터URL", "poster_url"],
    "포스터검색어": ["포스터검색어", "poster_query"],
}

표시컬럼 = list(COLUMN_ALIASES.keys())


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


def 목록문자열(items, limit=None):
    if not items:
        return "-"
    if limit is not None:
        items = items[:limit]
    return ", ".join(items)


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


def 러닝타임구간(분):
    if pd.isna(분):
        return "미상"
    분 = int(분)
    if 분 < 100:
        return "100분 미만"
    if 분 < 120:
        return "100~119분"
    if 분 < 140:
        return "120~139분"
    return "140분 이상"


def 장르프로필(장르):
    mapping = {
        "액션": {
            "감정": "전율,쾌감,몰입",
            "상황": "친구와,주말,액션좋아할때",
            "특징": "블록버스터,속도감,카타르시스",
            "해시태그": "액션,몰입,대작",
            "세부장르": "범죄액션",
            "연령등급": "15세 이상",
            "ott": "넷플릭스,디즈니플러스,웨이브",
        },
        "드라마": {
            "감정": "감동,여운,몰입",
            "상황": "혼자,조용한밤,깊게보고싶을때",
            "특징": "인생,서사,감정선",
            "해시태그": "드라마,감동,여운",
            "세부장르": "휴먼드라마",
            "연령등급": "12세 이상",
            "ott": "넷플릭스,왓챠,웨이브",
        },
        "스릴러": {
            "감정": "긴장,불안,몰입",
            "상황": "밤,혼자,반전좋아할때",
            "특징": "반전,심리,서스펜스",
            "해시태그": "스릴러,반전,몰입",
            "세부장르": "심리스릴러",
            "연령등급": "15세 이상",
            "ott": "넷플릭스,티빙,왓챠",
        },
        "로맨스": {
            "감정": "설렘,감성,여운",
            "상황": "연인과,밤,감성적인날",
            "특징": "사랑,청춘,관계",
            "해시태그": "로맨스,감성,설렘",
            "세부장르": "감성로맨스",
            "연령등급": "12세 이상",
            "ott": "넷플릭스,디즈니플러스,쿠팡플레이",
        },
        "애니메이션": {
            "감정": "따뜻함,힐링,감동",
            "상황": "가족과,주말오후,가볍게",
            "특징": "성장,가족,모험",
            "해시태그": "애니메이션,힐링,가족",
            "세부장르": "가족애니메이션",
            "연령등급": "전체관람가",
            "ott": "디즈니플러스,넷플릭스,웨이브",
        },
        "판타지": {
            "감정": "신비로움,몰입,경이로움",
            "상황": "주말,혼자,세계관좋아할때",
            "특징": "세계관,마법,모험",
            "해시태그": "판타지,모험,세계관",
            "세부장르": "판타지어드벤처",
            "연령등급": "12세 이상",
            "ott": "디즈니플러스,넷플릭스,티빙",
        },
        "코미디": {
            "감정": "유쾌함,웃김,가벼움",
            "상황": "친구와,주말,웃고싶을때",
            "특징": "웃음,기분전환,템포",
            "해시태그": "코미디,웃김,가볍게",
            "세부장르": "버디코미디",
            "연령등급": "12세 이상",
            "ott": "넷플릭스,티빙,쿠팡플레이",
        },
        "SF": {
            "감정": "경이로움,몰입,사색",
            "상황": "혼자,주말밤,생각하고싶을때",
            "특징": "우주,미래,설정",
            "해시태그": "SF,우주,세계관",
            "세부장르": "미래SF",
            "연령등급": "12세 이상",
            "ott": "넷플릭스,디즈니플러스,애플TV+",
        },
    }
    return mapping.get(
        장르,
        {
            "감정": "몰입,감상",
            "상황": "혼자,주말",
            "특징": "영화,스토리",
            "해시태그": "영화,추천",
            "세부장르": "일반",
            "연령등급": "12세 이상",
            "ott": "넷플릭스",
        },
    )


def 시리즈추출(영화명):
    rules = [
        ("어벤져스", "어벤져스 시리즈"),
        ("범죄도시", "범죄도시 시리즈"),
        ("신과함께", "신과함께 시리즈"),
        ("겨울왕국", "겨울왕국 시리즈"),
        ("아바타", "아바타 시리즈"),
        ("해리 포터", "해리 포터 시리즈"),
        ("킹스맨", "킹스맨 시리즈"),
        ("007", "007 시리즈"),
        ("적벽대전", "삼국지 시리즈"),
    ]
    for key, value in rules:
        if key in 영화명:
            return value
    return ""


def 출연진생성(국가, 장르, idx):
    pools = {
        "한국": ["송강호", "황정민", "이병헌", "전지현", "정우성", "박정민", "마동석", "김혜수"],
        "미국": ["레오나르도 디카프리오", "톰 크루즈", "로버트 다우니 주니어", "엠마 스톤", "라이언 고슬링", "크리스 에반스"],
        "영국": ["콜린 퍼스", "에디 레드메인", "휴 그랜트", "케이라 나이틀리", "대니얼 크레이그"],
        "스페인": ["하비에르 바르뎀", "페넬로페 크루즈", "벨렌 루에다", "마리오 카사스"],
        "인도": ["아미르 칸", "샤룩 칸", "란비르 카푸르", "디피카 파두콘", "알리아 바트"],
        "일본": ["기무라 타쿠야", "히로세 스즈", "아라가키 유이", "야마자키 켄토"],
        "중국": ["이연걸", "장쯔이", "공리", "주윤발", "주성치"],
        "대만": ["계륜미", "천이한", "왕대륙", "가진동", "주걸륜"],
    }
    base = pools.get(국가, ["배우A", "배우B", "배우C"])
    a = base[idx % len(base)]
    b = base[(idx + 2) % len(base)]
    c = base[(idx + 4) % len(base)]
    if 장르 == "애니메이션":
        return f"{a}, {b} (성우), {c} (성우)"
    return f"{a}, {b}, {c}"


def 한줄요약생성(장르, 특징태그):
    특징 = 태그분리(특징태그)
    핵심 = 특징[0] if 특징 else "몰입감"
    mapping = {
        "액션": f"{핵심}이 강한 통쾌한 액션 영화",
        "드라마": f"{핵심}을 중심으로 감정을 쌓아가는 드라마",
        "스릴러": f"{핵심}이 살아 있는 몰입형 스릴러",
        "로맨스": f"{핵심}과 감성이 어우러진 로맨스",
        "애니메이션": f"{핵심}과 따뜻함이 어우러진 가족 애니메이션",
        "판타지": f"{핵심}이 돋보이는 판타지 모험극",
        "코미디": f"{핵심}으로 기분 좋게 웃을 수 있는 코미디",
        "SF": f"{핵심}과 세계관이 매력적인 SF 영화",
    }
    return mapping.get(장르, "지금 보기 좋은 추천 영화")


def 짧은소개생성(영화명, 국가, 장르):
    return f"{국가}에서 화제가 되었던 {장르} 영화로, {영화명} 특유의 분위기와 몰입감이 돋보이는 작품입니다."


def 줄거리생성(영화명, 장르, 특징태그):
    특징 = 목록문자열(태그분리(특징태그), 3)
    return (
        f"{영화명}은(는) {장르} 장르의 매력을 중심으로 전개되는 작품입니다. "
        f"{특징} 요소를 바탕으로 관객을 몰입시키며, "
        f"인물의 선택과 감정의 흐름이 또렷하게 살아 있어 끝까지 집중해서 보기 좋습니다."
    )


def 예고편URL생성(query):
    q = str(query).replace(" ", "+")
    return f"https://www.youtube.com/results?search_query={q}+official+trailer"


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
        ],
        "한국": [
            ("명량", 2014, "액션", 128, 7.1, "김한민", "The Admiral Roaring Currents"),
            ("극한직업", 2019, "코미디", 111, 7.1, "이병헌", "Extreme Job"),
            ("신과함께-죄와 벌", 2017, "판타지", 139, 7.2, "김용화", "Along with the Gods The Two Worlds"),
            ("신과함께-인과 연", 2018, "판타지", 141, 7.1, "김용화", "Along with the Gods The Last 49 Days"),
            ("국제시장", 2014, "드라마", 126, 7.8, "윤제균", "Ode to My Father"),
            ("베테랑", 2015, "액션", 123, 7.0, "류승완", "Veteran 2015"),
            ("서울의 봄", 2023, "드라마", 141, 8.3, "김성수", "12.12 The Day"),
            ("암살", 2015, "액션", 139, 7.3, "최동훈", "Assassination 2015"),
            ("범죄도시 2", 2022, "액션", 106, 7.2, "이상용", "The Roundup"),
            ("범죄도시 3", 2023, "액션", 105, 6.6, "이상용", "The Roundup No Way Out"),
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
            ("엑시트", 2019, "액션", 103, 7.0, "이상근", "Exit"),
            ("내부자들", 2015, "드라마", 130, 7.8, "우민호", "Inside Men"),
            ("1987", 2017, "드라마", 129, 7.8, "장준환", "1987 When the Day Comes"),
            ("건축학개론", 2012, "로맨스", 118, 7.2, "이용주", "Architecture 101"),
            ("늑대소년", 2012, "판타지", 125, 7.2, "조성희", "A Werewolf Boy"),
            ("한산: 용의 출현", 2022, "액션", 129, 6.6, "김한민", "Hansan Rising Dragon"),
            ("검사외전", 2016, "코미디", 126, 6.7, "이일형", "A Violent Prosecutor"),
            ("말아톤", 2005, "드라마", 117, 7.7, "정윤철", "Marathon"),
            ("써니", 2011, "코미디", 124, 7.8, "강형철", "Sunny"),
            ("부당거래", 2010, "스릴러", 119, 7.2, "류승완", "The Unjust"),
            ("마더", 2009, "스릴러", 129, 7.8, "봉준호", "Mother 2009"),
            ("타짜", 2006, "드라마", 139, 7.2, "최동훈", "Tazza The High Rollers"),
            ("추격자", 2008, "스릴러", 125, 7.8, "나홍진", "The Chaser"),
        ],
        "영국": [
            ("007 스카이폴", 2012, "액션", 143, 7.8, "샘 멘데스", "Skyfall"),
            ("해리 포터와 죽음의 성물 2", 2011, "판타지", 130, 8.1, "데이비드 예이츠", "Harry Potter and the Deathly Hallows Part 2"),
            ("킹스 스피치", 2010, "드라마", 118, 8.0, "톰 후퍼", "The King's Speech"),
            ("노팅 힐", 1999, "로맨스", 124, 7.2, "로저 미첼", "Notting Hill"),
            ("패딩턴 2", 2017, "애니메이션", 103, 7.8, "폴 킹", "Paddington 2"),
        ],
        "스페인": [
            ("판의 미로", 2006, "판타지", 118, 8.2, "기예르모 델 토로", "Pan's Labyrinth"),
            ("더 임파서블", 2012, "드라마", 114, 7.6, "후안 안토니오 바요나", "The Impossible"),
            ("인비저블 게스트", 2016, "스릴러", 106, 8.0, "오리올 파울로", "The Invisible Guest"),
        ],
        "인도": [
            ("세 얼간이", 2009, "코미디", 170, 8.4, "라지쿠마르 히라니", "3 Idiots"),
            ("당갈", 2016, "드라마", 161, 8.3, "니테시 티와리", "Dangal"),
            ("RRR", 2022, "액션", 182, 7.8, "S. S. 라자몰리", "RRR"),
        ],
        "일본": [
            ("센과 치히로의 행방불명", 2001, "애니메이션", 125, 8.6, "미야자키 하야오", "Spirited Away"),
            ("너의 이름은", 2016, "로맨스", 106, 8.4, "신카이 마코토", "Your Name"),
            ("고질라 마이너스 원", 2023, "액션", 124, 8.0, "야마자키 타카시", "Godzilla Minus One"),
        ],
        "중국": [
            ("와호장룡", 2000, "액션", 120, 7.9, "이안", "Crouching Tiger Hidden Dragon"),
            ("영웅", 2002, "드라마", 99, 7.9, "장이머우", "Hero 2002"),
            ("쿵푸허슬", 2004, "코미디", 99, 7.7, "주성치", "Kung Fu Hustle"),
        ],
        "대만": [
            ("말할 수 없는 비밀", 2007, "로맨스", 101, 7.5, "주걸륜", "Secret 2007"),
            ("그 시절, 우리가 좋아했던 소녀", 2011, "드라마", 109, 7.6, "구파도", "You Are the Apple of My Eye"),
            ("메리 마이 데드 바디", 2023, "코미디", 130, 7.3, "청웨이하오", "Marry My Dead Body"),
        ],
    }

    rows = []
    idx = 1
    for 국가, movies in movie_map.items():
        for 영화명, 개봉연도, 장르, 상영시간, 평점, 감독, 포스터검색어 in movies:
            profile = 장르프로필(장르)
            rows.append({
                "영화명": 영화명,
                "개봉연도": 개봉연도,
                "국가": 국가,
                "장르": 장르,
                "세부장르": profile["세부장르"],
                "상영시간": 상영시간,
                "관객수": 500000 + idx * 9321,
                "글로벌흥행액": 25000000 + idx * 1750000,
                "평점": 평점,
                "감독": 감독,
                "출연진": 출연진생성(국가, 장르, idx),
                "연령등급": profile["연령등급"],
                "한줄요약": 한줄요약생성(장르, profile["특징"]),
                "짧은소개": 짧은소개생성(영화명, 국가, 장르),
                "줄거리": 줄거리생성(영화명, 장르, profile["특징"]),
                "감정태그": profile["감정"],
                "상황태그": profile["상황"],
                "특징태그": profile["특징"],
                "해시태그": profile["해시태그"],
                "시리즈": 시리즈추출(영화명),
                "OTT": profile["ott"],
                "예고편URL": 예고편URL생성(포스터검색어),
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
        normalized[target] = df[found] if found is not None else ""

    out = pd.DataFrame(normalized)

    문자컬럼 = [
        "영화명", "시대구분", "국가", "장르", "세부장르", "감독", "출연진", "연령등급",
        "한줄요약", "짧은소개", "줄거리", "감정태그", "상황태그", "특징태그",
        "해시태그", "시리즈", "OTT", "예고편URL", "포스터URL", "포스터검색어"
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
      <rect width='100%' height='100%' fill='#0f172a'/>
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
        resp = requests.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=10)
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
    query = str(row.get("포스터검색어", "")).strip() or str(row.get("영화명", "")).strip()
    year = row.get("개봉연도", None)
    tmdb_url = tmdb포스터가져오기(query, year, tmdb_api_key)
    if tmdb_url:
        return tmdb_url
    return 대체포스터생성(row.get("영화명", ""), row.get("장르", ""), row.get("개봉연도", None))


def 카드HTML생성(row, tmdb_api_key):
    title = escape(str(row["영화명"]))
    country = escape(str(row["국가"]))
    genre = escape(str(row["장르"]))
    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{float(row['평점']):.1f}"
    one_liner = escape(str(row["한줄요약"]))
    age_rating = escape(str(row["연령등급"]))
    ott_text = escape(목록문자열(태그분리(row["OTT"]), 2))
    poster = 포스터주소가져오기(row, tmdb_api_key)

    hover_text = f"{genre} · {runtime} · ★ {rating}<br>{age_rating} · {ott_text}"

    return f"""
    <div class='movie-card'>
        <div class='poster-wrap'>
            <img src='{포스터주소_html(poster)}' class='poster-img' alt='{title} 포스터'>

            <div class='poster-top-badges'>
                <span class='poster-badge'>{genre}</span>
                <span class='poster-badge'>★ {rating}</span>
            </div>

            <div class='poster-hover'>
                <div class='poster-hover-box'>
                    {hover_text}
                </div>
            </div>
        </div>

        <div class='card-info'>
            <div class='card-title'>{title}</div>
            <div class='card-meta'>{country} · {year} · {runtime} · {age_rating}</div>
            <div class='card-summary'>{one_liner}</div>
        </div>
    </div>
    """


def 포스터주소_html(url):
    return escape(url, quote=True)


def 카드HTML생성(row, tmdb_api_key):
    title = escape(str(row["영화명"]))
    country = escape(str(row["국가"]))
    genre = escape(str(row["장르"]))
    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{float(row['평점']):.1f}"
    one_liner = escape(str(row["한줄요약"]))
    poster = 포스터주소가져오기(row, tmdb_api_key)

    return f"""
    <div class='movie-card'>
        <div class='poster-wrap'>
            <img src='{포스터주소_html(poster)}' class='poster-img' alt='{title} 포스터'>
            <div class='card-gradient'></div>
            <div class='card-bottom'>
                <div class='card-title'>{title}</div>
                <div class='card-sub'>{country} · {genre} · {year} · {runtime} · ★ {rating}</div>
                <div class='card-sub' style='margin-top:6px;'>{one_liner}</div>
            </div>
            <div class='card-hover'>
                <div><b>{title}</b> ({year})</div>
                <div>국가: {country}</div>
                <div>장르: {genre}</div>
                <div>상영시간: {runtime}</div>
                <div>연령등급: {escape(str(row['연령등급']))}</div>
                <div>OTT: {escape(str(row['OTT']))}</div>
                <div>감독: {escape(str(row['감독']))}</div>
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

    chips = "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(row["감정태그"])[:3]])
    chips += "".join([f"<span class='chip'>{escape(t)}</span>" for t in 태그분리(row["특징태그"])[:3]])

    return f"""
    <div class='hero-wrap'>
        <img src='{포스터주소_html(poster)}' class='hero-bg' alt='{title} 포스터'>
        <div class='hero-overlay'></div>
        <div class='hero-content'>
            <div class='hero-badge'>오늘의 픽</div>
            <div class='hero-title'>{title}</div>
            <div class='hero-meta'>{country} · {genre} · {year} · {runtime} · 감독 {director}</div>
            <div class='hero-desc'>{escape(str(row["짧은소개"]))}</div>
            <div class='hero-desc' style='font-size:.95rem;'>{escape(str(row["한줄요약"]))}</div>
            <div class='chip-row'>{chips}</div>
            <div class='hero-stats'>
                <div class='hero-stat'><div class='hero-stat-label'>평점</div><div class='hero-stat-value'>★ {rating}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>관객수</div><div class='hero-stat-value'>{audience}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>글로벌 흥행액</div><div class='hero-stat-value'>{gross}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>연령등급</div><div class='hero-stat-value'>{escape(str(row["연령등급"]))}</div></div>
            </div>
        </div>
    </div>
    """


def 추천섹션(title, data, tmdb_api_key, cols_per_row=5):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if len(data) == 0:
        st.info("표시할 영화가 없습니다.")
        return
    for start in range(0, len(data), cols_per_row):
        chunk = data.iloc[start:start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                st.markdown(카드HTML생성(row, tmdb_api_key), unsafe_allow_html=True)


def 세션초기화():
    if "wishlist" not in st.session_state:
        st.session_state["wishlist"] = []
    if "watched" not in st.session_state:
        st.session_state["watched"] = []
    if "rewatch" not in st.session_state:
        st.session_state["rewatch"] = []
    if "user_rating" not in st.session_state:
        st.session_state["user_rating"] = {}
    if "user_review" not in st.session_state:
        st.session_state["user_review"] = {}
    if "현재페이지" not in st.session_state:
        st.session_state["현재페이지"] = 1


def 리스트토글(key, value):
    arr = st.session_state[key]
    if value in arr:
        arr.remove(value)
    else:
        arr.append(value)
    st.session_state[key] = arr


def 메인():
    세션초기화()

    with st.sidebar:
        st.subheader("설정")
        다크모드 = st.toggle("다크모드", value=True)
        uploaded = st.file_uploader("CSV 또는 XLSX 업로드", type=["csv", "xlsx"])

    스타일적용(다크모드)

    st.title("🎬 무드픽")
    st.caption("영화를 찾는 것보다, 지금의 분위기에 맞는 작품을 고르기 쉽게 만들어주는 탐색형 추천 서비스")

    tmdb_api_key = None
    if "TMDB_API_KEY" in st.secrets:
        tmdb_api_key = st.secrets["TMDB_API_KEY"]

    with st.sidebar:
        st.caption("실제 포스터를 자동으로 불러오려면 TMDb API Key를 넣어주세요.")
        manual_tmdb = st.text_input("TMDb API Key", type="password", value=tmdb_api_key or "")
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

    with st.sidebar:
        st.subheader("필터")
        선택국가 = st.multiselect("국가", [x for x in 사용가능국가 if x in df["국가"].unique().tolist()])
        선택장르 = st.multiselect("장르", sorted(df["장르"].dropna().unique().tolist()))
        선택세부장르 = st.multiselect("세부장르", sorted(df["세부장르"].dropna().unique().tolist()))
        선택시대 = st.multiselect("시대", [x for x in 시대순서 if x in df["시대구분"].unique().tolist()])
        선택감정 = st.multiselect("기분 태그", sorted({tag for text in df["감정태그"] for tag in 태그분리(text)}))
        선택상황 = st.multiselect("상황 태그", sorted({tag for text in df["상황태그"] for tag in 태그분리(text)}))
        선택연령등급 = st.multiselect("연령등급", sorted(df["연령등급"].dropna().unique().tolist()))
        선택OTT = st.multiselect("OTT", sorted({tag for text in df["OTT"] for tag in 태그분리(text)}))
        러닝타임옵션 = st.multiselect("러닝타임", ["100분 미만", "100~119분", "120~139분", "140분 이상"])
        해시태그검색 = st.text_input("해시태그 검색", placeholder="#반전, #힐링")
        일반검색 = st.text_input("영화명 / 감독 / 배우 / 특징 검색")
        정렬기준 = st.selectbox("정렬", ["평점 높은 순", "최신순", "관객수 높은 순", "영화명순", "짧은 러닝타임순"])
        페이지당개수 = st.selectbox("페이지당 카드 수", [8, 10, 12, 15, 20], index=2)

    filtered = df.copy()
    if 선택국가:
        filtered = filtered[filtered["국가"].isin(선택국가)]
    if 선택장르:
        filtered = filtered[filtered["장르"].isin(선택장르)]
    if 선택세부장르:
        filtered = filtered[filtered["세부장르"].isin(선택세부장르)]
    if 선택시대:
        filtered = filtered[filtered["시대구분"].isin(선택시대)]
    if 선택감정:
        filtered = filtered[filtered["감정태그"].apply(lambda x: 모든태그포함여부(x, 선택감정))]
    if 선택상황:
        filtered = filtered[filtered["상황태그"].apply(lambda x: 모든태그포함여부(x, 선택상황))]
    if 선택연령등급:
        filtered = filtered[filtered["연령등급"].isin(선택연령등급)]
    if 선택OTT:
        filtered = filtered[filtered["OTT"].apply(lambda x: all(t in 태그분리(x) for t in 선택OTT))]
    if 러닝타임옵션:
        filtered = filtered[filtered["상영시간"].apply(lambda x: 러닝타임구간(x) in 러닝타임옵션)]
    if 해시태그검색.strip():
        query_tags = [t.lstrip("#") for t in 태그분리(해시태그검색.replace(" ", ","))]
        filtered = filtered[filtered["해시태그"].apply(lambda x: any(q.lower() in str(x).lower().replace("#", "") for q in query_tags))]
    if 일반검색.strip():
        q = 일반검색.lower()
        filtered = filtered[
            filtered["영화명"].str.lower().str.contains(q, na=False)
            | filtered["감독"].str.lower().str.contains(q, na=False)
            | filtered["출연진"].str.lower().str.contains(q, na=False)
            | filtered["특징태그"].str.lower().str.contains(q, na=False)
            | filtered["줄거리"].str.lower().str.contains(q, na=False)
        ]

    if 정렬기준 == "평점 높은 순":
        filtered = filtered.sort_values(["평점", "개봉연도"], ascending=[False, False], na_position="last")
    elif 정렬기준 == "최신순":
        filtered = filtered.sort_values(["개봉연도", "평점"], ascending=[False, False], na_position="last")
    elif 정렬기준 == "관객수 높은 순":
        filtered = filtered.sort_values(["관객수", "평점"], ascending=[False, False], na_position="last")
    elif 정렬기준 == "짧은 러닝타임순":
        filtered = filtered.sort_values(["상영시간", "평점"], ascending=[True, False], na_position="last")
    else:
        filtered = filtered.sort_values("영화명", ascending=True)

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("전체 영화 수", len(df))
    top2.metric("검색 결과 수", len(filtered))
    top3.metric("찜한 영화", len(st.session_state["wishlist"]))
    top4.metric("본 영화", len(st.session_state["watched"]))

    if len(filtered) == 0:
        st.warning("조건에 맞는 영화가 없습니다. 필터를 조금 줄여보세요.")
        st.stop()

    선택영화명 = st.selectbox("대표로 볼 영화 선택", filtered["영화명"].tolist(), index=0)
    선택행 = filtered[filtered["영화명"] == 선택영화명].iloc[0]

    st.markdown(히어로HTML생성(선택행, tmdb_api_key), unsafe_allow_html=True)

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        if st.button("🤍 찜하기 / 해제", use_container_width=True):
            리스트토글("wishlist", 선택영화명)
    with a2:
        if st.button("✅ 본 영화 체크", use_container_width=True):
            리스트토글("watched", 선택영화명)
    with a3:
        if st.button("🔁 다시 보고 싶음", use_container_width=True):
            리스트토글("rewatch", 선택영화명)
    with a4:
        st.link_button("▶ 예고편 보기", str(선택행["예고편URL"]), use_container_width=True)

    전체페이지수 = max(1, math.ceil(len(filtered) / 페이지당개수))
    if st.session_state["현재페이지"] > 전체페이지수:
        st.session_state["현재페이지"] = 전체페이지수

    st.markdown("<div class='page-box'>", unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns([1, 1, 2, 2])
    with p1:
        if st.button("◀ 이전 페이지", use_container_width=True):
            st.session_state["현재페이지"] = max(1, st.session_state["현재페이지"] - 1)
    with p2:
        if st.button("다음 페이지 ▶", use_container_width=True):
            st.session_state["현재페이지"] = min(전체페이지수, st.session_state["현재페이지"] + 1)
    with p3:
        현재페이지입력 = st.number_input("페이지 번호", min_value=1, max_value=전체페이지수, value=st.session_state["현재페이지"], step=1)
        st.session_state["현재페이지"] = 현재페이지입력
    with p4:
        st.markdown(f"<div style='padding-top:30px; font-size:.95rem;'>현재 <b>{st.session_state['현재페이지']}</b> / 전체 <b>{전체페이지수}</b> 페이지</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    시작 = (st.session_state["현재페이지"] - 1) * 페이지당개수
    끝 = 시작 + 페이지당개수
    page_df = filtered.iloc[시작:끝].copy()

    추천섹션("지금 많이 보는 영화", page_df, tmdb_api_key, cols_per_row=5)
    추천섹션("한국 흥행작 모음", df[df["국가"] == "한국"].sort_values("관객수", ascending=False).head(10), tmdb_api_key, cols_per_row=5)
    추천섹션("감성 로맨스 모음", df[df["장르"] == "로맨스"].sort_values("평점", ascending=False).head(10), tmdb_api_key, cols_per_row=5)
    추천섹션("몰입감 높은 스릴러", df[df["장르"] == "스릴러"].sort_values("평점", ascending=False).head(10), tmdb_api_key, cols_per_row=5)

    st.markdown("<div class='section-title'>선택한 영화 상세</div>", unsafe_allow_html=True)
    info1, info2 = st.columns([1.0, 2.0])
    with info1:
        st.image(포스터주소가져오기(선택행, tmdb_api_key), use_container_width=True)
    with info2:
        st.markdown("<div class='detail-panel'>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-head'>{escape(str(선택행['영화명']))}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='detail-meta'>{escape(str(선택행['국가']))} · {escape(str(선택행['장르']))} · "
            f"{escape(str(선택행['세부장르']))} · {('-' if pd.isna(선택행['개봉연도']) else int(선택행['개봉연도']))} · "
            f"{('-' if pd.isna(선택행['상영시간']) else str(int(선택행['상영시간'])) + '분')} · "
            f"{escape(str(선택행['연령등급']))}</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**한 줄 요약**: {선택행['한줄요약']}")
        st.markdown(f"**짧은 소개**: {선택행['짧은소개']}")
        st.markdown(f"**줄거리**: {선택행['줄거리']}")
        st.markdown(f"**감독**: {선택행['감독']}")
        st.markdown(f"**출연진**: {선택행['출연진']}")
        st.markdown(f"**OTT 제공**: {선택행['OTT']}")
        if str(선택행["시리즈"]).strip():
            st.markdown(f"**시리즈 / 세계관**: {선택행['시리즈']}")

        st.markdown(
            f"""
            <div class='detail-grid'>
                <div class='detail-box'><div class='detail-box-label'>평점</div><div class='detail-box-value'>★ {('-' if pd.isna(선택행['평점']) else round(float(선택행['평점']), 1))}</div></div>
                <div class='detail-box'><div class='detail-box-label'>관객수</div><div class='detail-box-value'>{숫자표시(선택행['관객수'])}</div></div>
                <div class='detail-box'><div class='detail-box-label'>글로벌 흥행액</div><div class='detail-box-value'>{금액표시(선택행['글로벌흥행액'])}</div></div>
                <div class='detail-box'><div class='detail-box-label'>러닝타임 구간</div><div class='detail-box-value'>{러닝타임구간(선택행['상영시간'])}</div></div>
                <div class='detail-box'><div class='detail-box-label'>감정 태그</div><div class='detail-box-value'>{escape(목록문자열(태그분리(선택행['감정태그'])))}</div></div>
                <div class='detail-box'><div class='detail-box-label'>상황 태그</div><div class='detail-box-value'>{escape(목록문자열(태그분리(선택행['상황태그'])))}</div></div>
                <div class='detail-box'><div class='detail-box-label'>특징 태그</div><div class='detail-box-value'>{escape(목록문자열(태그분리(선택행['특징태그'])))}</div></div>
                <div class='detail-box'><div class='detail-box-label'>해시태그</div><div class='detail-box-value'>{escape(목록문자열(태그분리(선택행['해시태그'])))}</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>내 평가 / 한 줄 리뷰</div>", unsafe_allow_html=True)
    r1, r2 = st.columns([1, 2])
    with r1:
        user_score = st.slider("내 평점", 0.0, 10.0, float(st.session_state["user_rating"].get(선택영화명, 8.0)), 0.5)
        if st.button("내 평점 저장", use_container_width=True):
            st.session_state["user_rating"][선택영화명] = user_score
    with r2:
        current_review = st.session_state["user_review"].get(선택영화명, "")
        review_text = st.text_area("한 줄 리뷰", value=current_review, height=100, placeholder="예: 긴장감이 끝까지 유지되는 반전 스릴러")
        if st.button("리뷰 저장", use_container_width=True):
            st.session_state["user_review"][선택영화명] = review_text

    st.markdown("<div class='section-title'>비슷한 작품 추천</div>", unsafe_allow_html=True)
    같은장르 = df[(df["장르"] == 선택행["장르"]) & (df["영화명"] != 선택행["영화명"])].sort_values(["평점", "개봉연도"], ascending=[False, False]).head(6)
    같은감독 = df[(df["감독"] == 선택행["감독"]) & (df["영화명"] != 선택행["영화명"])].sort_values(["평점", "개봉연도"], ascending=[False, False]).head(6)
    시리즈추천 = df[(df["시리즈"] == 선택행["시리즈"]) & (df["영화명"] != 선택행["영화명"])].sort_values(["평점", "개봉연도"], ascending=[False, False]).head(6) if str(선택행["시리즈"]).strip() else df.iloc[0:0]
    배우목록 = 태그분리(str(선택행["출연진"]).replace(" (성우)", ""))
    같은배우 = df[df["영화명"] != 선택행["영화명"]].copy()
    같은배우 = 같은배우[같은배우["출연진"].apply(lambda x: any(actor in str(x) for actor in 배우목록))]
    같은배우 = 같은배우.sort_values(["평점", "개봉연도"], ascending=[False, False]).head(6)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**같은 장르**")
        for _, rec in 같은장르.iterrows():
            st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['국가']))} · {escape(str(rec['장르']))} · 평점 {rec['평점']}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("**같은 감독**")
        if len(같은감독) == 0:
            st.info("같은 감독 작품이 없습니다.")
        else:
            for _, rec in 같은감독.iterrows():
                st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['감독']))} · {escape(str(rec['국가']))}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("**같은 배우**")
        if len(같은배우) == 0:
            st.info("같은 배우 기반 추천이 없습니다.")
        else:
            for _, rec in 같은배우.iterrows():
                st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['출연진']))}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown("**같은 시리즈 / 세계관**")
        if len(시리즈추천) == 0:
            st.info("같은 시리즈 추천이 없습니다.")
        else:
            for _, rec in 시리즈추천.iterrows():
                st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['시리즈']))}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>내 리스트</div>", unsafe_allow_html=True)
    l1, l2, l3 = st.columns(3)
    with l1:
        st.markdown("**찜한 영화**")
        st.write(st.session_state["wishlist"] if st.session_state["wishlist"] else ["없음"])
    with l2:
        st.markdown("**본 영화**")
        st.write(st.session_state["watched"] if st.session_state["watched"] else ["없음"])
    with l3:
        st.markdown("**다시 보고 싶은 영화**")
        st.write(st.session_state["rewatch"] if st.session_state["rewatch"] else ["없음"])

    with st.expander("현재 검색 데이터 표 보기"):
        st.dataframe(page_df[표시컬럼], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    메인()
