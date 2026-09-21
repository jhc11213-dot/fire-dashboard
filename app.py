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
    # 🏃 케이던스가 추가된 전체 열쇠(컬럼)
    cols = ["날짜", "근무", "컨디션", "체중", "VO2Max", "장비", "타겟", "평균심박", "최대심박", "케이던스", "메모"]
    
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
        
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # KeyError 방지용 안전장치 (열 이름이 존재할 때만 숫자로 변환)
    if '체중' in df.columns:
        df['체중'] = pd.to_numeric(df['체중'], errors='coerce')
    if 'VO2Max' in df.columns:
        df['VO2Max'] = pd.to_numeric(df['VO2Max'], errors='coerce')
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
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def load_mock_data():
    ws = sheet.worksheet("Mock")
    data = ws.get_all_values()
    cols = ["날짜", "과목", "회차", "점수", "오답노트"]
    if len(data) <= 1:
        if not data: ws.append_row(cols)
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data[1:], columns=data[0])
    if '점수' in df.columns:
        df['점수'] = pd.to_numeric(df['점수'], errors='coerce')
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

# --- 🌟 상단 대시보드 ---
st.markdown("<h1 style='text-align: center; font-size: 32px; color: #FF4B4B;'>🔥 2027 소방 컨트롤 타워</h1>", unsafe_allow_html=True)
d_day = (date(2027, 3, 6) - date.today()).days
df_run = load_run_data()

# 체중/VO2Max 에러 방지 처리
if not df_run.empty and '체중' in df_run.columns and pd.notnull(df_run['체중'].iloc[-1]):
    last_weight = df_run['체중'].iloc[-1]
else:
    last_weight = 75.0
    
if not df_run.empty and 'VO2Max' in df_run.columns and pd.notnull(df_run['VO2Max'].iloc[-1]):
    last_vo2 = df_run['VO2Max'].iloc[-1]
else:
    last_vo2 = 46.0

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric(label="소방 시험", value=f"D-{d_day}")
col_m2.metric(label="최근 체중", value=f"{last_weight} kg")
col_m3.metric(label="VO2 Max", value=f"{last_vo2}")
st.write("---")

# --- 탭 구성 ---
tab1, tab2, tab3, tab4 = st.tabs(["📚 필기", "🏃 러닝", "🏋️ 체력", "📋 피드백"])

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
        
    if not df_mock.empty and '과목' in df_mock.columns:
        df_fire = df_mock[df_mock['과목'] == '소방학개론']
        if not df_fire.empty:
            st.line_chart(df_fire.groupby('날짜')['점수'].mean())
            with st.expander("📋 소방학 모의고사 전체 기록"): st.dataframe(df_fire.sort_values(by="날짜", ascending=False))

    st.write("<br><br>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='color: #3498DB;'>🚑 응급처치학개론</h2>", unsafe_allow_html=True)
    st.markdown("#### 📍 단계별 진도")
    study_state["em_theory"] = st.number_input("1. 이론 강의 완료 수", 0, 200, study_state["em_theory"])
    study_state["em_review"] = st.number_input("2. 전체 복습 회독 수", 0, 50, study_state["em_review"])
    study_state["em_prob"] = st.number_input("3. 기출/문제풀이 진행도 (%)", 0, 100, study_state["em_prob"])

    st.write("---")
    st.markdown("#### 📍 4단계: 실전 모의고사 (응급처치학)")
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
        
    if not df_mock.empty and '과목' in df_mock.columns:
        df_em = df_mock[df_mock['과목'] == '응급처치학개론']
        if not df_em.empty:
            st.line_chart(df_em.groupby('날짜')['점수'].mean())
            with st.expander("📋 응급처치 모의고사 전체 기록"): st.dataframe(df_em.sort_values(by="날짜", ascending=False))

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
        # 🏃 케이던스 입력칸
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
        
        # 케이던스를 포함해서 엑셀에 저장
        new_run = [str(run_date), duty_type, condition, weight, vo2max, shoe_used, target_hr, avg_hr, max_hr, cadence, run_memo]
        sheet.worksheet("Run").append_row(new_run)
        st.success("✅ 러닝 기록이 저장되었습니다!")

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

    st.write("---")
    st.markdown("<h3 style='color: #2C3E50;'>📈 종목별 성장 궤적</h3>", unsafe_allow_html=True)
    df_gym = load_gym_data()
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

# --- 하단 캐릭터 ---
st.write("---")
bottom_image_png = "firefighter.png"
bottom_image_jpg = "firefighter.jpg"
img_path = bottom_image_png if os.path.exists(bottom_image_png) else (bottom_image_jpg if os.path.exists(bottom_image_jpg) else None)
if img_path:
    c_s1, c_img, c_s2 = st.columns([1, 1, 1])
    with c_img: st.image(img_path, width=150)
