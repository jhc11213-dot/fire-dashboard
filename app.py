import streamlit as st
import pandas as pd
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# 기본 세팅
st.set_page_config(page_title="2027 소방 컨트롤 타워", layout="centered")

# --- 🎨 디자인 세팅 ---
page_bg_css = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
.stApp, p, h1, h2, h3, h4, h5, h6, label, input, button, textarea, li {
    font-family: 'Jua', sans-serif !important;
}
span[class*="material"], i, .stIcon, svg {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
}
.stApp { background-color: #FFF8E7; }
.main .block-container {
    background-color: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    padding: 1.5rem 1rem !important; 
    margin-top: 1rem;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
}
p, div, span, label, h1, h2, h3, h4, h5, h6 { color: #333333; }
</style>
'''
st.markdown(page_bg_css, unsafe_allow_html=True)

# --- ☁️ 구글 스프레드시트 연동 ---
@st.cache_resource(ttl=600)
def init_connection():
    key_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        key_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

try:
    client = init_connection()
    sheet = client.open_by_key("1XMHkq1ffHRRQ1J-qzGZV76ELQfXjs6icr3a6cg8o6b4")
except Exception as e:
    st.error(f"🚨 구글 스프레드시트 연동 실패! 에러 내용: {e}")
    st.stop()

# --- 데이터 읽기/쓰기 함수 ---
def load_run_data():
    ws = sheet.worksheet("Run")
    data = ws.get_all_values()
    cols = ["날짜", "근무", "컨디션", "체중", "VO2Max", "장비", "타겟", "평균심박", "최대심박", "케이던스", "메모"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    if '체중' in df.columns: df['체중'] = pd.to_numeric(df['체중'], errors='coerce')
    if 'VO2Max' in df.columns: df['VO2Max'] = pd.to_numeric(df['VO2Max'], errors='coerce')
    return df

def load_gym_data():
    ws = sheet.worksheet("Gym")
    data = ws.get_all_values()
    cols = ["날짜", "악력", "좌전굴", "왕오달", "제멀", "배근력", "메모"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in ["악력", "좌전굴", "왕오달", "제멀", "배근력"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def load_mock_data():
    ws = sheet.worksheet("Mock")
    data = ws.get_all_values()
    cols = ["날짜", "과목", "회차", "점수", "오답노트"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    if '점수' in df.columns: df['점수'] = pd.to_numeric(df['점수'], errors='coerce')
    return df

def load_study_data():
    ws = sheet.worksheet("Study")
    try:
        val = ws.acell('A1').value
        if val: return json.loads(val)
    except: pass
    return {
        "fire_theory": 0, "fire_special": [], 
        "fire_review": {"기초이론": 0, "연소이론": 0, "화재이론": 0, "소화이론": 0, "건축방재 및 피난": 0, "위험물 및 특수가연물": 0, "소방시설": 0, "소방행정 및 조직": 0, "소방기능": 0, "재난관리론": 0},
        "fire_prob": 0,
        "em_theory": 0, "em_review": 0, "em_prob": 0
    }

def load_plan_data():
    ws = sheet.worksheet("Plan")
    data = ws.get_all_values()
    cols = ["날짜", "월간목표", "주간목표", "일간계획"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# 📊 최근값과 평균값을 계산해주는 헬퍼 함수
def get_latest_and_avg(df, col_name, default_val):
    if df.empty or col_name not in df.columns or df[col_name].dropna().empty:
        return default_val, 0.0
    valid_data = df[col_name].dropna()
    return valid_data.iloc[-1], valid_data.mean()

# --- 🌟 상단 대시보드 ---
st.markdown("<h1 style='text-align: center; font-size: 32px; color: #FF4B4B;'>🔥 2027 소방 컨트롤 타워</h1>", unsafe_allow_html=True)
d_day = (date(2027, 3, 6) - date.today()).days
df_run = load_run_data()

last_weight, avg_weight = get_latest_and_avg(df_run, '체중', 81.4)
last_vo2, avg_vo2 = get_latest_and_avg(df_run, 'VO2Max', 46.0)

weight_delta = last_weight - avg_weight if avg_weight != 0 else 0
vo2_delta = last_vo2 - avg_vo2 if avg_vo2 != 0 else 0

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric(label="소방 시험", value=f"D-{d_day}")
col_m2.metric(label="최근 체중", value=f"{last_weight:.1f}kg", delta=f"{weight_delta:.1f}kg (평균대비)", delta_color="inverse")
col_m3.metric(label="VO2 Max", value=f"{last_vo2:.1f}", delta=f"{vo2_delta:.1f} (평균대비)")
st.write("---")

# --- 탭 구성 (플래너 추가) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 필기", "🏃 러닝", "🏋️ 체력", "📋 피드백", "📅 플래너"])

# TAB 1: 필기 진도
with tab1:
    study_state = load_study_data()
    df_mock = load_mock_data()
    if not df_mock.empty and '날짜' in df_mock.columns:
        df_mock['날짜'] = pd.to_datetime(df_mock['날짜'], errors='coerce')

    st.markdown("<h2 style='color: #E74C3C;'>🚒 소방학개론</h2>", unsafe_allow_html=True)
    st.markdown("#### 📍 1단계: 이론 강의")
    study_state["fire_theory"] = st.slider("메인 이론 강의 (총 107강)", 0, 107, study_state["fire_theory"])
    st.progress(study_state["fire_theory"] / 107.0)
    
    with st.expander("➕ 특강/서브 강의 추가하기"):
        new_sp_name = st.text_input("특강 이름")
        new_sp_total = st.number_input("총 강의 수", min_value=1, value=10)
        if st.button("특강 등록", use_container_width=True):
            if new_sp_name:
                study_state["fire_special"].append({"name": new_sp_name, "total": new_sp_total, "completed": 0})
                sheet.worksheet("Study").update_acell('A1', json.dumps(study_state, ensure_ascii=False))
                st.rerun()
                
    for i, sp in enumerate(study_state["fire_special"]):
        sp["completed"] = st.number_input(f"📺 {sp['name']} (총 {sp['total']}강)", 0, sp["total"], sp["completed"], key=f"sp_{i}")
        st.progress(sp["completed"] / sp["total"])

    st.write("---")
    st.markdown("#### 📍 2단계: 단원별 복습 (회독)")
    c_rev1, c_rev2 = st.columns(2)
    chapters = list(study_state["fire_review"].keys())
    for i, chap in enumerate(chapters):
        if i % 2 == 0: study_state["fire_review"][chap] = c_rev1.number_input(f"📖 {chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
        else: study_state["fire_review"][chap] = c_rev2.number_input(f"📖 {chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
            
    total_fire_review = min(study_state["fire_review"].values())
    st.success(f"🔥 소방학개론 전체 **{total_fire_review}회독** 달성!")

    st.write("---")
    st.markdown("#### 📍 3단계: 기출 및 문제풀이")
    study_state["fire_prob"] = st.number_input("📝 소방학 기출 진행도 (%)", 0, 100, study_state["fire_prob"])

    st.write("---")
    st.markdown("#### 📍 4단계: 실전 모의고사 (소방학)")
    
    if not df_mock.empty and '과목' in df_mock.columns:
        df_fire = df_mock[df_mock['과목'] == '소방학개론']
        if not df_fire.empty:
            last_f, avg_f = get_latest_and_avg(df_fire, '점수', 0)
            f_delta = last_f - avg_f
            st.metric(label="최근 소방학 점수", value=f"{last_f:.1f}점", delta=f"{f_delta:.1f}점 (평균대비)")
            st.line_chart(df_fire.groupby('날짜')['점수'].mean())
            with st.expander("📋 소방학 모의고사 전체 기록"): st.dataframe(df_fire.sort_values(by="날짜", ascending=False))

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        f_mock_date = st.date_input("응시 날짜", date.today(), key="f_mock_date")
        f_mock_round = st.text_input("회차", placeholder="예: 전범위 1회", key="f_mock_round")
    with c_f2:
        f_mock_score = st.number_input("점수", min_value=0, max_value=100, value=80, step=5, key="f_mock_score")
    f_mock_memo = st.text_area("메모", placeholder="오답 노트 / 약점 파악 등", key="f_mock_memo", label_visibility="collapsed")
    
    if st.button("💾 소방학 모의고사 저장", use_container_width=True, key="f_mock_btn"):
        sheet.worksheet("Mock").append_row([str(f_mock_date), "소방학개론", f_mock_round, f_mock_score, f_mock_memo])
        st.success("✅ 소방학 점수 저장 완료!")
        st.rerun()

    st.write("<br><br>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='color: #3498DB;'>🚑 응급처치학개론</h2>", unsafe_allow_html=True)
    st.markdown("#### 📍 단계별 진도")
    study_state["em_theory"] = st.number_input("1. 이론 강의 완료 수", 0, 200, study_state["em_theory"])
    study_state["em_review"] = st.number_input("2. 전체 복습 회독 수", 0, 50, study_state["em_review"])
    study_state["em_prob"] = st.number_input("3. 기출/문제풀이 진행도 (%)", 0, 100, study_state["em_prob"])

    st.write("---")
    st.markdown("#### 📍 4단계: 실전 모의고사 (응급처치학)")
    
    if not df_mock.empty and '과목' in df_mock.columns:
        df_em = df_mock[df_mock['과목'] == '응급처치학개론']
        if not df_em.empty:
            last_e, avg_e = get_latest_and_avg(df_em, '점수', 0)
            e_delta = last_e - avg_e
            st.metric(label="최근 응급처치 점수", value=f"{last_e:.1f}점", delta=f"{e_delta:.1f}점 (평균대비)")
            st.line_chart(df_em.groupby('날짜')['점수'].mean())
            with st.expander("📋 응급처치 모의고사 전체 기록"): st.dataframe(df_em.sort_values(by="날짜", ascending=False))

    c_e1, c_e2 = st.columns(2)
    with c_e1:
        e_mock_date = st.date_input("응시 날짜", date.today(), key="e_mock_date")
        e_mock_round = st.text_input("회차", placeholder="예: 전범위 1회", key="e_mock_round")
    with c_e2:
        e_mock_score = st.number_input("점수", min_value=0, max_value=100, value=80, step=5, key="e_mock_score")
    e_mock_memo = st.text_area("메모", placeholder="오답 노트 / 약점 파악 등", key="e_mock_memo", label_visibility="collapsed")
    
    if st.button("💾 응급처치 모의고사 저장", use_container_width=True, key="e_mock_btn"):
        sheet.worksheet("Mock").append_row([str(e_mock_date), "응급처치학개론", e_mock_round, e_mock_score, e_mock_memo])
        st.success("✅ 응급처치 점수 저장 완료!")
        st.rerun()

    st.write("<br><br>", unsafe_allow_html=True)
    st.info("💡 위에서 체크한 1~3단계(이론/회독/기출) 진도를 저장하려면 아래 버튼을 누르세요.")
    if st.button("💾 전체 1~3단계 진도 클라우드 저장", use_container_width=True):
        sheet.worksheet("Study").update_acell('A1', json.dumps(study_state, ensure_ascii=False))
        st.success("✅ 진도가 구글 엑셀에 저장되었습니다!")

# TAB 2: 러닝 기록
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        run_date = st.date_input("🗓️ 훈련 날짜", date.today())
        weight = st.number_input("⚖️ 체중 (kg)", value=float(last_weight), step=0.1)
        avg_hr = st.number_input("📉 평균 심박 (bpm)", min_value=60, max_value=200, value=140)
        cadence = st.number_input("👣 케이던스 (spm)", min_value=100, max_value=250, value=170, step=1)
    with c2:
        duty_type = st.selectbox("🏥 근무 형태", ["데이", "이브닝", "나이트", "더블 (16시간)", "오프"])
        vo2max = st.number_input("🫀 VO2 Max", value=float(last_vo2), step=0.1)
        max_hr = st.number_input("📈 최대 심박 (bpm)", min_value=60, max_value=220, value=150)

    shoe_used = st.selectbox("👟 착용 러닝화 선택", ["선택 안함", "아디다스 하이퍼부스트 런", "노바 블라스트 5", "아디제로 에보 SL (1)", "아디제로 에보 SL (2)", "클라우드 몬스터 3 하이퍼"])
    shoe_img_map = {
        "아디다스 하이퍼부스트 런": "hyperboost.jpg", 
        "노바 블라스트 5": "nova5.jpg", 
        "아디제로 에보 SL (1)": "evo1.jpg", 
        "아디제로 에보 SL (2)": "evo2.jpg", 
        "클라우드 몬스터 3 하이퍼": "cloudmonster.jpg"
    }
    
    if shoe_used != "선택 안함":
        img_filename = shoe_img_map.get(shoe_used)
        if img_filename and os.path.exists(img_filename):
            st.image(img_filename, width=300)
        else:
            st.warning(f"💡 깃허브에 '{img_filename}' 파일이 없습니다. 사진을 업로드하면 여기에 나타납니다.")

    target_hr = st.selectbox("🎯 훈련 목적", ["150bpm 미만 (리커버리)", "159bpm 미만 (크루즈/존3)", "타겟 없음 (자유 훈련)"])
    condition = st.slider("🔋 주관적 피로도 (1:최악 ~ 5:최상)", 1, 5, 3)
    
    with st.expander("📝 훈련 특이사항 메모"): 
        run_memo = st.text_area("러닝 메모", placeholder="특이사항 기입", label_visibility="collapsed")

    if st.button("💾 러닝 기록 저장 및 판독", use_container_width=True):
        if "150bpm" in target_hr and max_hr >= 150: st.error("❌ [Fail] 최대 심박 150 오버. 다음엔 파워워킹 전환해.")
        elif "159bpm" in target_hr and max_hr >= 160: st.error("❌ [Fail] 최대 심박 160 오버. 존4 역치 훈련으로 빠짐.")
        else: st.success("✅ [Pass] 심박 통제 완벽함. 훈련 성공.")
        
        new_run = [str(run_date), duty_type, condition, weight, vo2max, shoe_used, target_hr, avg_hr, max_hr, cadence, run_memo]
        sheet.worksheet("Run").append_row(new_run)
        st.success("✅ 러닝 기록이 저장되었습니다!")
        st.rerun()

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 러닝 누적 트렌드</h3>", unsafe_allow_html=True)
    if not df_run.empty and '날짜' in df_run.columns:
        df_run['날짜'] = pd.to_datetime(df_run['날짜'], errors='coerce')
        df_run = df_run.sort_values('날짜').set_index('날짜')
        if '체중' in df_run.columns:
            st.write("**체중 변화 (가벼워지는 몸)**")
            st.line_chart(df_run['체중'])
        if 'VO2Max' in df_run.columns:
            st.write("**가민 VO2 Max 궤적 (엔진 업그레이드)**")
            st.line_chart(df_run['VO2Max'])

# TAB 3: 체력학원 기록
with tab3:
    df_gym = load_gym_data()
    
    if not df_gym.empty:
        st.markdown("#### 🏆 최근 측정 기록 (평균 대비)")
        last_grip, avg_grip = get_latest_and_avg(df_gym, '악력', 0)
        last_sit, avg_sit = get_latest_and_avg(df_gym, '좌전굴', 0)
        last_shut, avg_shut = get_latest_and_avg(df_gym, '왕오달', 0)
        last_jump, avg_jump = get_latest_and_avg(df_gym, '제멀', 0)
        last_back, avg_back = get_latest_and_avg(df_gym, '배근력', 0)

        gc1, gc2, gc3 = st.columns(3)
        gc1.metric("💪 악력", f"{last_grip}kg", f"{last_grip - avg_grip:.1f}kg")
        gc2.metric("🧘 좌전굴", f"{last_sit}cm", f"{last_sit - avg_sit:.1f}cm")
        gc3.metric("🏃 왕오달", f"{last_shut}회", f"{last_shut - avg_shut:.1f}회")
        
        gc4, gc5 = st.columns(2)
        gc4.metric("🐸 제자리멀리뛰기", f"{last_jump}cm", f"{last_jump - avg_jump:.1f}cm")
        gc5.metric("🏋️ 배근력", f"{last_back}kg", f"{last_back - avg_back:.1f}kg")
        st.write("---")

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
        gym_memo = st.text_area("학원 메모", placeholder="강사님 피드백 등 기입", label_visibility="collapsed")

    if st.button("💾 체력 기록 저장", use_container_width=True):
        new_gym = [str(gym_date), grip, sit_reach, shuttle, jump, back_str, gym_memo]
        sheet.worksheet("Gym").append_row(new_gym)
        st.success("✅ 체력 기록 저장 완료!")
        st.rerun()

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 종목별 성장 궤적</h3>", unsafe_allow_html=True)
    if not df_gym.empty and '날짜' in df_gym.columns:
        df_gym['날짜'] = pd.to_datetime(df_gym['날짜'], errors='coerce')
        df_gym = df_gym.sort_values('날짜').set_index('날짜')
        
        cols_gym1 = [c for c in ['악력', '배근력'] if c in df_gym.columns]
        if cols_gym1:
            st.write("**1. 근력 (kg)** - 악력, 배근력")
            st.line_chart(df_gym[cols_gym1])
            
        cols_gym2 = [c for c in ['좌전굴', '제멀'] if c in df_gym.columns]
        if cols_gym2:
            st.write("**2. 유연성/순발력 (cm)** - 좌전굴, 제멀")
            st.line_chart(df_gym[cols_gym2])
            
        if '왕오달' in df_gym.columns:
            st.write("**3. 심폐지구력 (회)** - 왕오달")
            st.line_chart(df_gym[['왕오달']])

# TAB 4: 피드백 복사
with tab4:
    st.markdown("<h3 style='color: #2C3E50;'>📋 피드백 전송용 텍스트</h3>", unsafe_allow_html=True)
    try: feedback_memo = run_memo
    except NameError: feedback_memo = ""
    
    safe_duty = duty_type if 'duty_type' in locals() else "기록 없음"
    safe_weight = weight if 'weight' in locals() else "기록 없음"
    safe_vo2 = vo2max if 'vo2max' in locals() else "기록 없음"
    safe_shoe = shoe_used if 'shoe_used' in locals() else "기록 없음"
    safe_target = target_hr if 'target_hr' in locals() else "기록 없음"
    safe_avg = avg_hr if 'avg_hr' in locals() else "0"
    safe_max = max_hr if 'max_hr' in locals() else "0"
    safe_cadence = cadence if 'cadence' in locals() else "0"

    feedback_text = f"""[훈련 보고서]
- 날짜: {date.today()} / 근무: {safe_duty}
- 체중: {safe_weight}kg / VO2Max: {safe_vo2}
- 장비: {safe_shoe} / 타겟: {safe_target}
- 심박: 평균 {safe_avg}bpm / 최대 {safe_max}bpm
- 케이던스: {safe_cadence}spm
- 메모: {feedback_memo}"""
    st.code(feedback_text, language="markdown")

# TAB 5: 📅 플래너 & 체크리스트 (신규 추가!)
with tab5:
    st.markdown("<h2 style='color: #F39C12;'>📅 목표 & 체크리스트</h2>", unsafe_allow_html=True)
    plan_date = st.date_input("🗓️ 날짜 선택 (과거 기록 조회/수정 가능)", date.today(), key="plan_date")

    df_plan = load_plan_data()
    
    # 선택한 날짜의 기존 데이터 불러오기
    existing_row = df_plan[df_plan['날짜'] == str(plan_date)]
    if not existing_row.empty:
        month_g = existing_row.iloc[-1]['월간목표']
        week_g = existing_row.iloc[-1]['주간목표']
        daily_json = existing_row.iloc[-1]['일간계획']
        try: daily_tasks = json.loads(daily_json) if daily_json else {}
        except: daily_tasks = {}
    else:
        month_g = ""
        week_g = ""
        daily_tasks = {}

    st.markdown("#### 🎯 이번 달 & 이번 주 목표")
    month_goal = st.text_area("🏆 월간 목표", value=month_g, placeholder="예: 소방학 1회독 완강, 체중 79kg 진입")
    week_goal = st.text_area("🎯 주간 목표", value=week_g, placeholder="예: 기출 3회차 풀기, 5km 런닝 2회")
    
    st.write("---")
    st.markdown("#### ✅ 일간 체크리스트 (오늘 할 일)")
    
    tasks = []
    checks = []
    existing_keys = list(daily_tasks.keys())
    
    # 5개의 체크리스트 입력칸 제공
    for i in range(5):
        default_task = existing_keys[i] if i < len(existing_keys) else ""
        default_check = daily_tasks.get(default_task, False) if default_task else False
        
        c_chk, c_txt = st.columns([1, 6])
        with c_chk:
            is_done = st.checkbox("완료", value=default_check, key=f"chk_{i}", label_visibility="collapsed")
        with c_txt:
            task_name = st.text_input(f"할 일 {i+1}", value=default_task, label_visibility="collapsed", key=f"task_{i}", placeholder=f"할 일 {i+1} 입력")
        
        if task_name.strip():
            tasks.append(task_name.strip())
            checks.append(is_done)
            
    # 달성률 프로그레스 바 계산
    completed_count = sum(checks)
    total_count = len(tasks)
    progress_ratio = completed_count / total_count if total_count > 0 else 0.0
    
    st.write("<br>", unsafe_allow_html=True)
    st.progress(progress_ratio)
    st.write(f"**오늘의 달성률: {int(progress_ratio * 100)}%** ({completed_count}/{total_count})")
    
    if st.button("💾 플래너 저장", use_container_width=True):
        new_daily_dict = {tasks[i]: checks[i] for i in range(len(tasks))}
        row_data = [str(plan_date), month_goal, week_goal, json.dumps(new_daily_dict, ensure_ascii=False)]
        
        ws_plan = sheet.worksheet("Plan")
        try:
            # 해당 날짜가 이미 있으면 덮어쓰기 (중복 저장 방지)
            cell = ws_plan.find(str(plan_date), in_column=1)
            ws_plan.update_cell(cell.row, 1, row_data[0])
            ws_plan.update_cell(cell.row, 2, row_data[1])
            ws_plan.update_cell(cell.row, 3, row_data[2])
            ws_plan.update_cell(cell.row, 4, row_data[3])
        except gspread.exceptions.CellNotFound:
            # 해당 날짜가 없으면 새로 추가
            ws_plan.append_row(row_data)
            
        st.success("✅ 플래너가 저장되었습니다!")
        st.rerun()

# --- 하단 캐릭터 ---
st.write("---")
bottom_image_png = "firefighter.png"
bottom_image_jpg = "firefighter.jpg"
img_path = bottom_image_png if os.path.exists(bottom_image_png) else (bottom_image_jpg if os.path.exists(bottom_image_jpg) else None)
if img_path:
    c_s1, c_img, c_s2 = st.columns([1, 1, 1])
    with c_img: st.image(img_path, width=150)
