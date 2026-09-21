import streamlit as st
import pandas as pd
import os
import json
import gspread
import random
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
    # 윗몸 컬럼 추가됨
    cols = ["날짜", "악력", "좌전굴", "왕오달", "제멀", "배근력", "윗몸", "메모"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in ["악력", "좌전굴", "왕오달", "제멀", "배근력", "윗몸"]:
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
    cols = ["구분", "지정일", "내용"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

def load_study_time_data():
    ws = sheet.worksheet("StudyTime")
    data = ws.get_all_values()
    cols = ["날짜", "순공시간", "메모"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    if '순공시간' in df.columns: df['순공시간'] = pd.to_numeric(df['순공시간'], errors='coerce')
    return df

def get_latest_and_avg(df, col_name, default_val):
    if df.empty or col_name not in df.columns or df[col_name].dropna().empty:
        return default_val, 0.0
    valid_data = df[col_name].dropna()
    return valid_data.iloc[-1], valid_data.mean()

# --- 체력 점수 계산 함수 (소방 남자 기준 환산) ---
def get_score_grip(val):
    if val >= 60.0: return 10
    elif val >= 58.0: return 9
    elif val >= 56.0: return 8
    elif val >= 54.0: return 7
    elif val >= 52.0: return 6
    elif val >= 50.0: return 5
    elif val >= 48.0: return 4
    elif val >= 46.0: return 3
    elif val >= 44.0: return 2
    elif val >= 42.0: return 1
    return 0

def get_score_sit_reach(val):
    if val >= 25.8: return 10
    elif val >= 24.2: return 9
    elif val >= 22.8: return 8
    elif val >= 21.3: return 7
    elif val >= 19.9: return 6
    elif val >= 18.3: return 5
    elif val >= 16.8: return 4
    elif val >= 15.6: return 3
    elif val >= 14.3: return 2
    elif val >= 13.0: return 1
    return 0

def get_score_shuttle(val):
    if val >= 78: return 10
    elif val >= 74: return 9
    elif val >= 70: return 8
    elif val >= 66: return 7
    elif val >= 62: return 6
    elif val >= 58: return 5
    elif val >= 54: return 4
    elif val >= 48: return 3
    elif val >= 43: return 2
    elif val >= 39: return 1
    return 0

def get_score_jump(val):
    if val >= 263: return 10
    elif val >= 258: return 9
    elif val >= 253: return 8
    elif val >= 248: return 7
    elif val >= 243: return 6
    elif val >= 238: return 5
    elif val >= 233: return 4
    elif val >= 228: return 3
    elif val >= 223: return 2
    elif val >= 218: return 1
    return 0

def get_score_back(val):
    if val >= 206: return 10
    elif val >= 201: return 9
    elif val >= 196: return 8
    elif val >= 191: return 7
    elif val >= 186: return 6
    elif val >= 181: return 5
    elif val >= 176: return 4
    elif val >= 171: return 3
    elif val >= 166: return 2
    elif val >= 161: return 1
    return 0

def get_score_situp(val):
    if val >= 52: return 10
    elif val >= 50: return 9
    elif val >= 48: return 8
    elif val >= 46: return 7
    elif val >= 43: return 6
    elif val >= 41: return 5
    elif val >= 39: return 4
    elif val >= 37: return 3
    elif val >= 35: return 2
    elif val >= 33: return 1
    return 0

# --- 🌟 상단 대시보드 ---
st.markdown("<h1 style='text-align: center; font-size: 32px; color: #FF4B4B;'>🔥 2027 소방 컨트롤 타워</h1>", unsafe_allow_html=True)

# 💡 랜덤 동기부여 명언
quotes = [
    "네가 포기하고 싶은 오늘이, 누군가에게는 그토록 살고 싶었던 내일이다.",
    "땀은 배신하지 않는다. 고통은 지나가지만, 영광은 남는다.",
    "오늘 걷지 않으면 내일은 뛰어야 한다.",
    "준비된 자만이 기회를 잡는다. 2027년, 그 자리는 내 것이다.",
    "반복에 지치지 않는 자가 성취한다.",
    "불 속으로 뛰어들 용기, 그 용기를 위한 오늘의 땀방울."
]
st.markdown(f"<p style='text-align: center; color: #7F8C8D; font-style: italic; font-size: 16px;'>\"{random.choice(quotes)}\"</p>", unsafe_allow_html=True)

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

# --- 탭 구성 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 필기", "🏃 러닝", "🏋️ 체력", "📋 피드백", "📅 플래너"])

# TAB 1: 필기 진도
with tab1:
    st.markdown("<h2 style='color: #27AE60;'>⏱️ 일일 순공 시간 (캠스터디)</h2>", unsafe_allow_html=True)
    df_study_time = load_study_time_data()
    
    if not df_study_time.empty and '날짜' in df_study_time.columns:
        df_study_time['날짜'] = pd.to_datetime(df_study_time['날짜'], errors='coerce')
        st.markdown("#### 📊 최근 순공 시간 추이")
        chart_data = df_study_time.groupby('날짜')['순공시간'].sum()
        st.bar_chart(chart_data)
        
    c_t1, c_t2, c_t3 = st.columns([1, 1, 2])
    with c_t1:
        st_date = st.date_input("공부 날짜", date.today(), key="st_date")
    with c_t2:
        st_hours = st.number_input("순공 시간 (시간)", min_value=0.0, max_value=24.0, value=8.0, step=0.5, key="st_hours")
    with c_t3:
        st_memo = st.text_input("메모", placeholder="집중도, 특이사항", key="st_memo")
        
    if st.button("💾 순공 시간 저장", use_container_width=True):
        sheet.worksheet("StudyTime").append_row([str(st_date), st_hours, st_memo])
        st.success(f"✅ {st_date} 순공시간 {st_hours}시간 저장 완료!")
        st.rerun()

    st.write("---")
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
        "아디다스 하이퍼부스트 런": "hyperboost.jpg", "노바 블라스트 5": "nova5.jpg", 
        "아디제로 에보 SL (1)": "evo1.jpg", "아디제로 에보 SL (2)": "evo2.jpg", "클라우드 몬스터 3 하이퍼": "cloudmonster.jpg"
    }
    if shoe_used != "선택 안함":
        img_filename = shoe_img_map.get(shoe_used)
        if img_filename and os.path.exists(img_filename): st.image(img_filename, width=300)

    target_hr = st.selectbox("🎯 훈련 목적", ["150bpm 미만 (리커버리)", "159bpm 미만 (크루즈/존3)", "타겟 없음 (자유 훈련)"])
    condition = st.slider("🔋 주관적 피로도 (1:최악 ~ 5:최상)", 1, 5, 3)
    with st.expander("📝 훈련 특이사항 메모"): 
        run_memo = st.text_area("러닝 메모", placeholder="특이사항 기입", label_visibility="collapsed")

    if st.button("💾 러닝 기록 저장 및 판독", use_container_width=True):
        if "150bpm" in target_hr and max_hr >= 150: st.error("❌ [Fail] 최대 심박 150 오버. 다음엔 파워워킹 전환해.")
        elif "159bpm" in target_hr and max_hr >= 160: st.error("❌ [Fail] 최대 심박 160 오버. 존4 역치 훈련으로 빠짐.")
        else: st.success("✅ [Pass] 심박 통제 완벽함. 훈련 성공.")
        sheet.worksheet("Run").append_row([str(run_date), duty_type, condition, weight, vo2max, shoe_used, target_hr, avg_hr, max_hr, cadence, run_memo])
        st.success("✅ 러닝 기록이 저장되었습니다!")
        st.rerun()

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 러닝 누적 트렌드</h3>", unsafe_allow_html=True)
    if not df_run.empty and '날짜' in df_run.columns:
        df_run['날짜'] = pd.to_datetime(df_run['날짜'], errors='coerce')
        df_run = df_run.sort_values('날짜').set_index('날짜')
        if '체중' in df_run.columns: st.line_chart(df_run['체중'])
        if 'VO2Max' in df_run.columns: st.line_chart(df_run['VO2Max'])

# TAB 3: 체력학원 기록
with tab3:
    df_gym = load_gym_data()
    if not df_gym.empty:
        st.markdown("#### 🏆 최근 측정 기록 (평균 대비)")
        last_grip, avg_grip = get_latest_and_avg(df_gym, '악력', 0)
        last_sit, avg_sit = get_latest_and_avg(df_gym, '좌전굴', 0)
        last_shut, avg_shut = get_latest_and_avg(df_gym, '왕오달', 0)
        gc1, gc2, gc3 = st.columns(3)
        gc1.metric("💪 악력", f"{last_grip}kg", f"{last_grip - avg_grip:.1f}kg")
        gc2.metric("🧘 좌전굴", f"{last_sit}cm", f"{last_sit - avg_sit:.1f}cm")
        gc3.metric("🏃 왕오달", f"{last_shut}회", f"{last_shut - avg_shut:.1f}회")
        st.write("---")

    gym_date = st.date_input("🗓️ 측정 날짜", date.today(), key="gym_date_tab3")
    
    # --- 체력 점수 실시간 환산 패널 ---
    st.markdown("#### 🏅 실시간 점수 환산 (남자 기준)")
    c_gym1, c_gym2 = st.columns(2)
    with c_gym1:
        grip = st.number_input("💪 악력 (kg)", value=40.0, step=0.1)
        sit_reach = st.number_input("🧘 좌전굴 (cm)", value=10.0, step=0.1)
        shuttle = st.number_input("🏃‍♂️ 왕복오래달리기 (회)", value=40, step=1)
    with c_gym2:
        back_str = st.number_input("🏋️ 배근력 (kg)", value=150.0, step=0.1)
        jump = st.number_input("🐸 제자리멀리뛰기 (cm)", value=200, step=1)
        situp = st.number_input("🛌 윗몸일으키기 (회/1분)", value=40, step=1)
        
    s_grip = get_score_grip(grip)
    s_sit_reach = get_score_sit_reach(sit_reach)
    s_shuttle = get_score_shuttle(shuttle)
    s_back = get_score_back(back_str)
    s_jump = get_score_jump(jump)
    s_situp = get_score_situp(situp)
    total_score = s_grip + s_sit_reach + s_shuttle + s_back + s_jump + s_situp
    
    st.info(f"🔥 현재 수치로 체력시험 응시 시 예상 점수는 **총 {total_score}점** (60점 만점) 입니다!")
        
    with st.expander("📝 학원 피드백 메모"): 
        gym_memo = st.text_area("학원 메모", placeholder="강사님 피드백 등 기입", label_visibility="collapsed")

    if st.button("💾 체력 기록 저장", use_container_width=True):
        sheet.worksheet("Gym").append_row([str(gym_date), grip, sit_reach, shuttle, jump, back_str, situp, gym_memo])
        st.success("✅ 체력 기록 및 윗몸일으키기 저장 완료!")
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
            
        cols_gym3 = [c for c in ['왕오달', '윗몸'] if c in df_gym.columns]
        if cols_gym3:
            st.write("**3. 심폐/근지구력 (회)** - 왕오달, 윗몸일으키기")
            st.line_chart(df_gym[cols_gym3])

# TAB 4: 피드백 복사
with tab4:
    st.markdown("<h3 style='color: #2C3E50;'>📋 피드백 전송용 텍스트</h3>", unsafe_allow_html=True)
    try: feedback_memo = run_memo
    except NameError: feedback_memo = ""
    safe_duty = duty_type if 'duty_type' in locals() else "기록 없음"
    safe_weight = weight if 'weight' in locals() else "기록 없음"
    safe_vo2 = vo2max if 'vo2max' in locals() else "기록 없음"
    safe_shoe = shoe_used if 'shoe_used' in locals() else "기록 없음"
    safe_avg = avg_hr if 'avg_hr' in locals() else "0"
    safe_max = max_hr if 'max_hr' in locals() else "0"
    safe_cadence = cadence if 'cadence' in locals() else "0"

    st.code(f"""[훈련 보고서]\n- 날짜: {date.today()} / 근무: {safe_duty}\n- 체중: {safe_weight}kg / VO2Max: {safe_vo2}\n- 장비: {safe_shoe}\n- 심박: 평균 {safe_avg}bpm / 최대 {safe_max}bpm\n- 케이던스: {safe_cadence}spm\n- 메모: {feedback_memo}""", language="markdown")

# TAB 5: 📅 플래너 & 체크리스트
with tab5:
    st.markdown("<h2 style='color: #F39C12;'>📅 플래너 & 체크리스트</h2>", unsafe_allow_html=True)
    df_plan = load_plan_data()

    # --- 1. 월간 목표 ---
    st.markdown("#### 🏆 월간 목표")
    c_m1, c_m2 = st.columns([1, 2])
    with c_m1:
        m_date = st.date_input("기준 월 선택 (달력 터치)", date.today(), key="m_date")
        m_str = m_date.strftime("%Y년 %m월")
    
    df_m = df_plan[(df_plan['구분'] == '월간') & (df_plan['지정일'] == m_str)]
    m_val = df_m.iloc[-1]['내용'] if not df_m.empty else ""
    
    with c_m2:
        m_goal = st.text_area("목표 내용", value=m_val, placeholder="예: 소방학 1회독 완강", label_visibility="collapsed")
        
    if st.button(f"💾 {m_str} 목표 저장", use_container_width=True, key="btn_m"):
        sheet.worksheet("Plan").append_row(["월간", m_str, m_goal])
        st.success(f"✅ {m_str} 목표 저장 완료!")
        st.rerun()

    st.write("---")

    # --- 2. 주간 목표 ---
    st.markdown("#### 🎯 주간 목표")
    w_dates = st.date_input("주간 기간 선택 (시작일~종료일 드래그)", [date.today(), date.today()], key="w_date")
    if len(w_dates) == 2:
        w_str = f"{w_dates[0].strftime('%Y/%m/%d')} ~ {w_dates[1].strftime('%Y/%m/%d')}"
    else:
        w_str = f"{w_dates[0].strftime('%Y/%m/%d')} ~ (종료일 선택 요망)"
        
    df_w = df_plan[(df_plan['구분'] == '주간') & (df_plan['지정일'] == w_str)]
    w_val = df_w.iloc[-1]['내용'] if not df_w.empty else ""
    
    w_goal = st.text_area("주간 목표", value=w_val, placeholder="예: 기출 3회차 풀기, 5km 런닝 2회", label_visibility="collapsed")
    
    if st.button(f"💾 주간 목표 저장", use_container_width=True, key="btn_w"):
        sheet.worksheet("Plan").append_row(["주간", w_str, w_goal])
        st.success("✅ 주간 목표 저장 완료!")
        st.rerun()

    st.write("---")

    # --- 3. 일간 체크리스트 ---
    st.markdown("#### ✅ 일간 체크리스트")
    d_date = st.date_input("날짜 선택 (어제/오늘 등)", date.today(), key="d_date")
    d_str = d_date.strftime("%Y-%m-%d")
    
    df_d = df_plan[(df_plan['구분'] == '일간') & (df_plan['지정일'] == d_str)]
    d_val_json = df_d.iloc[-1]['내용'] if not df_d.empty else "{}"
    try: daily_tasks = json.loads(d_val_json)
    except: daily_tasks = {}
    
    tasks, checks = [], []
    existing_keys = list(daily_tasks.keys())
    
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
            
    completed = sum(checks)
    total = len(tasks)
    prog = completed / total if total > 0 else 0.0
    
    st.progress(prog)
    st.write(f"**달성률: {int(prog * 100)}%** ({completed}/{total})")
    
    if st.button(f"💾 {d_str} 체크리스트 저장", use_container_width=True, key="btn_d"):
        new_daily = {tasks[i]: checks[i] for i in range(len(tasks))}
        sheet.worksheet("Plan").append_row(["일간", d_str, json.dumps(new_daily, ensure_ascii=False)])
        st.success("✅ 일간 체크리스트 저장 완료!")
        st.rerun()

# --- 하단 캐릭터 ---
st.write("---")
bottom_image_png = "firefighter.png"
bottom_image_jpg = "firefighter.jpg"
img_path = bottom_image_png if os.path.exists(bottom_image_png) else (bottom_image_jpg if os.path.exists(bottom_image_jpg) else None)
if img_path:
    c_s1, c_img, c_s2 = st.columns([1, 1, 1])
    with c_img: st.image(img_path, width=150)
