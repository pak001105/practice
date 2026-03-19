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
    데이터 = [
        # 미국
        {"영화명":"인터스텔라","개봉연도":2014,"국가":"미국","장르":"SF","상영시간":169,"관객수":10300000,"글로벌흥행액":731000000,"평점":8.7,"감독":"크리스토퍼 놀란","감정태그":"몰입,경이로움,울림","상황태그":"혼자,주말밤,생각하고싶을때","특징태그":"우주,철학,명작","해시태그":"SF,우주,명작,몰입","포스터URL":"","포스터검색어":"Interstellar"},
        {"영화명":"다크 나이트","개봉연도":2008,"국가":"미국","장르":"액션","상영시간":152,"관객수":8500000,"글로벌흥행액":1006000000,"평점":9.0,"감독":"크리스토퍼 놀란","감정태그":"긴장,몰입,전율","상황태그":"혼자,친구와,주말","특징태그":"히어로,범죄,명작","해시태그":"액션,히어로,명작,전율","포스터URL":"","포스터검색어":"The Dark Knight"},
        {"영화명":"라라랜드","개봉연도":2016,"국가":"미국","장르":"로맨스","상영시간":128,"관객수":3600000,"글로벌흥행액":471000000,"평점":8.0,"감독":"데이미언 셔젤","감정태그":"설렘,감성,여운","상황태그":"연인과,밤,감성적인날","특징태그":"음악,사랑,뮤지컬","해시태그":"로맨스,감성,뮤지컬,여운","포스터URL":"","포스터검색어":"La La Land"},
        {"영화명":"인사이드 아웃","개봉연도":2015,"국가":"미국","장르":"애니메이션","상영시간":95,"관객수":4970000,"글로벌흥행액":857000000,"평점":8.1,"감독":"피트 닥터","감정태그":"힐링,따뜻함,감동","상황태그":"가족과,주말오후,가볍게","특징태그":"성장,가족,감정","해시태그":"애니메이션,힐링,가족,감동","포스터URL":"","포스터검색어":"Inside Out"},
        {"영화명":"쇼생크 탈출","개봉연도":1994,"국가":"미국","장르":"드라마","상영시간":142,"관객수":1200000,"글로벌흥행액":29000000,"평점":9.3,"감독":"프랭크 다라본트","감정태그":"희망,감동,울림","상황태그":"혼자,깊게보고싶을때,명작감상","특징태그":"명작,감옥,인생","해시태그":"드라마,명작,희망,인생","포스터URL":"","포스터검색어":"The Shawshank Redemption"},
        {"영화명":"겟 아웃","개봉연도":2017,"국가":"미국","장르":"스릴러","상영시간":104,"관객수":2100000,"글로벌흥행액":255000000,"평점":7.7,"감독":"조던 필","감정태그":"불안,긴장,충격","상황태그":"혼자,밤,몰입하고싶을때","특징태그":"반전,풍자,심리","해시태그":"스릴러,반전,심리,충격","포스터URL":"","포스터검색어":"Get Out"},

        # 한국
        {"영화명":"기생충","개봉연도":2019,"국가":"한국","장르":"스릴러","상영시간":132,"관객수":10317247,"글로벌흥행액":262000000,"평점":8.5,"감독":"봉준호","감정태그":"긴장,충격,몰입","상황태그":"혼자,친구와,주말밤","특징태그":"사회풍자,반전,수상작","해시태그":"스릴러,봉준호,반전,수상작","포스터URL":"","포스터검색어":"Parasite"},
        {"영화명":"극한직업","개봉연도":2019,"국가":"한국","장르":"코미디","상영시간":111,"관객수":16266480,"글로벌흥행액":120000000,"평점":7.1,"감독":"이병헌","감정태그":"유쾌함,웃김,가벼움","상황태그":"친구와,가족과,스트레스풀고싶을때","특징태그":"형사,코믹,흥행작","해시태그":"코미디,한국영화,흥행작,웃김","포스터URL":"","포스터검색어":"Extreme Job"},
        {"영화명":"올드보이","개봉연도":2003,"국가":"한국","장르":"액션","상영시간":120,"관객수":3260000,"글로벌흥행액":15000000,"평점":8.4,"감독":"박찬욱","감정태그":"전율,충격,강렬함","상황태그":"혼자,몰입,강한영화보고싶을때","특징태그":"복수,반전,명작","해시태그":"액션,복수,반전,박찬욱","포스터URL":"","포스터검색어":"Oldboy"},
        {"영화명":"8월의 크리스마스","개봉연도":1998,"국가":"한국","장르":"로맨스","상영시간":97,"관객수":500000,"글로벌흥행액":0,"평점":8.3,"감독":"허진호","감정태그":"잔잔함,여운,슬픔","상황태그":"혼자,감성적인날,비오는날","특징태그":"멜로,감성,명작","해시태그":"로맨스,감성,여운,한국영화","포스터URL":"","포스터검색어":"Christmas in August"},
        {"영화명":"국제시장","개봉연도":2014,"국가":"한국","장르":"드라마","상영시간":126,"관객수":14257115,"글로벌흥행액":99000000,"평점":7.8,"감독":"윤제균","감정태그":"감동,울림,뭉클함","상황태그":"가족과,명절,감동받고싶을때","특징태그":"가족,시대극,실화감성","해시태그":"드라마,가족,감동,시대극","포스터URL":"","포스터검색어":"Ode to My Father"},
        {"영화명":"마당을 나온 암탉","개봉연도":2011,"국가":"한국","장르":"애니메이션","상영시간":93,"관객수":2200000,"글로벌흥행액":0,"평점":7.3,"감독":"오성윤","감정태그":"따뜻함,감동,희망","상황태그":"가족과,아이와함께,주말오후","특징태그":"가족,성장,애니메이션","해시태그":"애니메이션,가족,감동,한국","포스터URL":"","포스터검색어":"Leafie A Hen into the Wild"},

        # 영국
        {"영화명":"킹스 스피치","개봉연도":2010,"국가":"영국","장르":"드라마","상영시간":118,"관객수":1000000,"글로벌흥행액":427000000,"평점":8.0,"감독":"톰 후퍼","감정태그":"감동,희망,울림","상황태그":"혼자,조용한밤,좋은영화보고싶을때","특징태그":"실화,수상작,왕실","해시태그":"드라마,실화,수상작,영국","포스터URL":"","포스터검색어":"The King's Speech"},
        {"영화명":"노팅 힐","개봉연도":1999,"국가":"영국","장르":"로맨스","상영시간":124,"관객수":800000,"글로벌흥행액":364000000,"평점":7.2,"감독":"로저 미첼","감정태그":"설렘,따뜻함,기분좋음","상황태그":"연인과,주말밤,편하게","특징태그":"로맨틱코미디,명작,영국감성","해시태그":"로맨스,영국,감성,설렘","포스터URL":"","포스터검색어":"Notting Hill"},
        {"영화명":"007 스카이폴","개봉연도":2012,"국가":"영국","장르":"액션","상영시간":143,"관객수":1300000,"글로벌흥행액":1109000000,"평점":7.8,"감독":"샘 멘데스","감정태그":"전율,긴장,쾌감","상황태그":"친구와,주말,액션보고싶을때","특징태그":"첩보,시리즈,흥행작","해시태그":"액션,첩보,007,영국","포스터URL":"","포스터검색어":"Skyfall"},
        {"영화명":"패딩턴 2","개봉연도":2017,"국가":"영국","장르":"애니메이션","상영시간":103,"관객수":300000,"글로벌흥행액":228000000,"평점":7.8,"감독":"폴 킹","감정태그":"따뜻함,힐링,유쾌함","상황태그":"가족과,주말오후,가볍게","특징태그":"가족,모험,영국감성","해시태그":"애니메이션,힐링,가족,영국","포스터URL":"","포스터검색어":"Paddington 2"},
        {"영화명":"28일 후","개봉연도":2002,"국가":"영국","장르":"스릴러","상영시간":113,"관객수":200000,"글로벌흥행액":85000000,"평점":7.5,"감독":"대니 보일","감정태그":"불안,긴장,공포","상황태그":"밤,혼자,몰입하고싶을때","특징태그":"좀비,재난,서스펜스","해시태그":"스릴러,좀비,재난,영국","포스터URL":"","포스터검색어":"28 Days Later"},
        {"영화명":"브리짓 존스의 일기","개봉연도":2001,"국가":"영국","장르":"코미디","상영시간":97,"관객수":500000,"글로벌흥행액":282000000,"평점":6.8,"감독":"샤론 맥과이어","감정태그":"유쾌함,편안함,설렘","상황태그":"혼자,친구와,가볍게","특징태그":"로코,일상,영국감성","해시태그":"코미디,로코,영국,가볍게","포스터URL":"","포스터검색어":"Bridget Jones's Diary"},

        # 스페인
        {"영화명":"판의 미로","개봉연도":2006,"국가":"스페인","장르":"판타지","상영시간":118,"관객수":300000,"글로벌흥행액":83000000,"평점":8.2,"감독":"기예르모 델 토로","감정태그":"어두움,몰입,여운","상황태그":"혼자,밤,분위기있는영화","특징태그":"판타지,전쟁,명작","해시태그":"판타지,전쟁,명작,스페인","포스터URL":"","포스터검색어":"Pan's Labyrinth"},
        {"영화명":"더 임파서블","개봉연도":2012,"국가":"스페인","장르":"드라마","상영시간":114,"관객수":400000,"글로벌흥행액":198000000,"평점":7.6,"감독":"후안 안토니오 바요나","감정태그":"긴장,감동,절박함","상황태그":"가족과,몰입,실화좋아할때","특징태그":"실화,재난,가족","해시태그":"드라마,실화,재난,스페인","포스터URL":"","포스터검색어":"The Impossible"},
        {"영화명":"줄리아의 눈","개봉연도":2010,"국가":"스페인","장르":"스릴러","상영시간":118,"관객수":100000,"글로벌흥행액":0,"평점":6.7,"감독":"기옘 모랄레스","감정태그":"불안,긴장,서늘함","상황태그":"밤,혼자,스릴원할때","특징태그":"미스터리,심리,반전","해시태그":"스릴러,심리,반전,스페인","포스터URL":"","포스터검색어":"Julia's Eyes"},
        {"영화명":"오픈 유어 아이즈","개봉연도":1997,"국가":"스페인","장르":"SF","상영시간":119,"관객수":50000,"글로벌흥행액":0,"평점":7.7,"감독":"알레한드로 아메나바르","감정태그":"혼란,몰입,충격","상황태그":"혼자,생각하고싶을때,밤","특징태그":"반전,심리,SF","해시태그":"SF,반전,심리,스페인","포스터URL":"","포스터검색어":"Open Your Eyes"},
        {"영화명":"토렌테","개봉연도":1998,"국가":"스페인","장르":"코미디","상영시간":97,"관객수":50000,"글로벌흥행액":0,"평점":6.8,"감독":"산티아고 세구라","감정태그":"유쾌함,병맛,가벼움","상황태그":"친구와,가볍게,웃고싶을때","특징태그":"블랙코미디,컬트,시리즈","해시태그":"코미디,컬트,스페인,웃김","포스터URL":"","포스터검색어":"Torrente"},
        {"영화명":"타데오 존스","개봉연도":2012,"국가":"스페인","장르":"애니메이션","상영시간":92,"관객수":100000,"글로벌흥행액":45000000,"평점":6.1,"감독":"엔리케 가토","감정태그":"모험,유쾌함,편안함","상황태그":"가족과,아이와함께,주말","특징태그":"모험,가족,애니메이션","해시태그":"애니메이션,가족,모험,스페인","포스터URL":"","포스터검색어":"Tad The Lost Explorer"},

        # 인도
        {"영화명":"세 얼간이","개봉연도":2009,"국가":"인도","장르":"코미디","상영시간":170,"관객수":4500000,"글로벌흥행액":90000000,"평점":8.4,"감독":"라지쿠마르 히라니","감정태그":"유쾌함,감동,희망","상황태그":"친구와,가족과,기분전환","특징태그":"청춘,우정,명작","해시태그":"코미디,청춘,우정,인도","포스터URL":"","포스터검색어":"3 Idiots"},
        {"영화명":"당갈","개봉연도":2016,"국가":"인도","장르":"드라마","상영시간":161,"관객수":3000000,"글로벌흥행액":311000000,"평점":8.3,"감독":"니테시 티와리","감정태그":"열정,감동,뭉클함","상황태그":"가족과,동기부여받고싶을때,주말","특징태그":"실화,스포츠,가족","해시태그":"드라마,실화,스포츠,인도","포스터URL":"","포스터검색어":"Dangal"},
        {"영화명":"바후발리: 더 비기닝","개봉연도":2015,"국가":"인도","장르":"액션","상영시간":159,"관객수":2000000,"글로벌흥행액":100000000,"평점":8.0,"감독":"S. S. 라자몰리","감정태그":"웅장함,전율,쾌감","상황태그":"친구와,주말,대작보고싶을때","특징태그":"전쟁,판타지,대서사","해시태그":"액션,대서사,인도,전쟁","포스터URL":"","포스터검색어":"Baahubali The Beginning"},
        {"영화명":"런치박스","개봉연도":2013,"국가":"인도","장르":"로맨스","상영시간":104,"관객수":300000,"글로벌흥행액":23000000,"평점":7.8,"감독":"리테쉬 바트라","감정태그":"잔잔함,따뜻함,여운","상황태그":"혼자,감성적인날,조용한밤","특징태그":"편지,일상,감성","해시태그":"로맨스,감성,여운,인도","포스터URL":"","포스터검색어":"The Lunchbox"},
        {"영화명":"안다둔","개봉연도":2018,"국가":"인도","장르":"스릴러","상영시간":139,"관객수":800000,"글로벌흥행액":45000000,"평점":8.2,"감독":"스리람 라가반","감정태그":"긴장,몰입,충격","상황태그":"혼자,밤,반전좋아할때","특징태그":"반전,범죄,블랙코미디","해시태그":"스릴러,반전,범죄,인도","포스터URL":"","포스터검색어":"Andhadhun"},
        {"영화명":"하누만","개봉연도":2024,"국가":"인도","장르":"판타지","상영시간":158,"관객수":500000,"글로벌흥행액":35000000,"평점":7.8,"감독":"프라샨트 바르마","감정태그":"쾌감,전율,웅장함","상황태그":"주말,친구와,대작좋아할때","특징태그":"히어로,신화,판타지","해시태그":"판타지,히어로,신화,인도","포스터URL":"","포스터검색어":"Hanu Man"},

        # 일본
        {"영화명":"센과 치히로의 행방불명","개봉연도":2001,"국가":"일본","장르":"애니메이션","상영시간":125,"관객수":2160000,"글로벌흥행액":395000000,"평점":8.6,"감독":"미야자키 하야오","감정태그":"신비로움,감동,몰입","상황태그":"가족과,혼자,명작보고싶을때","특징태그":"판타지,성장,명작","해시태그":"애니메이션,판타지,명작,일본","포스터URL":"","포스터검색어":"Spirited Away"},
        {"영화명":"너의 이름은","개봉연도":2016,"국가":"일본","장르":"로맨스","상영시간":106,"관객수":3710000,"글로벌흥행액":382000000,"평점":8.4,"감독":"신카이 마코토","감정태그":"설렘,감성,여운","상황태그":"연인과,혼자,밤","특징태그":"애니메이션,판타지,청춘","해시태그":"로맨스,애니메이션,청춘,일본","포스터URL":"","포스터검색어":"Your Name"},
        {"영화명":"고질라 마이너스 원","개봉연도":2023,"국가":"일본","장르":"액션","상영시간":124,"관객수":600000,"글로벌흥행액":115000000,"평점":8.0,"감독":"야마자키 타카시","감정태그":"긴장,웅장함,몰입","상황태그":"주말,친구와,대작보고싶을때","특징태그":"괴수,재난,전쟁","해시태그":"액션,괴수,재난,일본","포스터URL":"","포스터검색어":"Godzilla Minus One"},
        {"영화명":"링","개봉연도":1998,"국가":"일본","장르":"스릴러","상영시간":96,"관객수":200000,"글로벌흥행액":19000000,"평점":7.2,"감독":"나카타 히데오","감정태그":"공포,불안,서늘함","상황태그":"밤,혼자,공포좋아할때","특징태그":"공포,저주,심리","해시태그":"스릴러,공포,저주,일본","포스터URL":"","포스터검색어":"Ringu"},
        {"영화명":"어느 가족","개봉연도":2018,"국가":"일본","장르":"드라마","상영시간":121,"관객수":300000,"글로벌흥행액":75000000,"평점":7.9,"감독":"고레에다 히로카즈","감정태그":"잔잔함,여운,먹먹함","상황태그":"혼자,조용한밤,생각하고싶을때","특징태그":"가족,사회,수상작","해시태그":"드라마,가족,수상작,일본","포스터URL":"","포스터검색어":"Shoplifters"},
        {"영화명":"용과 주근깨 공주","개봉연도":2021,"국가":"일본","장르":"판타지","상영시간":121,"관객수":200000,"글로벌흥행액":65000000,"평점":7.1,"감독":"호소다 마모루","감정태그":"감성,몰입,희망","상황태그":"혼자,주말,비주얼좋아할때","특징태그":"가상세계,음악,성장","해시태그":"판타지,성장,음악,일본","포스터URL":"","포스터검색어":"Belle 2021"},

        # 중국
        {"영화명":"와호장룡","개봉연도":2000,"국가":"중국","장르":"액션","상영시간":120,"관객수":400000,"글로벌흥행액":213000000,"평점":7.9,"감독":"이안","감정태그":"아름다움,몰입,전율","상황태그":"혼자,주말밤,명작감상","특징태그":"무협,명작,수상작","해시태그":"액션,무협,명작,중국","포스터URL":"","포스터검색어":"Crouching Tiger Hidden Dragon"},
        {"영화명":"영웅","개봉연도":2002,"국가":"중국","장르":"드라마","상영시간":99,"관객수":300000,"글로벌흥행액":177000000,"평점":7.9,"감독":"장이머우","감정태그":"웅장함,비장함,몰입","상황태그":"혼자,영상미좋아할때,주말","특징태그":"무협,미장센,역사","해시태그":"드라마,무협,영상미,중국","포스터URL":"","포스터검색어":"Hero 2002"},
        {"영화명":"유랑지구","개봉연도":2019,"국가":"중국","장르":"SF","상영시간":125,"관객수":1000000,"글로벌흥행액":700000000,"평점":6.0,"감독":"궈판","감정태그":"웅장함,긴장,몰입","상황태그":"친구와,주말,대작좋아할때","특징태그":"우주,재난,SF","해시태그":"SF,재난,우주,중국","포스터URL":"","포스터검색어":"The Wandering Earth"},
        {"영화명":"안녕 리","개봉연도":2021,"국가":"중국","장르":"코미디","상영시간":128,"관객수":800000,"글로벌흥행액":820000000,"평점":7.7,"감독":"자 링","감정태그":"유쾌함,감동,뭉클함","상황태그":"가족과,친구와,편하게","특징태그":"타임슬립,가족,코미디","해시태그":"코미디,가족,감동,중국","포스터URL":"","포스터검색어":"Hi Mom 2021"},
        {"영화명":"소시대","개봉연도":2013,"국가":"중국","장르":"로맨스","상영시간":116,"관객수":200000,"글로벌흥행액":79000000,"평점":5.0,"감독":"궈징밍","감정태그":"화려함,가벼움,설렘","상황태그":"친구와,가볍게,트렌디한영화보고싶을때","특징태그":"청춘,도시,패션","해시태그":"로맨스,청춘,도시,중국","포스터URL":"","포스터검색어":"Tiny Times"},
        {"영화명":"장진호","개봉연도":2021,"국가":"중국","장르":"스릴러","상영시간":176,"관객수":500000,"글로벌흥행액":913000000,"평점":5.5,"감독":"천카이거 외","감정태그":"긴장,비장함,압도감","상황태그":"주말,대작좋아할때,혼자","특징태그":"전쟁,실화감성,대작","해시태그":"스릴러,전쟁,대작,중국","포스터URL":"","포스터검색어":"The Battle at Lake Changjin"},

        # 대만
        {"영화명":"말할 수 없는 비밀","개봉연도":2007,"국가":"대만","장르":"로맨스","상영시간":101,"관객수":1600000,"글로벌흥행액":14000000,"평점":7.5,"감독":"주걸륜","감정태그":"설렘,감성,여운","상황태그":"연인과,혼자,감성적인날","특징태그":"음악,학원물,판타지","해시태그":"로맨스,음악,감성,대만","포스터URL":"","포스터검색어":"Secret 2007"},
        {"영화명":"그 시절, 우리가 좋아했던 소녀","개봉연도":2011,"국가":"대만","장르":"드라마","상영시간":109,"관객수":500000,"글로벌흥행액":21000000,"평점":7.6,"감독":"구파도","감정태그":"청춘,그리움,설렘","상황태그":"혼자,추억에잠길때,밤","특징태그":"청춘,첫사랑,학원","해시태그":"드라마,청춘,첫사랑,대만","포스터URL":"","포스터검색어":"You Are the Apple of My Eye"},
        {"영화명":"카페 6","개봉연도":2016,"국가":"대만","장르":"코미디","상영시간":103,"관객수":100000,"글로벌흥행액":0,"평점":6.4,"감독":"오자운","감정태그":"청량함,가벼움,설렘","상황태그":"친구와,가볍게,주말오후","특징태그":"청춘,캠퍼스,감성","해시태그":"코미디,청춘,감성,대만","포스터URL":"","포스터검색어":"At Cafe 6"},
        {"영화명":"더 새드니스","개봉연도":2021,"국가":"대만","장르":"스릴러","상영시간":99,"관객수":50000,"글로벌흥행액":0,"평점":6.4,"감독":"롭 자바즈","감정태그":"공포,불쾌함,긴장","상황태그":"밤,혼자,강한자극원할때","특징태그":"고어,바이러스,극한","해시태그":"스릴러,공포,고어,대만","포스터URL":"","포스터검색어":"The Sadness"},
        {"영화명":"실크","개봉연도":2006,"국가":"대만","장르":"판타지","상영시간":108,"관객수":50000,"글로벌흥행액":0,"평점":6.4,"감독":"수 차오빈","감정태그":"서늘함,신비로움,몰입","상황태그":"밤,혼자,분위기있는영화","특징태그":"유령,초자연,미스터리","해시태그":"판타지,미스터리,유령,대만","포스터URL":"","포스터검색어":"Silk 2006"},
        {"영화명":"청설","개봉연도":2009,"국가":"대만","장르":"애니메이션","상영시간":109,"관객수":300000,"글로벌흥행액":0,"평점":7.5,"감독":"정펀펀","감정태그":"따뜻함,잔잔함,설렘","상황태그":"연인과,혼자,조용한날","특징태그":"청춘,로맨스,감성","해시태그":"애니메이션,청춘,감성,대만","포스터URL":"","포스터검색어":"Hear Me 2009"},
    ]

    df = pd.DataFrame(데이터)
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
