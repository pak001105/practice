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

사용가능국가 = ["미국", "한국", "영국", "스페인", "인도", "일본", "중국", "대만", "프랑스", "이탈리아", "독일", "멕시코", "호주", "캐나다", "덴마크", "이란", "아르헨티나"]
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
    "수상여부": ["수상여부", "awards"],
    "대표리뷰": ["대표리뷰", "featured_review"],
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
        "공포": {
            "감정": "공포,긴장,스릴",
            "상황": "밤,혼자,겁없을때",
            "특징": "공포,음산함,충격",
            "해시태그": "공포,호러,긴장",
            "세부장르": "심리공포",
            "연령등급": "18세 이상",
            "ott": "넷플릭스,왓챠,웨이브",
        },
        "범죄": {
            "감정": "긴장,몰입,통쾌함",
            "상황": "혼자,밤,반전좋아할때",
            "특징": "범죄,두뇌싸움,반전",
            "해시태그": "범죄,두뇌,반전",
            "세부장르": "범죄스릴러",
            "연령등급": "15세 이상",
            "ott": "넷플릭스,왓챠,티빙",
        },
        "뮤지컬": {
            "감정": "설렘,감동,흥겨움",
            "상황": "연인과,기분좋을때,음악좋아할때",
            "특징": "음악,노래,춤",
            "해시태그": "뮤지컬,음악,감동",
            "세부장르": "뮤지컬드라마",
            "연령등급": "전체관람가",
            "ott": "넷플릭스,디즈니플러스,애플TV+",
        },
        "다큐멘터리": {
            "감정": "경이로움,사색,감동",
            "상황": "혼자,생각하고싶을때,공부할때",
            "특징": "실화,사실,통찰",
            "해시태그": "다큐,실화,통찰",
            "세부장르": "자연다큐",
            "연령등급": "전체관람가",
            "ott": "넷플릭스,왓챠,애플TV+",
        },
        "전쟁": {
            "감정": "긴장,감동,숙연함",
            "상황": "혼자,진지하게볼때",
            "특징": "전쟁,역사,인간",
            "해시태그": "전쟁,역사,인간",
            "세부장르": "전쟁드라마",
            "연령등급": "15세 이상",
            "ott": "넷플릭스,왓챠,디즈니플러스",
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
        ("어벤져스", "마블 시네마틱 유니버스"),
        ("아이언맨", "마블 시네마틱 유니버스"),
        ("캡틴 아메리카", "마블 시네마틱 유니버스"),
        ("토르", "마블 시네마틱 유니버스"),
        ("블랙팬서", "마블 시네마틱 유니버스"),
        ("스파이더맨", "마블 시네마틱 유니버스"),
        ("범죄도시", "범죄도시 시리즈"),
        ("신과함께", "신과함께 시리즈"),
        ("겨울왕국", "겨울왕국 시리즈"),
        ("아바타", "아바타 시리즈"),
        ("해리 포터", "해리 포터 시리즈"),
        ("킹스맨", "킹스맨 시리즈"),
        ("007", "007 시리즈"),
        ("적벽대전", "삼국지 시리즈"),
        ("분노의 질주", "분노의 질주 시리즈"),
        ("미션 임파서블", "미션 임파서블 시리즈"),
        ("존 윅", "존 윅 시리즈"),
        ("매트릭스", "매트릭스 시리즈"),
        ("반지의 제왕", "반지의 제왕 시리즈"),
        ("호빗", "반지의 제왕 세계관"),
        ("토이 스토리", "토이 스토리 시리즈"),
        ("인크레더블", "인크레더블 시리즈"),
        ("쿵푸팬더", "쿵푸팬더 시리즈"),
        ("슈렉", "슈렉 시리즈"),
    ]
    for key, value in rules:
        if key in 영화명:
            return value
    return ""


def 수상여부생성(영화명):
    awards_map = {
        "기생충": "아카데미 작품상·감독상·각본상·국제영화상 4관왕",
        "조커": "베니스국제영화제 황금사자상, 아카데미 남우주연상",
        "라라랜드": "아카데미 감독상·여우주연상 포함 6개 부문 수상",
        "킹스 스피치": "아카데미 작품상·감독상·남우주연상 포함 4관왕",
        "센과 치히로의 행방불명": "아카데미 장편애니메이션상, 베를린영화제 황금곰상",
        "올드보이": "칸영화제 심사위원대상",
        "판의 미로": "아카데미 촬영·미술·분장상 수상",
        "와호장룡": "아카데미 외국어영화상·촬영상 포함 4관왕",
        "노매드랜드": "아카데미 작품상·감독상·여우주연상 3관왕",
        "드라이브 마이 카": "아카데미 국제영화상, 칸영화제 각본상",
        "로마": "아카데미 감독상·국제영화상·촬영상 수상",
        "문라이트": "아카데미 작품상·각색상·남우조연상 수상",
        "위플래쉬": "아카데미 편집·녹음·남우조연상 수상",
        "버드맨": "아카데미 작품상·감독상·각본상·촬영상 수상",
        "그래비티": "아카데미 감독상·촬영상 포함 7관왕",
        "아티스트": "아카데미 작품상·감독상·남우주연상 수상",
        "헤어질 결심": "칸영화제 감독상",
        "브로커": "칸영화제 남우주연상 (송강호)",
    }
    return awards_map.get(영화명, "흥행 및 평단 호평")


def 대표리뷰생성(장르, 영화명):
    mapping = {
        "액션": f"{영화명}은 속도감과 몰입감이 좋아서 큰 화면으로 볼수록 매력이 살아납니다.",
        "드라마": f"{영화명}은 감정선이 차곡차곡 쌓여서 보고 난 뒤 여운이 오래 남는 작품입니다.",
        "스릴러": f"{영화명}은 긴장감을 오래 유지하면서도 전개가 흥미롭게 이어지는 편입니다.",
        "로맨스": f"{영화명}은 감성적인 분위기와 관계의 흐름을 섬세하게 담아낸 작품입니다.",
        "애니메이션": f"{영화명}은 보기 편하면서도 따뜻한 메시지가 남는 작품입니다.",
        "판타지": f"{영화명}은 세계관과 비주얼이 강점이라 몰입해서 보기 좋습니다.",
        "코미디": f"{영화명}은 분위기를 가볍게 만들고 싶을 때 보기 좋은 영화입니다.",
        "SF": f"{영화명}은 설정과 세계관을 따라가는 재미가 큰 작품입니다.",
        "공포": f"{영화명}은 분위기와 긴장감이 끝까지 살아있어 공포 팬에게 추천합니다.",
        "범죄": f"{영화명}은 두뇌 싸움과 반전이 매력적인 범죄 영화입니다.",
        "뮤지컬": f"{영화명}은 음악과 영상미가 어우러져 보는 내내 즐거운 작품입니다.",
        "전쟁": f"{영화명}은 전쟁의 참혹함과 인간의 의지를 동시에 담아낸 수작입니다.",
    }
    return mapping.get(장르, f"{영화명}은 지금 분위기에 맞춰 보기 좋은 추천작입니다.")


def 출연진생성(국가, 장르, idx):
    pools = {
        "한국": ["송강호", "황정민", "이병헌", "전지현", "정우성", "박정민", "마동석", "김혜수", "유아인", "공유", "하정우", "전도연", "손예진", "조정석", "류준열", "박서준"],
        "미국": ["레오나르도 디카프리오", "톰 크루즈", "로버트 다우니 주니어", "엠마 스톤", "라이언 고슬링", "크리스 에반스", "브래드 피트", "앤젤리나 졸리", "메릴 스트립", "케이트 블란쳇", "조니 뎁", "맷 데이먼", "조지 클루니", "나탈리 포트만"],
        "영국": ["콜린 퍼스", "에디 레드메인", "휴 그랜트", "케이라 나이틀리", "대니얼 크레이그", "케이트 윈슬렛", "베네딕트 컴버배치", "톰 히들스턴"],
        "스페인": ["하비에르 바르뎀", "페넬로페 크루즈", "벨렌 루에다", "마리오 카사스", "안토니오 반데라스"],
        "인도": ["아미르 칸", "샤룩 칸", "란비르 카푸르", "디피카 파두콘", "알리아 바트", "살만 칸"],
        "일본": ["기무라 타쿠야", "히로세 스즈", "아라가키 유이", "야마자키 켄토", "마츠야마 켄이치", "나가사와 마사미"],
        "중국": ["이연걸", "장쯔이", "공리", "주윤발", "주성치", "양조위", "장국영"],
        "대만": ["계륜미", "천이한", "왕대륙", "가진동", "주걸륜", "서약선"],
        "프랑스": ["오드리 토투", "뱅상 카셀", "마리옹 코티아르", "장 뤽 고다르", "이자벨 위페르"],
        "이탈리아": ["모니카 벨루치", "로베르토 베니니", "소피아 로렌", "마르첼로 마스트로이안니"],
        "독일": ["다이안 크루거", "미카엘 하네케", "팀 뵈르나르"],
        "멕시코": ["가엘 가르시아 베르날", "디에고 루나", "살마 아이엑"],
        "호주": ["니콜 키드먼", "케이트 블란쳇", "휴 잭맨", "멜 깁슨"],
        "캐나다": ["라이언 레이놀즈", "짐 캐리", "마이크 마이어스", "킬리안 머피"],
        "덴마크": ["마즈 미켈슨", "다리아 비코브스카야"],
        "이란": ["레이라 하타미", "마니아 아크바리"],
        "아르헨티나": ["리카르도 다린", "메르세데스 모란"],
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
        "공포": f"섬뜩한 {핵심}이 가득한 공포 영화",
        "범죄": f"{핵심}이 넘치는 긴장감 있는 범죄 영화",
        "뮤지컬": f"노래와 {핵심}이 어우러진 뮤지컬 영화",
        "전쟁": f"{핵심}과 인간의 의지를 그린 전쟁 영화",
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
            ("아바타", 2009, "SF", 162, 7.9, "제임스 카메론", "Avatar 2009"),
            ("아바타: 물의 길", 2022, "SF", 192, 7.6, "제임스 카메론", "Avatar The Way of Water"),
            ("어벤져스: 엔드게임", 2019, "액션", 181, 8.4, "안소니 루소, 조 루소", "Avengers Endgame"),
            ("어벤져스: 인피니티 워", 2018, "액션", 149, 8.4, "안소니 루소, 조 루소", "Avengers Infinity War"),
            ("타이타닉", 1997, "로맨스", 194, 7.9, "제임스 카메론", "Titanic 1997"),
            ("인터스텔라", 2014, "SF", 169, 8.7, "크리스토퍼 놀란", "Interstellar 2014"),
            ("다크 나이트", 2008, "액션", 152, 9.0, "크리스토퍼 놀란", "The Dark Knight 2008"),
            ("라라랜드", 2016, "뮤지컬", 128, 8.0, "데이미언 셔젤", "La La Land 2016"),
            ("조커", 2019, "드라마", 122, 8.4, "토드 필립스", "Joker 2019"),
            ("그래비티", 2013, "SF", 91, 7.7, "알폰소 쿠아론", "Gravity 2013"),
            ("노매드랜드", 2020, "드라마", 108, 7.3, "클로이 자오", "Nomadland 2020"),
            ("문라이트", 2016, "드라마", 111, 7.4, "배리 젠킨스", "Moonlight 2016"),
            ("위플래쉬", 2014, "드라마", 107, 8.5, "데이미언 셔젤", "Whiplash 2014"),
            ("버드맨", 2014, "드라마", 119, 7.7, "알레한드로 곤살레스 이냐리투", "Birdman 2014"),
            ("매드맥스: 분노의 도로", 2015, "액션", 120, 8.1, "조지 밀러", "Mad Max Fury Road 2015"),
            ("존 윅", 2014, "액션", 101, 7.4, "채드 스타헬스키", "John Wick 2014"),
            ("인셉션", 2010, "SF", 148, 8.8, "크리스토퍼 놀란", "Inception 2010"),
            ("쇼생크 탈출", 1994, "드라마", 142, 9.3, "프랭크 다라본트", "The Shawshank Redemption"),
            ("포레스트 검프", 1994, "드라마", 142, 8.8, "로버트 저메키스", "Forrest Gump 1994"),
            ("레옹", 1994, "액션", 110, 8.5, "뤽 베송", "Leon The Professional"),
            ("펄프 픽션", 1994, "범죄", 154, 8.9, "쿠엔틴 타란티노", "Pulp Fiction 1994"),
            ("양들의 침묵", 1991, "스릴러", 118, 8.6, "조나단 드미", "The Silence of the Lambs"),
            ("매트릭스", 1999, "SF", 136, 8.7, "워쇼스키 자매", "The Matrix 1999"),
            ("분노의 질주: 더 얼티메이트", 2009, "액션", 107, 6.5, "저스틴 린", "Fast and Furious 2009"),
            ("미션 임파서블: 폴아웃", 2018, "액션", 147, 7.7, "크리스토퍼 맥쿼리", "Mission Impossible Fallout"),
            ("토이 스토리 4", 2019, "애니메이션", 100, 7.7, "조시 쿨리", "Toy Story 4"),
            ("코코", 2017, "애니메이션", 105, 8.4, "리 언크리치", "Coco 2017"),
            ("소울", 2020, "애니메이션", 100, 8.0, "피트 닥터", "Soul Pixar 2020"),
            ("업", 2009, "애니메이션", 96, 8.2, "피트 닥터", "Up Pixar 2009"),
            ("월-E", 2008, "애니메이션", 98, 8.4, "앤드루 스탠튼", "WALL-E 2008"),
            ("겨울왕국 2", 2019, "애니메이션", 103, 6.8, "크리스 벅, 제니퍼 리", "Frozen 2 2019"),
            ("반지의 제왕: 반지 원정대", 2001, "판타지", 178, 8.8, "피터 잭슨", "Lord of the Rings Fellowship"),
            ("해리 포터와 마법사의 돌", 2001, "판타지", 152, 7.6, "크리스 콜럼버스", "Harry Potter Sorcerers Stone"),
            ("나이트메어", 2021, "공포", 110, 7.5, "스콧 쿠퍼", "Antlers 2021"),
            ("겟 아웃", 2017, "공포", 104, 7.7, "조던 필", "Get Out 2017"),
            ("어스", 2019, "공포", 116, 6.8, "조던 필", "Us 2019"),
            ("허트 로커", 2008, "전쟁", 131, 7.5, "캐스린 비글로우", "The Hurt Locker"),
            ("덩케르크", 2017, "전쟁", 106, 7.4, "크리스토퍼 놀란", "Dunkirk 2017"),
            ("블랙호크 다운", 2001, "전쟁", 144, 7.7, "리들리 스콧", "Black Hawk Down"),
            ("아이리시맨", 2019, "범죄", 209, 7.8, "마틴 스코세이지", "The Irishman 2019"),
            ("기묘한 이야기", 2021, "SF", 130, 8.0, "더퍼 브라더스", "Stranger Things Movie"),
            ("탑건: 매버릭", 2022, "액션", 130, 8.3, "조셉 코신스키", "Top Gun Maverick"),
            ("오펜하이머", 2023, "드라마", 180, 8.9, "크리스토퍼 놀란", "Oppenheimer 2023"),
            ("바비", 2023, "코미디", 114, 6.9, "그레타 거윅", "Barbie 2023"),
            ("가디언즈 오브 갤럭시 3", 2023, "SF", 150, 8.0, "제임스 건", "Guardians of the Galaxy 3"),
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
            ("범죄도시 3", 2023, "액션", 105, 7.0, "이상용", "The Roundup 3"),
            ("7번방의 선물", 2013, "코미디", 127, 8.2, "이환경", "Miracle in Cell No 7"),
            ("도둑들", 2012, "액션", 135, 6.8, "최동훈", "The Thieves"),
            ("변호인", 2013, "드라마", 127, 7.7, "양우석", "The Attorney"),
            ("부산행", 2016, "스릴러", 118, 7.6, "연상호", "Train to Busan"),
            ("기생충", 2019, "스릴러", 132, 8.5, "봉준호", "Parasite 2019"),
            ("올드보이", 2003, "스릴러", 120, 8.4, "박찬욱", "Oldboy 2003"),
            ("괴물", 2006, "스릴러", 119, 7.1, "봉준호", "The Host 2006"),
            ("헤어질 결심", 2022, "로맨스", 138, 7.3, "박찬욱", "Decision to Leave"),
            ("과속스캔들", 2008, "코미디", 108, 7.2, "강형철", "Scandal Makers"),
            ("광해, 왕이 된 남자", 2012, "드라마", 131, 7.8, "추창민", "Masquerade"),
            ("내부자들", 2015, "드라마", 130, 7.8, "우민호", "Inside Men"),
            ("1987", 2017, "드라마", 129, 7.8, "장준환", "1987 When the Day Comes"),
            ("밀정", 2016, "액션", 140, 7.1, "김지운", "The Age of Shadows"),
            ("택시운전사", 2017, "드라마", 137, 7.7, "장훈", "A Taxi Driver"),
            ("공작", 2018, "스릴러", 137, 7.4, "윤종빈", "The Spy Gone North"),
            ("남산의 부장들", 2020, "드라마", 114, 7.3, "우민호", "The Man Standing Next"),
            ("강철비", 2017, "액션", 139, 7.3, "양우석", "Steel Rain"),
            ("아수라", 2016, "범죄", 134, 7.1, "김성수", "Asura The City of Madness"),
            ("신세계", 2013, "범죄", 134, 8.2, "박훈정", "New World 2013"),
            ("베를린", 2013, "액션", 135, 7.3, "류승완", "The Berlin File"),
            ("끝까지 간다", 2014, "스릴러", 111, 7.9, "김성훈", "A Hard Day"),
            ("악마를 보았다", 2010, "스릴러", 141, 7.8, "김지운", "I Saw the Devil"),
            ("친절한 금자씨", 2005, "드라마", 112, 7.5, "박찬욱", "Sympathy for Lady Vengeance"),
            ("봄날은 간다", 2001, "로맨스", 106, 7.7, "허진호", "One Fine Spring Day"),
            ("클래식", 2003, "로맨스", 127, 7.8, "곽재용", "The Classic"),
            ("엽기적인 그녀", 2001, "로맨스", 122, 7.8, "곽재용", "My Sassy Girl Korean"),
            ("건축학개론", 2012, "로맨스", 117, 7.7, "엄태화", "Architecture 101"),
            ("써니", 2011, "드라마", 124, 7.8, "강형철", "Sunny 2011 Korean"),
            ("수상한 그녀", 2014, "코미디", 124, 7.5, "황동혁", "Miss Granny 2014"),
            ("완벽한 타인", 2018, "코미디", 101, 7.7, "이재규", "Intimate Strangers Korean"),
            ("기억의 밤", 2017, "스릴러", 109, 6.9, "장항준", "Forgotten 2017 Korean"),
            ("곡성", 2016, "공포", 156, 7.4, "나홍진", "The Wailing"),
            ("파묘", 2024, "공포", 134, 7.3, "장재현", "Exhuma 2024"),
            ("범죄도시 4", 2024, "액션", 109, 7.1, "허명행", "The Roundup 4"),
            ("웡카", 2024, "뮤지컬", 116, 7.2, "폴 킹", "Wonka 2024"),
            ("브로커", 2022, "드라마", 129, 7.2, "고레에다 히로카즈", "Broker 2022"),
            ("비상선언", 2022, "스릴러", 140, 6.0, "한재림", "Emergency Declaration"),
            ("외계+인 1부", 2022, "SF", 142, 5.8, "최동훈", "Alienoid Part 1"),
        ],
        "영국": [
            ("007 스카이폴", 2012, "액션", 143, 7.8, "샘 멘데스", "Skyfall 2012"),
            ("007 노 타임 투 다이", 2021, "액션", 163, 7.3, "캐리 후쿠나가", "No Time To Die"),
            ("해리 포터와 죽음의 성물 2", 2011, "판타지", 130, 8.1, "데이비드 예이츠", "Harry Potter Deathly Hallows 2"),
            ("킹스 스피치", 2010, "드라마", 118, 8.0, "톰 후퍼", "The Kings Speech"),
            ("킹스맨: 시크릿 에이전트", 2014, "액션", 129, 7.7, "매튜 본", "Kingsman Secret Service"),
            ("1917", 2019, "전쟁", 119, 8.3, "샘 멘데스", "1917 2019"),
            ("파이트 클럽", 1999, "드라마", 139, 8.8, "데이비드 핀처", "Fight Club 1999"),
            ("블랙미러: 밴더스내치", 2018, "SF", 90, 7.2, "데이비드 슐로스버그", "Black Mirror Bandersnatch"),
            ("어바웃 타임", 2013, "로맨스", 123, 7.8, "리처드 커티스", "About Time 2013"),
            ("러브 액츄얼리", 2003, "로맨스", 135, 7.6, "리처드 커티스", "Love Actually 2003"),
            ("브리짓 존스의 일기", 2001, "로맨스", 97, 6.7, "샤론 맥과이어", "Bridget Jones Diary"),
            ("노팅 힐", 1999, "로맨스", 124, 7.2, "로저 미첼", "Notting Hill 1999"),
            ("패딩턴 2", 2017, "코미디", 103, 7.8, "폴 킹", "Paddington 2"),
            ("오만과 편견", 2005, "로맨스", 129, 7.8, "조 라이트", "Pride and Prejudice 2005"),
            ("셰익스피어 인 러브", 1998, "로맨스", 123, 7.1, "존 매든", "Shakespeare in Love"),
            ("빌리 엘리어트", 2000, "드라마", 110, 7.7, "스티븐 달드리", "Billy Elliot 2000"),
        ],
        "스페인": [
            ("판의 미로", 2006, "판타지", 118, 8.2, "기예르모 델 토로", "Pans Labyrinth"),
            ("인비저블 게스트", 2016, "스릴러", 106, 8.0, "오리올 파울로", "The Invisible Guest"),
            ("더 바디", 2012, "스릴러", 108, 7.4, "오리올 파울로", "The Body 2012"),
            ("플랫폼", 2019, "스릴러", 94, 7.0, "가우데르 가스테아고이티아", "The Platform 2019"),
            ("버고니아", 2010, "드라마", 90, 7.2, "넬리 부엔디아", "Buried 2010"),
            ("오픈 유어 아이즈", 1997, "SF", 117, 7.8, "알레한드로 아메나바르", "Open Your Eyes 1997"),
            ("악마의 등뼈", 2001, "공포", 106, 7.5, "기예르모 델 토로", "The Devils Backbone"),
        ],
        "인도": [
            ("세 얼간이", 2009, "코미디", 170, 8.4, "라지쿠마르 히라니", "3 Idiots"),
            ("당갈", 2016, "드라마", 161, 8.3, "니테시 티와리", "Dangal"),
            ("PK", 2014, "코미디", 153, 8.1, "라지쿠마르 히라니", "PK 2014"),
            ("발리우드 퀸", 2014, "드라마", 116, 8.1, "비카스 발 굴", "Queen 2014"),
            ("RRR", 2022, "액션", 187, 7.8, "라자무울리", "RRR 2022"),
            ("바후발리: 더 비기닝", 2015, "액션", 159, 8.1, "라자무울리", "Baahubali The Beginning"),
            ("딜왈레 둘하니야 레 자옌게", 1995, "로맨스", 189, 8.1, "아디트야 초프라", "Dilwale Dulhania Le Jayenge"),
            ("무투", 1995, "액션", 166, 7.7, "K. S. 라비쿠마르", "Muthu Tamil"),
            ("슈퍼 30", 2019, "드라마", 152, 7.3, "비카스 발 굴", "Super 30 2019"),
        ],
        "일본": [
            ("센과 치히로의 행방불명", 2001, "애니메이션", 125, 8.6, "미야자키 하야오", "Spirited Away"),
            ("너의 이름은", 2016, "로맨스", 106, 8.4, "신카이 마코토", "Your Name Kimi no Na wa"),
            ("모노노케 히메", 1997, "애니메이션", 134, 8.4, "미야자키 하야오", "Princess Mononoke"),
            ("하울의 움직이는 성", 2004, "애니메이션", 119, 8.2, "미야자키 하야오", "Howls Moving Castle"),
            ("이웃집 토토로", 1988, "애니메이션", 86, 8.1, "미야자키 하야오", "My Neighbor Totoro"),
            ("날씨의 아이", 2019, "로맨스", 114, 7.5, "신카이 마코토", "Weathering With You"),
            ("스즈메의 문단속", 2022, "애니메이션", 122, 7.8, "신카이 마코토", "Suzume 2022"),
            ("드라이브 마이 카", 2021, "드라마", 179, 7.8, "하마구치 류스케", "Drive My Car"),
            ("링", 1998, "공포", 96, 7.2, "나카타 히데오", "Ringu 1998"),
            ("배틀 로얄", 2000, "스릴러", 114, 7.5, "키타노 타케시", "Battle Royale 2000"),
            ("하나비", 1997, "드라마", 103, 7.5, "키타노 타케시", "Hana-bi 1997"),
            ("도라에몽: 스탠바이미", 2014, "애니메이션", 95, 7.0, "다카하시 료이치", "Stand by Me Doraemon"),
            ("귀멸의 칼날: 무한열차편", 2020, "애니메이션", 117, 8.2, "소토자키 하루오", "Demon Slayer Mugen Train"),
            ("극장판 주술회전 0", 2021, "애니메이션", 105, 7.9, "박성후", "Jujutsu Kaisen 0"),
            ("더 퍼스트 슬램덩크", 2022, "애니메이션", 124, 8.3, "이노우에 타케히코", "The First Slam Dunk"),
        ],
        "중국": [
            ("와호장룡", 2000, "액션", 120, 7.9, "이안", "Crouching Tiger Hidden Dragon"),
            ("쿵푸허슬", 2004, "코미디", 99, 7.7, "주성치", "Kung Fu Hustle"),
            ("영웅", 2002, "액션", 99, 7.9, "장이머우", "Hero 2002"),
            ("연인", 2004, "로맨스", 119, 7.5, "장이머우", "House of Flying Daggers"),
            ("귀향", 2014, "드라마", 99, 7.4, "장이머우", "Coming Home 2014"),
            ("적벽대전", 2008, "액션", 148, 7.0, "오우삼", "Red Cliff 2008"),
            ("나의 소녀시대", 2015, "로맨스", 131, 7.8, "천위샨", "Our Times 2015 Taiwan"),
            ("유랑지구", 2019, "SF", 125, 7.0, "궈판", "The Wandering Earth"),
            ("유랑지구 2", 2023, "SF", 173, 7.7, "궈판", "The Wandering Earth 2"),
            ("장강 7호", 2008, "SF", 86, 6.4, "주성치", "CJ7 2008"),
            ("소림축구", 2001, "코미디", 87, 7.4, "주성치", "Shaolin Soccer"),
        ],
        "대만": [
            ("말할 수 없는 비밀", 2007, "로맨스", 101, 7.5, "주걸륜", "Secret 2007"),
            ("메리 마이 데드 바디", 2023, "코미디", 130, 7.3, "청웨이하오", "Marry My Dead Body"),
            ("나의 소녀시대", 2015, "로맨스", 131, 7.8, "천위샨", "Our Times 2015"),
            ("그 시절 우리가 좋아했던 소녀", 2011, "로맨스", 110, 7.5, "주더신", "You Are the Apple of My Eye"),
            ("오색", 2020, "드라마", 107, 7.5, "청웨이하오", "The Falls"),
        ],
        "프랑스": [
            ("아멜리에", 2001, "로맨스", 122, 8.3, "장 피에르 주네", "Amelie 2001"),
            ("레 미제라블", 2019, "드라마", 104, 7.7, "라지 리", "Les Miserables 2019"),
            ("비밀은 없다", 2010, "스릴러", 108, 7.2, "에릭 라르티고", "The Secret 2010"),
            ("피아노 치는 여자", 2001, "드라마", 130, 7.2, "미하엘 하네케", "The Piano Teacher"),
            ("인투쳐블: 1%의 우정", 2011, "드라마", 112, 8.5, "올리비에 나카쉐", "The Intouchables"),
            ("사랑은 아무나 하나", 2014, "로맨스", 96, 7.5, "졸리 퀸", "Love at First Fight"),
            ("마틸다", 1996, "코미디", 98, 7.0, "대니 드비토", "Matilda 1996"),
            ("블루는 따뜻한 색", 2013, "드라마", 179, 7.8, "압델라티프 케시슈", "Blue is the Warmest Color"),
            ("미드나잇 인 파리", 2011, "로맨스", 94, 7.7, "우디 앨런", "Midnight in Paris"),
        ],
        "이탈리아": [
            ("인생은 아름다워", 1997, "드라마", 116, 8.6, "로베르토 베니니", "Life is Beautiful"),
            ("시네마 천국", 1988, "드라마", 155, 8.5, "주세페 토르나토레", "Cinema Paradiso"),
            ("일 포스티노", 1994, "드라마", 108, 7.7, "마이클 래드포드", "Il Postino"),
            ("말레나", 2000, "드라마", 92, 7.5, "주세페 토르나토레", "Malena 2000"),
            ("위대한 아름다움", 2013, "드라마", 142, 7.7, "파울로 소렌티노", "The Great Beauty"),
        ],
        "독일": [
            ("타인의 삶", 2006, "드라마", 137, 8.4, "플로리안 헨켈 폰 도너스마르크", "The Lives of Others"),
            ("굿바이 레닌!", 2003, "코미디", 121, 7.7, "볼프강 베커", "Goodbye Lenin"),
            ("베로니카 포스의 갈망", 1982, "드라마", 104, 7.5, "라이너 베르너 파스빈더", "Veronika Voss"),
            ("작전명 발키리", 2008, "전쟁", 121, 7.1, "브라이언 싱어", "Valkyrie 2008"),
            ("Das Boot", 1981, "전쟁", 149, 8.3, "볼프강 페터젠", "Das Boot 1981"),
        ],
        "멕시코": [
            ("로마", 2018, "드라마", 135, 7.7, "알폰소 쿠아론", "Roma 2018"),
            ("아무르", 2012, "드라마", 127, 7.8, "미하엘 하네케", "Amour 2012"),
            ("크리멘", 2019, "드라마", 130, 7.4, "아마트 에스칼란테", "New Order"),
            ("Y Tu Mama Tambien", 2001, "드라마", 106, 7.6, "알폰소 쿠아론", "Y Tu Mama Tambien"),
        ],
        "호주": [
            ("매드맥스", 1979, "SF", 88, 6.9, "조지 밀러", "Mad Max 1979"),
            ("피아노", 1993, "드라마", 121, 7.5, "제인 캠피온", "The Piano 1993"),
            ("물랑 루즈!", 2001, "뮤지컬", 128, 7.6, "바즈 루어만", "Moulin Rouge 2001"),
            ("오스트레일리아", 2008, "드라마", 165, 6.6, "바즈 루어만", "Australia 2008"),
        ],
        "캐나다": [
            ("이터널 선샤인", 2004, "로맨스", 108, 8.3, "미셸 공드리", "Eternal Sunshine of the Spotless Mind"),
            ("아톤먼트", 2007, "로맨스", 123, 7.8, "조 라이트", "Atonement 2007"),
        ],
        "덴마크": [
            ("더 헌트", 2012, "드라마", 115, 8.3, "토마스 빈터베르그", "The Hunt 2012"),
            ("어나더 라운드", 2020, "드라마", 115, 7.7, "토마스 빈터베르그", "Another Round 2020"),
            ("멜랑콜리아", 2011, "SF", 135, 7.1, "라스 폰 트리에", "Melancholia 2011"),
        ],
        "이란": [
            ("씨민과 나데르의 별거", 2011, "드라마", 123, 8.3, "아스가르 파르하디", "A Separation 2011"),
            ("세일즈맨", 2016, "드라마", 125, 7.8, "아스가르 파르하디", "The Salesman 2016"),
            ("어바웃 엘리", 2009, "드라마", 119, 8.0, "아스가르 파르하디", "About Elly 2009"),
        ],
        "아르헨티나": [
            ("비밀 속의 눈들", 2009, "스릴러", 127, 8.2, "후안 호세 캄파넬라", "The Secret in Their Eyes"),
            ("와일드 테일즈", 2014, "코미디", 122, 8.1, "다미안 시프론", "Wild Tales 2014"),
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
                "수상여부": 수상여부생성(영화명),
                "대표리뷰": 대표리뷰생성(장르, 영화명),
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
        "해시태그", "시리즈", "OTT", "예고편URL", "포스터URL", "포스터검색어",
        "수상여부", "대표리뷰"
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


def 스타일적용(다크모드=True):
    bg = "#070b14" if 다크모드 else "#f4f6fb"
    main_text = "#FFFFFF" if 다크모드 else "#111111"
    sub = "#D6DEEA" if 다크모드 else "#374151"
    card_bg = "#111827" if 다크모드 else "#ffffff"
    border = "#243041" if 다크모드 else "#d1d5db"
    sidebar_text = "#111827"
    detail_bg = "#0d1520" if 다크모드 else "#f0f4fa"
    detail_border = "#1e2d42" if 다크모드 else "#c8d0dc"

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
            max-width: 1480px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }}
        h1, h2, h3, h4, h5, h6, p, label, div, span,
        .stMarkdown, .stCaption, [data-testid="stExpander"] * {{
            color: {main_text} !important;
            opacity: 1 !important;
        }}
        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"],
        [data-testid="stMetric"] * {{
            color: #111827 !important;
        }}
        [data-baseweb="input"] input,
        [data-baseweb="select"] *,
        [data-baseweb="textarea"] textarea {{
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
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
            min-height: 430px;
            border-radius: 28px;
            overflow: hidden;
            margin-bottom: 24px;
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
            background: linear-gradient(90deg, rgba(3,7,18,.94) 0%, rgba(3,7,18,.65) 45%, rgba(3,7,18,.20) 100%);
        }}
        .hero-content {{
            position: relative;
            z-index: 2;
            padding: 38px;
            max-width: 760px;
        }}
        .hero-badge {{
            display:inline-block;
            padding:7px 14px;
            border-radius:999px;
            background:rgba(255,255,255,.12);
            color:#fff;
            font-size:.82rem;
            margin-bottom:14px;
        }}
        .hero-title {{
            font-size:2.8rem;
            font-weight:800;
            line-height:1.05;
            margin-bottom:12px;
            color:#fff !important;
        }}
        .hero-meta {{
            font-size:.96rem;
            color:#e5edf7 !important;
            margin-bottom:14px;
        }}
        .hero-desc {{
            font-size:1rem;
            color:#e5edf7 !important;
            line-height:1.7;
            margin-bottom:14px;
        }}
        .chip-row {{
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-bottom:18px;
        }}
        .chip {{
            padding:8px 14px;
            border-radius:999px;
            background:rgba(255,255,255,.09);
            color:#fff !important;
            font-size:.85rem;
            border:1px solid rgba(255,255,255,.10);
        }}
        .hero-stats {{
            display:flex;
            gap:12px;
            flex-wrap:wrap;
        }}
        .hero-stat {{
            min-width:120px;
            padding:14px 16px;
            border-radius:18px;
            background:rgba(255,255,255,.08);
            border:1px solid rgba(255,255,255,.10);
        }}
        .hero-stat-label {{
            color:#d1d5db !important;
            font-size:.78rem;
            margin-bottom:4px;
        }}
        .hero-stat-value {{
            color:#fff !important;
            font-size:1.05rem;
            font-weight:700;
        }}
        .section-title {{
            font-size:1.22rem;
            font-weight:800;
            margin:8px 0 16px 0;
            color:{main_text} !important;
        }}
        .movie-card {{
            border-radius:22px;
            overflow:hidden;
            margin-bottom:8px;
            background:{card_bg};
            border:1px solid {border};
            box-shadow:0 12px 30px rgba(0,0,0,.18);
            transition: transform .15s ease, box-shadow .15s ease;
        }}
        .movie-card:hover {{
            transform: translateY(-3px);
            box-shadow:0 20px 40px rgba(0,0,0,.28);
        }}
        .poster-wrap {{
            position:relative;
            background:#0f172a;
        }}
        .poster-img {{
            width:100%;
            height:300px;
            object-fit:cover;
            display:block;
            background:#0f172a;
        }}
        .poster-top-badges {{
            position:absolute;
            top:10px;
            left:10px;
            right:10px;
            display:flex;
            justify-content:space-between;
            align-items:flex-start;
            z-index:3;
            pointer-events:none;
        }}
        .poster-badge {{
            display:inline-block;
            padding:5px 9px;
            border-radius:999px;
            background:rgba(15,23,42,.80);
            color:#fff !important;
            font-size:.72rem;
            border:1px solid rgba(255,255,255,.12);
        }}
        .card-info {{
            padding:12px 14px 6px 14px;
        }}
        .card-title {{
            font-size:.97rem;
            font-weight:800;
            line-height:1.3;
            color:{main_text} !important;
            margin-bottom:4px;
            min-height:2.5em;
        }}
        .card-meta {{
            font-size:.78rem;
            color:{sub} !important;
            margin-bottom:5px;
            line-height:1.4;
        }}
        .card-summary {{
            font-size:.77rem;
            color:{sub} !important;
            line-height:1.45;
            margin-bottom:6px;
        }}
        /* ── 카드 인라인 상세 패널 ── */
        .card-detail-panel {{
            background:{detail_bg};
            border-top:1px solid {detail_border};
            padding:10px 14px 12px 14px;
            font-size:.75rem;
            color:{sub} !important;
            line-height:1.55;
        }}
        .card-detail-row {{
            display:flex;
            gap:6px;
            margin-bottom:3px;
            flex-wrap:wrap;
        }}
        .card-detail-label {{
            color:#94a3b8 !important;
            min-width:62px;
            flex-shrink:0;
            font-size:.70rem;
        }}
        .card-detail-value {{
            color:{main_text} !important;
            font-size:.73rem;
            flex:1;
        }}
        .card-detail-tags {{
            display:flex;
            flex-wrap:wrap;
            gap:4px;
            margin-top:6px;
        }}
        .card-mini-tag {{
            padding:2px 7px;
            border-radius:999px;
            background:rgba(255,255,255,.06);
            border:1px solid rgba(255,255,255,.09);
            color:{sub} !important;
            font-size:.67rem;
        }}
        .card-ott-tag {{
            padding:2px 7px;
            border-radius:999px;
            background:rgba(59,130,246,.15);
            border:1px solid rgba(59,130,246,.25);
            color:#93c5fd !important;
            font-size:.67rem;
        }}
        .card-stat-row {{
            display:flex;
            gap:8px;
            margin-top:7px;
            margin-bottom:5px;
        }}
        .card-stat-box {{
            flex:1;
            background:rgba(255,255,255,.04);
            border:1px solid rgba(255,255,255,.06);
            border-radius:10px;
            padding:5px 8px;
            text-align:center;
        }}
        .card-stat-lbl {{
            color:#64748b !important;
            font-size:.62rem;
            display:block;
            margin-bottom:1px;
        }}
        .card-stat-val {{
            color:{main_text} !important;
            font-size:.74rem;
            font-weight:700;
        }}
        .small-btn-wrap {{
            margin-top:2px;
            margin-bottom:4px;
        }}
        .rail-card {{
            background:{card_bg};
            border:1px solid {border};
            border-radius:18px;
            padding:14px 16px;
            margin-bottom:12px;
        }}
        .rail-title {{
            font-size:.98rem;
            font-weight:700;
            margin-bottom:5px;
            color:{main_text} !important;
        }}
        .rail-sub {{
            font-size:.84rem;
            color:{sub} !important;
            line-height:1.5;
        }}
        .page-box {{
            padding:12px 14px;
            border-radius:18px;
            border:1px solid {border};
            background:rgba(17,24,39,.65);
            margin-bottom:20px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            <img src='{escape(poster, quote=True)}' class='poster-img' alt='{title} 포스터' loading='lazy'>
            <div class='poster-top-badges'>
                <span class='poster-badge'>{genre}</span>
                <span class='poster-badge'>★ {rating}</span>
            </div>
        </div>
        <div class='card-info'>
            <div class='card-title'>{title}</div>
            <div class='card-meta'>{country} · {year} · {runtime}</div>
            <div class='card-summary'>{one_liner}</div>
        </div>
    </div>
    """


@st.dialog("🎬 영화 상세 정보", width="large")
def 영화팝업(row, tmdb_api_key):
    poster = 포스터주소가져오기(row, tmdb_api_key)
    title = str(row["영화명"])
    country = str(row["국가"])
    genre = str(row["장르"])
    subgenre = str(row["세부장르"])
    year = "-" if pd.isna(row["개봉연도"]) else str(int(row["개봉연도"]))
    runtime = "-" if pd.isna(row["상영시간"]) else f"{int(row['상영시간'])}분"
    rating = "-" if pd.isna(row["평점"]) else f"{float(row['평점']):.1f}"
    director = str(row["감독"])
    cast = str(row["출연진"])
    age_rating = str(row["연령등급"])
    one_liner = str(row["한줄요약"])
    short_desc = str(row["짧은소개"])
    synopsis = str(row["줄거리"])
    awards = str(row["수상여부"])
    series = str(row["시리즈"])
    review = str(row["대표리뷰"])
    ott_list = 태그분리(row["OTT"])
    emotion_tags = 태그분리(row["감정태그"])
    situation_tags = 태그분리(row["상황태그"])
    feature_tags = 태그분리(row["특징태그"])
    hashtags = 태그분리(row["해시태그"])
    audience = 숫자표시(row["관객수"])
    gross = 금액표시(row["글로벌흥행액"])
    trailer_url = str(row["예고편URL"])

    # 팝업 내부 스타일
    st.markdown("""
    <style>
    [data-testid="stDialog"] * { color: #111 !important; }
    [data-testid="stDialog"] .popup-poster { border-radius:16px; overflow:hidden; }
    [data-testid="stDialog"] .popup-tag {
        display:inline-block; padding:3px 10px; border-radius:999px;
        background:#e8f0fe; color:#1a56db !important; font-size:.78rem;
        margin:2px; border:1px solid #c7d7fc;
    }
    [data-testid="stDialog"] .popup-ott-tag {
        display:inline-block; padding:3px 10px; border-radius:999px;
        background:#fef3c7; color:#92400e !important; font-size:.78rem;
        margin:2px; border:1px solid #fde68a;
    }
    [data-testid="stDialog"] .popup-emotion-tag {
        display:inline-block; padding:3px 10px; border-radius:999px;
        background:#f0fdf4; color:#166534 !important; font-size:.78rem;
        margin:2px; border:1px solid #bbf7d0;
    }
    [data-testid="stDialog"] .popup-stat-box {
        background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px;
        padding:10px 14px; text-align:center;
    }
    [data-testid="stDialog"] .popup-stat-lbl {
        color:#64748b !important; font-size:.72rem; display:block; margin-bottom:2px;
    }
    [data-testid="stDialog"] .popup-stat-val {
        color:#0f172a !important; font-size:1rem; font-weight:700;
    }
    [data-testid="stDialog"] .popup-section-title {
        font-size:.78rem; color:#64748b !important; font-weight:600;
        text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; margin-top:12px;
    }
    [data-testid="stDialog"] .popup-synopsis {
        background:#f8fafc; border-left:3px solid #3b82f6;
        padding:10px 14px; border-radius:0 10px 10px 0;
        font-size:.88rem; color:#1e293b !important; line-height:1.7;
    }
    [data-testid="stDialog"] .popup-review {
        background:#fffbeb; border:1px solid #fde68a;
        padding:10px 14px; border-radius:12px;
        font-size:.85rem; color:#78350f !important;
        font-style:italic; line-height:1.6;
    }
    [data-testid="stDialog"] .popup-info-row {
        display:flex; gap:6px; align-items:flex-start; margin-bottom:6px;
    }
    [data-testid="stDialog"] .popup-info-label {
        color:#64748b !important; font-size:.78rem; min-width:60px; flex-shrink:0; padding-top:1px;
    }
    [data-testid="stDialog"] .popup-info-value {
        color:#1e293b !important; font-size:.85rem; flex:1; line-height:1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    col_poster, col_info = st.columns([1, 1.8])

    with col_poster:
        st.image(poster, use_container_width=True)
        st.link_button("▶ 예고편 검색", trailer_url, use_container_width=True)

        # 찜/본 영화 버튼
        b1, b2 = st.columns(2)
        with b1:
            in_wish = title in st.session_state["wishlist"]
            if st.button("🤍 찜" if not in_wish else "❤️ 찜됨", use_container_width=True, key=f"pop_wish_{title}"):
                리스트토글("wishlist", title)
                st.rerun()
        with b2:
            in_watched = title in st.session_state["watched"]
            if st.button("✅ 봤어요" if not in_watched else "✅ 봄", use_container_width=True, key=f"pop_watched_{title}"):
                리스트토글("watched", title)
                st.rerun()

    with col_info:
        # 제목 & 기본 메타
        st.markdown(f"### {title}")
        st.markdown(f"**{country}** · {year} · {runtime} · {age_rating} · ★ **{rating}**")

        if series.strip():
            st.markdown(f"📺 시리즈: **{series}**")

        # 한줄 요약
        st.markdown(f"_{one_liner}_")
        st.divider()

        # 통계 박스
        s1, s2, s3 = st.columns(3)
        s1.markdown(f"<div class='popup-stat-box'><span class='popup-stat-lbl'>평점</span><span class='popup-stat-val'>★ {rating}</span></div>", unsafe_allow_html=True)
        s2.markdown(f"<div class='popup-stat-box'><span class='popup-stat-lbl'>관객수</span><span class='popup-stat-val'>{audience}</span></div>", unsafe_allow_html=True)
        s3.markdown(f"<div class='popup-stat-box'><span class='popup-stat-lbl'>흥행액</span><span class='popup-stat-val'>{gross}</span></div>", unsafe_allow_html=True)

        # 기본 정보
        st.markdown("<div class='popup-section-title'>기본 정보</div>", unsafe_allow_html=True)
        info_rows = [
            ("장르", f"{genre} / {subgenre}"),
            ("감독", director),
            ("출연진", cast),
            ("수상", awards),
        ]
        for lbl, val in info_rows:
            st.markdown(f"<div class='popup-info-row'><span class='popup-info-label'>{lbl}</span><span class='popup-info-value'>{escape(val)}</span></div>", unsafe_allow_html=True)

        # 짧은 소개
        st.markdown("<div class='popup-section-title'>소개</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='popup-synopsis'>{escape(short_desc)}</div>", unsafe_allow_html=True)

        # 줄거리
        st.markdown("<div class='popup-section-title'>줄거리</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='popup-synopsis'>{escape(synopsis)}</div>", unsafe_allow_html=True)

        # 태그들
        st.markdown("<div class='popup-section-title'>감정 · 상황 태그</div>", unsafe_allow_html=True)
        tag_html = "".join([f"<span class='popup-emotion-tag'>{escape(t)}</span>" for t in emotion_tags])
        tag_html += "".join([f"<span class='popup-tag'>{escape(t)}</span>" for t in situation_tags])
        tag_html += "".join([f"<span class='popup-tag'>{escape(t)}</span>" for t in feature_tags])
        st.markdown(tag_html, unsafe_allow_html=True)

        # OTT
        st.markdown("<div class='popup-section-title'>OTT 플랫폼</div>", unsafe_allow_html=True)
        ott_html = "".join([f"<span class='popup-ott-tag'>{escape(o)}</span>" for o in ott_list])
        st.markdown(ott_html if ott_html else "-", unsafe_allow_html=True)

        # 해시태그
        st.markdown("<div class='popup-section-title'>해시태그</div>", unsafe_allow_html=True)
        hash_html = "".join([f"<span class='popup-tag'>#{escape(h)}</span>" for h in hashtags])
        st.markdown(hash_html if hash_html else "-", unsafe_allow_html=True)

        # 대표 리뷰
        st.markdown("<div class='popup-section-title'>대표 리뷰</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='popup-review'>💬 {escape(review)}</div>", unsafe_allow_html=True)

        # 내 평가
        st.markdown("<div class='popup-section-title'>내 평가</div>", unsafe_allow_html=True)
        user_score = st.slider("내 평점", 0.0, 10.0,
                               float(st.session_state["user_rating"].get(title, 8.0)),
                               0.5, key=f"pop_score_{title}")
        user_review_text = st.text_area("한 줄 리뷰", value=st.session_state["user_review"].get(title, ""),
                                        height=70, key=f"pop_review_{title}")
        if st.button("💾 내 평가 저장", use_container_width=True, key=f"pop_save_{title}"):
            st.session_state["user_rating"][title] = user_score
            st.session_state["user_review"][title] = user_review_text
            st.success("저장되었습니다!")


def 카드UI(row, tmdb_api_key):
    st.markdown(카드HTML생성(row, tmdb_api_key), unsafe_allow_html=True)
    st.markdown("<div class='small-btn-wrap'>", unsafe_allow_html=True)
    if st.button("상세보기", key=f"popup_btn_{row['영화명']}", use_container_width=True):
        영화팝업(row, tmdb_api_key)
    st.markdown("</div>", unsafe_allow_html=True)


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
        <img src='{escape(poster, quote=True)}' class='hero-bg' alt='{title} 포스터'>
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

    대표영화 = filtered.iloc[0]
    st.markdown(히어로HTML생성(대표영화, tmdb_api_key), unsafe_allow_html=True)

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

    st.markdown("<div class='section-title'>지금 많이 보는 영화</div>", unsafe_allow_html=True)
    cols_per_row = 4
    for start in range(0, len(page_df), cols_per_row):
        chunk = page_df.iloc[start:start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                카드UI(row, tmdb_api_key)

    st.markdown("<div class='section-title'>추천 레일</div>", unsafe_allow_html=True)
    rec1, rec2, rec3 = st.columns(3)
    with rec1:
        st.markdown("**한국 흥행작 모음**")
        for _, rec in df[df["국가"] == "한국"].sort_values("관객수", ascending=False).head(6).iterrows():
            st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['장르']))} · 평점 {rec['평점']}</div></div>", unsafe_allow_html=True)
    with rec2:
        st.markdown("**감성 로맨스 모음**")
        for _, rec in df[df["장르"] == "로맨스"].sort_values("평점", ascending=False).head(6).iterrows():
            st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['국가']))} · 평점 {rec['평점']}</div></div>", unsafe_allow_html=True)
    with rec3:
        st.markdown("**몰입감 높은 스릴러**")
        for _, rec in df[df["장르"] == "스릴러"].sort_values("평점", ascending=False).head(6).iterrows():
            st.markdown(f"<div class='rail-card'><div class='rail-title'>{escape(str(rec['영화명']))}</div><div class='rail-sub'>{escape(str(rec['국가']))} · 평점 {rec['평점']}</div></div>", unsafe_allow_html=True)

    with st.expander("현재 검색 데이터 표 보기"):
        st.dataframe(page_df[표시컬럼], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    메인()
