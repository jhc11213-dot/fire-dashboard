import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date

# 기본 세팅
st.set_page_config(page_title="2027 소방 컨트롤 타워", layout="centered")

# --- 🎨 둥글둥글한 폰트(주아체) & 아주 연한 크림색 배경 세팅 ---
page_bg_css = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
html, body, [class*="css"], div, p, span, label, h1, h2, h3, h4, h5, h6 {
    font-family: 'Jua', sans-serif !important;
}
.stApp { background-color: #FFF8E7; }
.main .block-container {
    background-color: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    padding-top: 2rem;
    padding-bottom: 2rem;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
}
html, body, p, div, span, label { color: #333333 !important; }
</style>
'''
st.markdown(page_bg_css, unsafe_allow_html=True)

# --- 데이터 로드 함수 ---
RUN_FILE = "fire_data.csv"
GYM_FILE = "gym_data.csv"
STUDY_FILE = "study_state.json"
MOCK_FILE = "mock_data.csv" # 모의고사 저장용 파일 추가

def load_run_data():
    if os.path.exists(RUN_FILE): return pd.read_csv(RUN_FILE)
    return pd.DataFrame(columns=["날짜", "근무", "컨디션", "체중", "VO2Max", "장비", "타겟", "평균심박", "최대심박", "메모"])

def load_gym_data():
    if os.path.exists(GYM_FILE): return pd.read_csv(GYM_FILE)
    return pd.DataFrame(columns=["날짜", "악력", "좌전굴", "왕오달", "제멀", "배근력", "메모"])

def load_mock_data():
    if os.path.exists(MOCK_FILE): return pd.read_csv(MOCK_FILE)
    return pd.DataFrame(columns=["날짜", "과목", "회차", "점수", "오답노트"])

# 공부 데이터(JSON) 로드
def load_study_data():
    if os.path.exists(STUDY_FILE):
        with open(STUDY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "fire_theory": 0, "fire_special": [], 
        "fire_review": {
            "기초이론": 0, "연소이론": 0, "화재이론": 0, "소화이론": 0, "건축방재 및 피난": 0, 
            "위험물 및 특수가연물": 0, "소방시설": 0, "소방행정 및 조직": 0, "소방기능": 0, "재난관리론": 0
        },
        "fire_prob": 0,
        "em_theory": 0, "em_review": 0, "em_prob": 0
    }

def save_study_data(data):
    with open(STUDY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 🌟 상단 대시보드 ---
st.markdown("<h1 style='text-align: center; font-size: 38px; color: #FF4B4B;'>🔥 2027 소방 컨트롤 타워</h1>", unsafe_allow_html=True)
d_day = (date(2027, 3, 6) - date.today()).days
df_run = load_run_data()
last_weight = df_run['체중'].iloc[-1] if not df_run.empty else 75.0
last_vo2 = df_run['VO2Max'].iloc[-1] if not df_run.empty else 46.0

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric(label="소방 필기 시험", value=f"D-{d_day}")
col_m2.metric(label="최근 체중", value=f"{last_weight} kg")
col_m3.metric(label="가민 VO2 Max", value=f"{last_vo2}")
st.write("---")

# --- 탭 구성 ---
tab1, tab2, tab3, tab4 = st.tabs(["📚 필기 진도", "🏃‍♂️ 러닝 기록", "🏋️‍♂️ 체력학원 기록", "📋 피드백"])

# ==========================================
# TAB 1: 필기 진도
# ==========================================
with tab1:
    study_state = load_study_data()
    
    st.markdown("<h2 style='color: #E74C3C;'>🚒 소방학개론</h2>", unsafe_allow_html=True)
    
    # 1. 이론 강의
    st.markdown("#### 📍 1단계: 이론 강의")
    study_state["fire_theory"] = st.slider("메인 이론 강의 (총 107강)", 0, 107, study_state["fire_theory"])
    st.progress(study_state["fire_theory"] / 107.0)
    
    with st.expander("➕ 특강/서브 강의 추가하기"):
        new_sp_name = st.text_input("특강 이름 (예: 관계법규 특강)")
        new_sp_total = st.number_input("총 강의 수", min_value=1, value=10)
        if st.button("특강 등록"):
            if new_sp_name:
                study_state["fire_special"].append({"name": new_sp_name, "total": new_sp_total, "completed": 0})
                save_study_data(study_state)
                st.rerun()
                
    for i, sp in enumerate(study_state["fire_special"]):
        sp["completed"] = st.number_input(f"📺 {sp['name']} (총 {sp['total']}강)", 0, sp["total"], sp["completed"], key=f"sp_{i}")
        st.progress(sp["completed"] / sp["total"])

    st.write("---")
    
    # 2. 복습 파트
    st.markdown("#### 📍 2단계: 단원별 복습 (회독)")
    c_rev1, c_rev2 = st.columns(2)
    chapters = list(study_state["fire_review"].keys())
    
    for i, chap in enumerate(chapters):
        if i % 2 == 0:
            study_state["fire_review"][chap] = c_rev1.number_input(f"📖 {chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
        else:
            study_state["fire_review"][chap] = c_rev2.number_input(f"📖 {chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
            
    total_fire_review = min(study_state["fire_review"].values())
    st.success(f"🔥 소방학개론 전체 **{total_fire_review}회독** 달성!")

    st.write("---")

    # 3. 문풀
    st.markdown("#### 📍 3단계: 기출 및 문제풀이")
    study_state["fire_prob"] = st.number_input("📝 소방학 기출 진행도 (%)", 0, 100, study_state["fire_prob"])

    st.write("<br><br>", unsafe_allow_html=True)

    # --- 응급처치학개론 ---
    st.markdown("<h2 style='color: #3498DB;'>🚑 응급처치학개론</h2>", unsafe_allow_html=True)
    st.markdown("#### 📍 단계별 진도")
    study_state["em_theory"] = st.number_input("1. 이론 강의 완료 수", 0, 200, study_state["em_theory"])
    study_state["em_review"] = st.number_input("2. 전체 복습 회독 수", 0, 50, study_state["em_review"])
    study_state["em_prob"] = st.number_input("3. 기출/문제풀이 진행도 (%)", 0, 100, study_state["em_prob"])

    st.write("<br>", unsafe_allow_html=True)
    if st.button("💾 필기 진도 영구 저장하기", use_container_width=True):
        save_study_data(study_state)
        st.success("✅ 공부 진도가 안전하게 저장되었습니다!")
        
    st.write("---")
    
    # --- 모의고사 점수 시스템 (새로 추가) ---
    st.markdown("<h2 style='color: #9B59B6;'>💯 4단계: 실전 모의고사 기록</h2>", unsafe_allow_html=True)
    
    c_mock1, c_mock2 = st.columns(2)
    with c_mock1:
        mock_date = st.date_input("응시 날짜", date.today(), key="mock_date")
        mock_sub = st.selectbox("과목", ["소방학개론", "응급처치학개론"])
    with c_mock2:
        mock_round = st.text_input("모의고사 회차", placeholder="예: 전범위 1회, 해커스 3회")
        mock_score = st.number_input("점수", min_value=0, max_value=100, value=80, step=5)
        
    # 글자 겹침 방지: 제목은 짧게, 설명은 placeholder로 뺌
    mock_memo = st.text_area("오답 노트 / 약점 파악", placeholder="틀린 문제의 원인이나 헷갈렸던 개념을 적어둬.")
    
    if st.button("💾 모의고사 점수 저장", use_container_width=True):
        new_mock = pd.DataFrame({"날짜": [str(mock_date)], "과목": [mock_sub], "회차": [mock_round], "점수": [mock_score], "오답노트": [mock_memo]})
        df_mock = load_mock_data()
        df_mock = pd.concat([df_mock, new_mock], ignore_index=True)
        df_mock.to_csv(MOCK_FILE, index=False, encoding="utf-8-sig")
        st.success("✅ 모의고사 점수가 엑셀에 누적 저장됐어!")
        
    df_mock = load_mock_data()
    if not df_mock.empty:
        df_mock['날짜'] = pd.to_datetime(df_mock['날짜'])
        # 과목별로 점수 분리해서 그래프 그리기
        chart_data = df_mock.pivot_table(index='날짜', columns='과목', values='점수', aggfunc='mean')
        st.line_chart(chart_data)
        
        with st.expander("📋 모의고사 전체 기록 보기"):
            st.dataframe(df_mock.sort_values(by="날짜", ascending=False))

# ==========================================
# TAB 2: 러닝 기록
# ==========================================
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        run_date = st.date_input("🗓️ 훈련 날짜", date.today())
        weight = st.number_input("⚖️ 체중 (kg)", value=float(last_weight), step=0.1)
        avg_hr = st.number_input("📉 평균 심박 (bpm)", min_value=60, max_value=200, value=140)
    with c2:
        duty_type = st.selectbox("🏥 근무 형태", ["데이", "이브닝", "나이트", "더블 (16시간)", "오프"])
        vo2max = st.number_input("🫀 VO2 Max", value=float(last_vo2), step=0.1)
        max_hr = st.number_input("📈 최대 심박 (bpm)", min_value=60, max_value=220, value=150)

    shoe_used = st.selectbox("👟 착용 러닝화 선택", ["선택 안함", "아디다스 하이퍼부스트 런", "노바 블라스트 5", "아디제로 에보 SL (1)", "아디제로 에보 SL (2)", "클라우드 몬스터 3 하이퍼"])
    shoe_img_map = {"아디다스 하이퍼부스트 런": "hyperboost.jpg", "노바 블라스트 5": "nova5.jpg", "아디제로 에보 SL (1)": "evo1.jpg", "아디제로 에보 SL (2)": "evo2.jpg", "클라우드 몬스터 3 하이퍼": "cloudmonster.jpg"}
    if shoe_used in shoe_img_map and os.path.exists(shoe_img_map[shoe_used]):
        st.image(shoe_img_map[shoe_used], width=400)

    target_hr = st.selectbox("🎯 훈련 목적", ["150bpm 미만 (리커버리)", "159bpm 미만 (크루즈/존3)", "타겟 없음 (자유 훈련)"])
    condition = st.slider("🔋 주관적 피로도 (1:최악 ~ 5:최상)", 1, 5, 3)
    
    with st.expander("📝 훈련 특이사항 메모"): 
        # 글자 겹침 방지용 placeholder 적용
        run_memo = st.text_area("메모", placeholder="후면 사슬 데미지, 발바닥 통증 등 기입", label_visibility="collapsed")

    if st.button("💾 러닝 기록 저장 및 판독", use_container_width=True):
        if "150bpm" in target_hr and max_hr >= 150: st.error("❌ [Fail] 최대 심박 150 오버. 다음엔 파워워킹 전환해.")
        elif "159bpm" in target_hr and max_hr >= 160: st.error("❌ [Fail] 최대 심박 160 오버. 존4 역치 훈련으로 빠짐.")
        else: st.success("✅ [Pass] 심박 통제 완벽함. 훈련 성공.")
        new_run = pd.DataFrame({"날짜": [str(run_date)], "근무": [duty_type], "컨디션": [condition], "체중": [weight], "VO2Max": [vo2max], "장비": [shoe_used], "타겟": [target_hr], "평균심박": [avg_hr], "최대심박": [max_hr], "메모": [run_memo]})
        df_run = load_run_data() 
        df_run = pd.concat([df_run, new_run], ignore_index=True)
        df_run.to_csv(RUN_FILE, index=False, encoding="utf-8-sig")

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 러닝 누적 트렌드</h3>", unsafe_allow_html=True)
    if not df_run.empty:
        df_run['날짜'] = pd.to_datetime(df_run['날짜'])
        df_run = df_run.sort_values('날짜').set_index('날짜')
        st.write("**체중 변화 (가벼워지는 몸)**")
        st.line_chart(df_run['체중'])
        st.write("**가민 VO2 Max 궤적 (엔진 업그레이드)**")
        st.line_chart(df_run['VO2Max'])

# ==========================================
# TAB 3: 체력학원 기록
# ==========================================
with tab3:
    gym_date = st.date_input("🗓️ 측정 날짜", date.today(), key="gym_date_tab3")
    c_gym1, c_gym2 = st.columns(2)
    with c_gym1:
        grip = st.number_input("💪 악력 (kg)", value=40.0, step=0.1)
        sit_reach = st.number_input("🧘 좌전굴 (cm)", value=10.0, step=0.1)
        shuttle = st.number_input("🏃‍♂️ 왕복오래달리기 (회)", value=40, step=1)
    with c_gym2:
        back_str = st.number_input("🏋️ 배근력 (kg)", value=150.0, step=0.1)
        jump = st.number_input("🐸 제자리멀리뛰기 (cm)", value=200, step=1)
        
    with st.expander("📝 학원 피드백 메모"): 
        # 글자 겹침 방지용 placeholder 적용
        gym_memo = st.text_area("메모", placeholder="강사님 피드백, 보강할 근육 등 기입", label_visibility="collapsed")

    if st.button("💾 체력학원 기록 저장", use_container_width=True):
        new_gym = pd.DataFrame({"날짜": [str(gym_date)], "악력": [grip], "좌전굴": [sit_reach], "왕오달": [shuttle], "제멀": [jump], "배근력": [back_str], "메모": [gym_memo]})
        df_gym = load_gym_data()
        df_gym = pd.concat([df_gym, new_gym], ignore_index=True)
        df_gym.to_csv(GYM_FILE, index=False, encoding="utf-8-sig")
        st.success("✅ 체력 기록이 안전하게 저장되었습니다.")

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 종목별 성장 궤적</h3>", unsafe_allow_html=True)
    df_gym = load_gym_data()
    if not df_gym.empty:
        df_gym['날짜'] = pd.to_datetime(df_gym['날짜'])
        df_gym = df_gym.sort_values('날짜').set_index('날짜')
        st.write("**1. 근력 (kg)** - 악력, 배근력")
        st.line_chart(df_gym[['악력', '배근력']])
        st.write("**2. 유연성/순발력 (cm)** - 좌전굴, 제멀")
        st.line_chart(df_gym[['좌전굴', '제멀']])
        st.write("**3. 심폐지구력 (회)** - 왕오달")
        st.line_chart(df_gym[['왕오달']])

# ==========================================
# TAB 4: 피드백 복사
# ==========================================
with tab4:
    st.markdown("<h3 style='color: #2C3E50;'>📋 피드백 전송용 텍스트</h3>", unsafe_allow_html=True)
    try: feedback_memo = run_memo
    except NameError: feedback_memo = ""
    feedback_text = f"""[훈련 보고서]
- 날짜: {date.today()} / 근무: {duty_type}
- 체중: {weight}kg / VO2Max: {vo2max}
- 장비: {shoe_used} / 타겟: {target_hr}
- 심박: 평균 {avg_hr}bpm / 최대 {max_hr}bpm
- 메모: {feedback_memo}"""
    st.code(feedback_text, language="markdown")

# --- 하단 캐릭터 ---
st.write("---")
bottom_image_png = "firefighter.png"
bottom_image_jpg = "firefighter.jpg"
img_path = bottom_image_png if os.path.exists(bottom_image_png) else (bottom_image_jpg if os.path.exists(bottom_image_jpg) else None)
if img_path:
    c_s1, c_img, c_s2 = st.columns([1, 1, 1])
    with c_img: st.image(img_path, width=150)