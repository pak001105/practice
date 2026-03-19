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


def 기본데이터생성():
    data = [
        ["아바타",2009,"미국","SF",162,13300000,2923710708,7.9,"제임스 카메론","몰입,경이로움,압도감","주말,혼자,대작보고싶을때","우주,외계행성,블록버스터","SF,블록버스터,우주,미국","Avatar"],
        ["어벤져스: 엔드게임",2019,"미국","액션",181,13977409,2799439100,8.4,"안소니 루소, 조 루소","전율,쾌감,감동","친구와,주말밤,대작좋아할때","히어로,팀업,대서사","액션,히어로,마블,미국","Avengers Endgame"],
        ["인터스텔라",2014,"미국","SF",169,10309432,731000000,8.7,"크리스토퍼 놀란","몰입,경이로움,울림","혼자,생각하고싶을때,주말밤","우주,철학,부성애","SF,우주,명작,미국","Interstellar"],
        ["인셉션",2010,"미국","스릴러",148,5827444,839000000,8.8,"크리스토퍼 놀란","긴장,몰입,전율","혼자,집중하고싶을때,밤","꿈,반전,두뇌게임","스릴러,반전,두뇌게임,미국","Inception"],
        ["다크 나이트",2008,"미국","액션",152,4175526,1006000000,9.0,"크리스토퍼 놀란","전율,긴장,압도감","혼자,친구와,명작감상","히어로,범죄,명작","액션,히어로,명작,미국","The Dark Knight"],
        ["타이타닉",1997,"미국","로맨스",194,1970000,2264812968,7.9,"제임스 카메론","슬픔,설렘,여운","연인과,감성적인날,밤","실화감성,대서사,비극","로맨스,명작,비극,미국","Titanic"],
        ["라라랜드",2016,"미국","로맨스",128,3600000,471000000,8.0,"데이미언 셔젤","설렘,감성,여운","연인과,밤,감성적인날","뮤지컬,꿈,사랑","로맨스,뮤지컬,감성,미국","La La Land"],
        ["겨울왕국",2013,"미국","애니메이션",102,10296101,1280000000,7.4,"크리스 벅, 제니퍼 리","따뜻함,설렘,희망","가족과,아이와함께,주말오후","뮤지컬,공주,자매","애니메이션,가족,디즈니,미국","Frozen"],
        ["인사이드 아웃",2015,"미국","애니메이션",95,4970000,857000000,8.1,"피트 닥터","힐링,따뜻함,감동","가족과,혼자,가볍게","성장,감정,가족","애니메이션,힐링,가족,미국","Inside Out"],
        ["쇼생크 탈출",1994,"미국","드라마",142,1200000,29000000,9.3,"프랭크 다라본트","희망,감동,울림","혼자,깊게보고싶을때,명작감상","감옥,인생,명작","드라마,명작,희망,미국","The Shawshank Redemption"],

        ["명량",2014,"한국","액션",128,17616682,138000000,7.1,"김한민","비장함,전율,웅장함","가족과,명절,대작보고싶을때","전쟁,실존인물,흥행작","액션,전쟁,흥행작,한국","The Admiral Roaring Currents"],
        ["극한직업",2019,"한국","코미디",111,16266480,120000000,7.1,"이병헌","유쾌함,웃김,가벼움","친구와,가족과,스트레스풀고싶을때","형사,코믹,흥행작","코미디,웃김,흥행작,한국","Extreme Job"],
        ["신과함께-죄와 벌",2017,"한국","판타지",139,14414658,109000000,7.2,"김용화","감동,몰입,웅장함","가족과,주말,대작좋아할때","사후세계,가족,판타지","판타지,대작,한국영화,한국","Along with the Gods The Two Worlds"],
        ["국제시장",2014,"한국","드라마",126,14257115,99000000,7.8,"윤제균","감동,울림,뭉클함","가족과,명절,감동받고싶을때","가족,시대극,실화감성","드라마,가족,감동,한국","Ode to My Father"],
        ["베테랑",2015,"한국","액션",123,13414009,92000000,7.0,"류승완","쾌감,통쾌함,몰입","친구와,주말,통쾌한영화원할때","형사,범죄,추격","액션,범죄,통쾌함,한국","Veteran 2015"],
        ["서울의 봄",2023,"한국","드라마",141,13127824,97000000,8.3,"김성수","긴장,분노,몰입","혼자,역사영화보고싶을때,주말","실화감성,정치,시대극","드라마,실화감성,시대극,한국","12.12 The Day"],
        ["암살",2015,"한국","액션",139,12706247,90000000,7.3,"최동훈","전율,몰입,쾌감","가족과,주말,대작보고싶을때","독립운동,저격,시대극","액션,시대극,독립운동,한국","Assassination 2015"],
        ["범죄도시 2",2022,"한국","액션",106,12693415,101000000,7.2,"이상용","통쾌함,속도감,쾌감","친구와,주말,가볍게액션보고싶을때","형사,범죄,시리즈","액션,범죄,통쾌함,한국","The Roundup"],
        ["부산행",2016,"한국","스릴러",118,11565078,98000000,7.6,"연상호","긴장,감동,몰입","친구와,밤,몰입하고싶을때","좀비,재난,부성애","스릴러,좀비,재난,한국","Train to Busan"],
        ["기생충",2019,"한국","스릴러",132,10317247,262000000,8.5,"봉준호","긴장,충격,몰입","혼자,친구와,주말밤","사회풍자,반전,수상작","스릴러,반전,수상작,한국","Parasite"],

        ["007 스카이폴",2012,"영국","액션",143,1300000,1109000000,7.8,"샘 멘데스","전율,긴장,쾌감","친구와,주말,액션보고싶을때","첩보,시리즈,흥행작","액션,첩보,007,영국","Skyfall"],
        ["해리 포터와 죽음의 성물 2",2011,"영국","판타지",130,4500000,1342000000,8.1,"데이비드 예이츠","전율,감동,몰입","친구와,주말,시리즈정주행", "마법,시리즈,판타지","판타지,마법,영국,시리즈","Harry Potter and the Deathly Hallows Part 2"],
        ["킹스 스피치",2010,"영국","드라마",118,1000000,427000000,8.0,"톰 후퍼","감동,희망,울림","혼자,조용한밤,좋은영화보고싶을때","실화,수상작,왕실","드라마,실화,수상작,영국","The King's Speech"],
        ["노팅 힐",1999,"영국","로맨스",124,800000,364000000,7.2,"로저 미첼","설렘,따뜻함,기분좋음","연인과,주말밤,편하게","로맨틱코미디,명작,영국감성","로맨스,영국,감성,설렘","Notting Hill"],
        ["패딩턴 2",2017,"영국","애니메이션",103,300000,228000000,7.8,"폴 킹","따뜻함,힐링,유쾌함","가족과,주말오후,가볍게","가족,모험,영국감성","애니메이션,힐링,가족,영국","Paddington 2"],
        ["28일 후",2002,"영국","스릴러",113,200000,85000000,7.5,"대니 보일","불안,긴장,공포","밤,혼자,몰입하고싶을때","좀비,재난,서스펜스","스릴러,좀비,재난,영국","28 Days Later"],

        ["판의 미로",2006,"스페인","판타지",118,300000,83000000,8.2,"기예르모 델 토로","어두움,몰입,여운","혼자,밤,분위기있는영화","판타지,전쟁,명작","판타지,전쟁,명작,스페인","Pan's Labyrinth"],
        ["더 임파서블",2012,"스페인","드라마",114,400000,198000000,7.6,"후안 안토니오 바요나","긴장,감동,절박함","가족과,몰입,실화좋아할때","실화,재난,가족","드라마,실화,재난,스페인","The Impossible"],
        ["줄리아의 눈",2010,"스페인","스릴러",118,100000,0,6.7,"기옘 모랄레스","불안,긴장,서늘함","밤,혼자,스릴원할때","미스터리,심리,반전","스릴러,심리,반전,스페인","Julia's Eyes"],
        ["오픈 유어 아이즈",1997,"스페인","SF",119,50000,0,7.7,"알레한드로 아메나바르","혼란,몰입,충격","혼자,생각하고싶을때,밤","반전,심리,SF","SF,반전,심리,스페인","Open Your Eyes"],
        ["토렌테",1998,"스페인","코미디",97,50000,0,6.8,"산티아고 세구라","유쾌함,병맛,가벼움","친구와,가볍게,웃고싶을때","블랙코미디,컬트,시리즈","코미디,컬트,스페인,웃김","Torrente"],
        ["타데오 존스",2012,"스페인","애니메이션",92,100000,45000000,6.1,"엔리케 가토","모험,유쾌함,편안함","가족과,아이와함께,주말","모험,가족,애니메이션","애니메이션,가족,모험,스페인","Tad The Lost Explorer"],

        ["세 얼간이",2009,"인도","코미디",170,4500000,90000000,8.4,"라지쿠마르 히라니","유쾌함,감동,희망","친구와,가족과,기분전환","청춘,우정,명작","코미디,청춘,우정,인도","3 Idiots"],
        ["당갈",2016,"인도","드라마",161,3000000,311000000,8.3,"니테시 티와리","열정,감동,뭉클함","가족과,동기부여받고싶을때,주말","실화,스포츠,가족","드라마,실화,스포츠,인도","Dangal"],
        ["바후발리: 더 비기닝",2015,"인도","액션",159,2000000,100000000,8.0,"S. S. 라자몰리","웅장함,전율,쾌감","친구와,주말,대작보고싶을때","전쟁,판타지,대서사","액션,대서사,인도,전쟁","Baahubali The Beginning"],
        ["런치박스",2013,"인도","로맨스",104,300000,23000000,7.8,"리테쉬 바트라","잔잔함,따뜻함,여운","혼자,감성적인날,조용한밤","편지,일상,감성","로맨스,감성,여운,인도","The Lunchbox"],
        ["안다둔",2018,"인도","스릴러",139,800000,45000000,8.2,"스리람 라가반","긴장,몰입,충격","혼자,밤,반전좋아할때","반전,범죄,블랙코미디","스릴러,반전,범죄,인도","Andhadhun"],
        ["RRR",2022,"인도","액션",182,1000000,160000000,7.8,"S. S. 라자몰리","전율,쾌감,압도감","친구와,주말,대작좋아할때","시대극,액션,버디", "액션,대작,인도,버디","RRR"],

        ["센과 치히로의 행방불명",2001,"일본","애니메이션",125,2160000,395000000,8.6,"미야자키 하야오","신비로움,감동,몰입","가족과,혼자,명작보고싶을때","판타지,성장,명작","애니메이션,판타지,명작,일본","Spirited Away"],
        ["너의 이름은",2016,"일본","로맨스",106,3710000,382000000,8.4,"신카이 마코토","설렘,감성,여운","연인과,혼자,밤","애니메이션,판타지,청춘","로맨스,애니메이션,청춘,일본","Your Name"],
        ["고질라 마이너스 원",2023,"일본","액션",124,600000,115000000,8.0,"야마자키 타카시","긴장,웅장함,몰입","주말,친구와,대작보고싶을때","괴수,재난,전쟁","액션,괴수,재난,일본","Godzilla Minus One"],
        ["링",1998,"일본","스릴러",96,200000,19000000,7.2,"나카타 히데오","공포,불안,서늘함","밤,혼자,공포좋아할때","공포,저주,심리","스릴러,공포,저주,일본","Ringu"],
        ["어느 가족",2018,"일본","드라마",121,300000,75000000,7.9,"고레에다 히로카즈","잔잔함,여운,먹먹함","혼자,조용한밤,생각하고싶을때","가족,사회,수상작","드라마,가족,수상작,일본","Shoplifters"],
        ["하울의 움직이는 성",2004,"일본","판타지",119,1500000,236000000,8.2,"미야자키 하야오","설렘,신비로움,따뜻함","가족과,혼자,감성적인날","마법,전쟁,성장","판타지,애니메이션,마법,일본","Howl's Moving Castle"],

        ["와호장룡",2000,"중국","액션",120,400000,213000000,7.9,"이안","아름다움,몰입,전율","혼자,주말밤,명작감상","무협,명작,수상작","액션,무협,명작,중국","Crouching Tiger Hidden Dragon"],
        ["영웅",2002,"중국","드라마",99,300000,177000000,7.9,"장이머우","웅장함,비장함,몰입","혼자,영상미좋아할때,주말","무협,미장센,역사","드라마,무협,영상미,중국","Hero 2002"],
        ["유랑지구",2019,"중국","SF",125,1000000,700000000,6.0,"궈판","웅장함,긴장,몰입","친구와,주말,대작좋아할때","우주,재난,SF","SF,재난,우주,중국","The Wandering Earth"],
        ["안녕 리",2021,"중국","코미디",128,800000,820000000,7.7,"자 링","유쾌함,감동,뭉클함","가족과,친구와,편하게","타임슬립,가족,코미디","코미디,가족,감동,중국","Hi Mom 2021"],
        ["소시대",2013,"중국","로맨스",116,200000,79000000,5.0,"궈징밍","화려함,가벼움,설렘","친구와,가볍게,트렌디한영화보고싶을때","청춘,도시,패션","로맨스,청춘,도시,중국","Tiny Times"],
        ["장진호",2021,"중국","스릴러",176,500000,913000000,5.5,"천카이거 외","긴장,비장함,압도감","주말,대작좋아할때,혼자","전쟁,실화감성,대작","스릴러,전쟁,대작,중국","The Battle at Lake Changjin"],

        ["말할 수 없는 비밀",2007,"대만","로맨스",101,1600000,14000000,7.5,"주걸륜","설렘,감성,여운","연인과,혼자,감성적인날","음악,학원물,판타지","로맨스,음악,감성,대만","Secret 2007"],
        ["그 시절, 우리가 좋아했던 소녀",2011,"대만","드라마",109,500000,21000000,7.6,"구파도","청춘,그리움,설렘","혼자,추억에잠길때,밤","청춘,첫사랑,학원","드라마,청춘,첫사랑,대만","You Are the Apple of My Eye"],
        ["카페 6",2016,"대만","코미디",103,100000,0,6.4,"오자운","청량함,가벼움,설렘","친구와,가볍게,주말오후","청춘,캠퍼스,감성","코미디,청춘,감성,대만","At Cafe 6"],
        ["더 새드니스",2021,"대만","스릴러",99,50000,0,6.4,"롭 자바즈","공포,불쾌함,긴장","밤,혼자,강한자극원할때","고어,바이러스,극한","스릴러,공포,고어,대만","The Sadness"],
        ["실크",2006,"대만","판타지",108,50000,0,6.4,"수 차오빈","서늘함,신비로움,몰입","밤,혼자,분위기있는영화","유령,초자연,미스터리","판타지,미스터리,유령,대만","Silk 2006"],
        ["청설",2009,"대만","드라마",109,300000,0,7.5,"정펀펀","따뜻함,잔잔함,설렘","연인과,혼자,조용한날","청춘,로맨스,감성","드라마,청춘,감성,대만","Hear Me 2009"],
    ]

    columns = [
        "영화명","개봉연도","국가","장르","상영시간","관객수","글로벌흥행액","평점","감독",
        "감정태그","상황태그","특징태그","해시태그","포스터검색어"
    ]

    df = pd.DataFrame(data, columns=columns)
    df["포스터URL"] = ""
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
        section.main h1, section.main h2, section.main h3, section.main h4, section.main h5, section.main h6,
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
    st.caption("업로드 없이도 기본 영화 데이터를 바로 볼 수 있습니다. 파일을 올리면 업로드한 데이터가 우선 적용됩니다.")

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
