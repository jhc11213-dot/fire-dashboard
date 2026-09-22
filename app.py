import streamlit as st
import pandas as pd
import os
import json
import gspread
import random
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timezone, timedelta

# --- 🇰🇷 한국 시간(KST) 설정 ---
KST = timezone(timedelta(hours=9))
today_kst = datetime.now(KST).date()

# 기본 세팅
st.set_page_config(page_title="2027 소방 컨트롤 타워", layout="centered")

# --- 🎨 디자인 세팅 (세련된 차도남 스타일) ---
page_bg_css = '''
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

.stApp, p, h1, h2, h3, h4, h5, h6, label, input, button, textarea, li, .st-emotion-cache-1104idt {
    font-family: 'Pretendard', -apple-system, sans-serif !important;
}
.stApp { background-color: #F4F6F8; }
.main .block-container {
    background-color: #FFFFFF;
    border-radius: 16px;
    padding: 2.5rem 1.5rem !important; 
    margin-top: 1.5rem;
    border: 1px solid #E9ECEF;
    box-shadow: 0px 8px 30px rgba(0, 0, 0, 0.04);
}
h1, h2, h3, h4, h5, h6 { color: #1A1D20 !important; font-weight: 700 !important; letter-spacing: -0.5px; }
p, div, span, label, li { color: #343A40; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    height: 50px; white-space: pre-wrap; background-color: #F8F9FA;
    border-radius: 8px 8px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
}
.stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #212529 !important; }
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
    st.error(f"🚨 연동 실패! 에러: {e}")
    st.stop()

# --- 🚀 구글 데이터 밀림 완벽 차단 함수 ---
def parse_sheet_data(ws_name, cols):
    ws = sheet.worksheet(ws_name)
    data = ws.get_all_values()
    if len(data) <= 1:
        return pd.DataFrame(columns=cols)
    
    clean_rows = []
    for row in data[1:]:
        # 정해진 열(기둥) 개수보다 모자라면 빈칸 추가, 넘치면 잘라버림 (에러 원천 차단!)
        row = row + [""] * (len(cols) - len(row))
        clean_rows.append(row[:len(cols)])
        
    return pd.DataFrame(clean_rows, columns=cols)

# --- 🚀 구글 API 과부하 방지 (데이터 캐싱 적용) ---
@st.cache_data(ttl=60)
def load_run_data():
    cols = ["날짜", "근무", "컨디션", "체중", "VO2Max", "장비", "타겟", "평균심박", "최대심박", "케이던스", "메모"]
    df = parse_sheet_data("Run", cols)
    df['체중'] = pd.to_numeric(df['체중'], errors='coerce')
    df['VO2Max'] = pd.to_numeric(df['VO2Max'], errors='coerce')
    return df

@st.cache_data(ttl=60)
def load_gym_data():
    cols = ["날짜", "악력", "좌전굴", "왕오달", "제멀", "배근력", "윗몸", "메모"]
    df = parse_sheet_data("Gym", cols)
    for col in ["악력", "좌전굴", "왕오달", "제멀", "배근력", "윗몸"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

@st.cache_data(ttl=60)
def load_mock_data():
    cols = ["날짜", "과목", "회차", "점수", "오답노트"]
    df = parse_sheet_data("Mock", cols)
    df['점수'] = pd.to_numeric(df['점수'], errors='coerce')
    return df

@st.cache_data(ttl=60)
def load_study_data():
    ws = sheet.worksheet("Study")
    default_data = {
        "fire_theory": 0, "fire_special": [], 
        "fire_review": {"기초이론": 0, "연소이론": 0, "화재이론": 0, "소화이론": 0, "건축방재 및 피난": 0, "위험물 및 특수가연물": 0, "소방시설": 0, "소방행정 및 조직": 0, "소방기능": 0, "재난관리론": 0},
        "fire_prob": {"기초이론": 0, "연소이론": 0, "화재이론": 0, "소화이론": 0, "건축방재 및 피난": 0, "위험물 및 특수가연물": 0, "소방시설": 0, "소방행정 및 조직": 0, "소방기능": 0, "재난관리론": 0},
        "em_theory": 0, 
        "em_review": {"응급의료체계": 0, "환자평가": 0, "심폐소생술": 0, "내과응급": 0, "외상응급": 0, "특수응급(소아/노인)": 0}, 
        "em_prob": {"응급의료체계": 0, "환자평가": 0, "심폐소생술": 0, "내과응급": 0, "외상응급": 0, "특수응급(소아/노인)": 0}
    }
    try:
        val = ws.acell('A1').value
        if val: 
            data = json.loads(val)
            if isinstance(data.get("fire_prob"), (int, float)): data["fire_prob"] = default_data["fire_prob"]
            if "em_review" not in data or isinstance(data.get("em_review"), (int, float)): data["em_review"] = default_data["em_review"]
            if "em_prob" not in data or isinstance(data.get("em_prob"), (int, float)): data["em_prob"] = default_data["em_prob"]
            for k, v in default_data.items():
                if k not in data: data[k] = v
            return data
    except: pass
    return default_data

@st.cache_data(ttl=60)
def load_plan_data():
    cols = ["구분", "지정일", "내용"]
    return parse_sheet_data("Plan", cols)

@st.cache_data(ttl=60)
def load_study_time_data():
    cols = ["날짜", "순공시간", "메모"]
    df = parse_sheet_data("StudyTime", cols)
    df['순공시간'] = pd.to_numeric(df['순공시간'], errors='coerce')
    return df

def get_latest_and_avg(df, col_name, default_val):
    if df.empty or col_name not in df.columns or df[col_name].dropna().empty:
        return default_val, 0.0
    valid_data = df[col_name].dropna()
    return valid_data.iloc[-1], valid_data.mean()

# --- 🗑️ 데이터 에디터 (밀림 현상 & 이름 없는 열 완벽 차단!) ---
def manage_records(sheet_name, df, title, key_suffix):
    st.markdown(f"#### :material/edit_document: {title} 관리")
    st.caption("💡 표 왼쪽 빈 박스를 체크한 뒤 상단의 '휴지통' 아이콘으로 삭제하세요. 완료 후 반드시 [동기화]를 눌러주세요.")
    
    if df.empty:
        safe_df = pd.DataFrame(columns=df.columns)
    else:
        safe_df = df.copy()
        safe_df = safe_df.astype(str).replace(['nan', 'NaT', 'None', '<NA>', 'NaN'], '')

    edited_df = st.data_editor(safe_df, num_rows="dynamic", use_container_width=True, key=f"editor_{key_suffix}")
    
    if st.button(f":material/sync: {sheet_name} 시트 동기화", key=f"sync_{key_suffix}", use_container_width=True):
        ws = sheet.worksheet(sheet_name)
        ws.clear() # 기존 찌꺼기 완벽 삭제
        
        # A1(맨 위 왼쪽)부터 밀림 없이 강제 덮어쓰기!
        upload_data = [edited_df.columns.tolist()]
        if not edited_df.empty:
            upload_data.extend(edited_df.values.tolist())
            
        try:
            ws.update(values=upload_data, range_name="A1")
        except:
            ws.update("A1", upload_data) # 버전 호환용 안전장치
            
        st.cache_data.clear()
        st.success("✅ 구글 시트에 깔끔하게 반영 완료!")
        st.rerun()

# --- 체력 점수 계산 함수 ---
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
st.markdown("<h1 style='text-align: center; font-size: 28px; font-weight: 800; color: #111111; letter-spacing: -1px;'>2027 FIRE CONTROL TOWER</h1>", unsafe_allow_html=True)

quotes = [
    "네가 포기하고 싶은 오늘이, 누군가에게는 그토록 살고 싶었던 내일이다.",
    "땀은 배신하지 않는다. 고통은 지나가지만, 영광은 남는다.",
    "오늘 걷지 않으면 내일은 뛰어야 한다.",
    "준비된 자만이 기회를 잡는다. 2027년, 그 자리는 내 것이다.",
    "반복에 지치지 않는 자가 성취한다.",
    "불 속으로 뛰어들 용기, 그 용기를 위한 오늘의 땀방울."
]
st.markdown(f"<p style='text-align: center; color: #868E96; font-size: 15px; margin-top: -10px;'>\"{random.choice(quotes)}\"</p>", unsafe_allow_html=True)

d_day = (date(2027, 3, 6) - today_kst).days
df_run = load_run_data()

last_weight, avg_weight = get_latest_and_avg(df_run, '체중', 81.4)
last_vo2, avg_vo2 = get_latest_and_avg(df_run, 'VO2Max', 45.0)

weight_delta = last_weight - avg_weight if avg_weight != 0 else 0
vo2_delta = last_vo2 - avg_vo2 if avg_vo2 != 0 else 0

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric(label="D-DAY", value=f"D-{d_day}")
col_m2.metric(label="WEIGHT", value=f"{last_weight:.1f}kg", delta=f"{weight_delta:.1f}kg", delta_color="inverse")
col_m3.metric(label="VO2 MAX", value=f"{last_vo2:.1f}", delta=f"{vo2_delta:.1f}")
st.write("---")

# --- 탭 구성 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    ":material/menu_book: 필기", 
    ":material/directions_run: 러닝", 
    ":material/fitness_center: 체력", 
    ":material/assignment: 리포트", 
    ":material/calendar_month: 플래너"
])

# TAB 1: 필기 진도
with tab1:
    st.markdown("### :material/timer: 순공 시간")
    df_study_time = load_study_time_data()
    
    if not df_study_time.empty and '날짜' in df_study_time.columns:
        st_chart = df_study_time.copy()
        st_chart['날짜'] = pd.to_datetime(st_chart['날짜'], errors='coerce')
        st_chart = st_chart.dropna(subset=['날짜', '순공시간'])
        if not st_chart.empty:
            st.bar_chart(st_chart.groupby('날짜')['순공시간'].sum())
        
    c_t1, c_t2, c_t3 = st.columns([1, 1, 2])
    with c_t1: st_date = st.date_input("날짜", today_kst, key="st_date")
    with c_t2: st_hours = st.number_input("시간 (H)", min_value=0.0, max_value=24.0, value=8.0, step=0.5, key="st_hours")
    with c_t3: st_memo = st.text_input("메모", placeholder="특이사항", key="st_memo")
        
    if st.button(":material/save: 기록 저장", use_container_width=True, key="btn_st"):
        sheet.worksheet("StudyTime").append_row([str(st_date), st_hours, st_memo])
        st.cache_data.clear()
        st.rerun()
        
    with st.expander("⏱️ 순공 시간 기록 보기/관리"):
        manage_records("StudyTime", df_study_time, "순공 시간", "studytime")

    st.write("---")
    study_state = load_study_data()
    df_mock = load_mock_data()

    st.markdown("### :material/local_fire_department: 소방학개론")
    st.markdown("#### 1단계: 이론 강의")
    study_state["fire_theory"] = st.slider("메인 이론 강의", 0, 107, study_state["fire_theory"], key="fire_theory_in")
    st.progress(study_state["fire_theory"] / 107.0)
    
    with st.expander("서브 강의 추가"):
        new_sp_name = st.text_input("특강 이름", key="new_sp_name")
        new_sp_total = st.number_input("총 강의 수", min_value=1, value=10, key="new_sp_total")
        if st.button(":material/add: 등록", use_container_width=True, key="add_sp_btn"):
            if new_sp_name:
                study_state["fire_special"].append({"name": new_sp_name, "total": new_sp_total, "completed": 0})
                sheet.worksheet("Study").update_acell('A1', json.dumps(study_state, ensure_ascii=False))
                st.cache_data.clear()
                st.rerun()
                
    for i, sp in enumerate(study_state["fire_special"]):
        sp["completed"] = st.number_input(f"{sp['name']} (총 {sp['total']}강)", 0, sp["total"], sp["completed"], key=f"sp_{i}")
        st.progress(sp["completed"] / sp["total"])

    st.write("---")
    st.markdown("#### 2단계: 단원별 복습")
    c_rev1, c_rev2 = st.columns(2)
    chapters = list(study_state["fire_review"].keys())
    for i, chap in enumerate(chapters):
        if i % 2 == 0: study_state["fire_review"][chap] = c_rev1.number_input(f"{chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
        else: study_state["fire_review"][chap] = c_rev2.number_input(f"{chap}", 0, 50, study_state["fire_review"][chap], key=f"chap_{i}")
    st.caption(f"전체 {min(study_state['fire_review'].values())}회독 달성")

    st.write("---")
    st.markdown("#### 3단계: 단원별 기출/문제풀이")
    c_prob1, c_prob2 = st.columns(2)
    prob_chapters = list(study_state["fire_prob"].keys())
    for i, chap in enumerate(prob_chapters):
        if i % 2 == 0: study_state["fire_prob"][chap] = c_prob1.number_input(f"{chap}", 0, 50, study_state["fire_prob"][chap], key=f"f_prob_{i}")
        else: study_state["fire_prob"][chap] = c_prob2.number_input(f"{chap}", 0, 50, study_state["fire_prob"][chap], key=f"f_prob_{i}")
    st.caption(f"기출 전체 {min(study_state['fire_prob'].values())}회독 달성")

    st.write("---")
    st.markdown("#### 4단계: 실전 모의고사")
    
    FIRE_BENCHMARK = 60
    st.info("🎯 목표 합격선: 60점 (고정)", icon=":material/flag:")
    
    if not df_mock.empty and '과목' in df_mock.columns:
        df_fire = df_mock[df_mock['과목'] == '소방학개론'].copy()
        if not df_fire.empty:
            last_f, avg_f = get_latest_and_avg(df_fire, '점수', 0)
            diff = last_f - FIRE_BENCHMARK
            st.metric(label="최근 모의고사 점수", value=f"{last_f:.1f}점", delta=f"{diff:.1f}점 (합격선 대비)")
            
            df_fire['날짜'] = pd.to_datetime(df_fire['날짜'], errors='coerce')
            df_fire = df_fire.dropna(subset=['날짜', '점수'])
            if not df_fire.empty:
                chart_df = df_fire.groupby('날짜')['점수'].mean().reset_index()
                chart_df['합격선(60점)'] = FIRE_BENCHMARK
                chart_df = chart_df.set_index('날짜')
                chart_df.rename(columns={'점수': '내 점수'}, inplace=True)
                st.line_chart(chart_df[['내 점수', '합격선(60점)']])

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        f_mock_date = st.date_input("응시일", today_kst, key="f_mock_date")
        f_mock_round = st.text_input("회차", placeholder="예: 전범위 1회", key="f_mock_round")
    with c_f2:
        f_mock_score = st.number_input("점수", min_value=0, max_value=100, value=80, step=5, key="f_mock_score")
    f_mock_memo = st.text_area("메모", placeholder="오답 노트", key="f_mock_memo", label_visibility="collapsed")
    
    if st.button(":material/save: 점수 저장", use_container_width=True, key="f_mock_btn"):
        sheet.worksheet("Mock").append_row([str(f_mock_date), "소방학개론", f_mock_round, f_mock_score, f_mock_memo])
        st.cache_data.clear()
        st.rerun()

    st.write("<br>", unsafe_allow_html=True)
    st.markdown("### :material/medical_services: 응급처치학개론")
    st.markdown("#### 1단계: 이론 강의")
    study_state["em_theory"] = st.number_input("이론 완료 수", 0, 200, study_state["em_theory"], key="em_theory_in")
    
    st.write("---")
    st.markdown("#### 2단계: 단원별 복습")
    c_em_rev1, c_em_rev2 = st.columns(2)
    em_rev_chapters = list(study_state["em_review"].keys())
    for i, chap in enumerate(em_rev_chapters):
        if i % 2 == 0: study_state["em_review"][chap] = c_em_rev1.number_input(f"{chap}", 0, 50, study_state["em_review"][chap], key=f"em_rev_{i}")
        else: study_state["em_review"][chap] = c_em_rev2.number_input(f"{chap}", 0, 50, study_state["em_review"][chap], key=f"em_rev_{i}")
    st.caption(f"전체 {min(study_state['em_review'].values())}회독 달성")

    st.write("---")
    st.markdown("#### 3단계: 단원별 기출/문제풀이")
    c_em_prob1, c_em_prob2 = st.columns(2)
    em_prob_chapters = list(study_state["em_prob"].keys())
    for i, chap in enumerate(em_prob_chapters):
        if i % 2 == 0: study_state["em_prob"][chap] = c_em_prob1.number_input(f"{chap}", 0, 50, study_state["em_prob"][chap], key=f"em_prob_{i}")
        else: study_state["em_prob"][chap] = c_em_prob2.number_input(f"{chap}", 0, 50, study_state["em_prob"][chap], key=f"em_prob_{i}")
    st.caption(f"기출 전체 {min(study_state['em_prob'].values())}회독 달성")

    st.write("---")
    st.markdown("#### 4단계: 실전 모의고사")
    
    EM_BENCHMARK = 60
    st.info("🎯 목표 합격선: 60점 (고정)", icon=":material/flag:")
    
    if not df_mock.empty and '과목' in df_mock.columns:
        df_em = df_mock[df_mock['과목'] == '응급처치학개론'].copy()
        if not df_em.empty:
            last_e, avg_e = get_latest_and_avg(df_em, '점수', 0)
            diff_e = last_e - EM_BENCHMARK
            st.metric(label="최근 모의고사 점수", value=f"{last_e:.1f}점", delta=f"{diff_e:.1f}점 (합격선 대비)")

            df_em['날짜'] = pd.to_datetime(df_em['날짜'], errors='coerce')
            df_em = df_em.dropna(subset=['날짜', '점수'])
            if not df_em.empty:
                chart_df_e = df_em.groupby('날짜')['점수'].mean().reset_index()
                chart_df_e['합격선(60점)'] = EM_BENCHMARK
                chart_df_e = chart_df_e.set_index('날짜')
                chart_df_e.rename(columns={'점수': '내 점수'}, inplace=True)
                st.line_chart(chart_df_e[['내 점수', '합격선(60점)']])

    c_e1, c_e2 = st.columns(2)
    with c_e1:
        e_mock_date = st.date_input("응시일", today_kst, key="e_mock_date")
        e_mock_round = st.text_input("회차", placeholder="예: 1회", key="e_mock_round")
    with c_e2:
        e_mock_score = st.number_input("점수", min_value=0, max_value=100, value=80, step=5, key="e_mock_score")
    e_mock_memo = st.text_area("메모", placeholder="오답 노트", key="e_mock_memo_e", label_visibility="collapsed")
    
    if st.button(":material/save: 점수 저장", use_container_width=True, key="e_mock_btn"):
        sheet.worksheet("Mock").append_row([str(e_mock_date), "응급처치학개론", e_mock_round, e_mock_score, e_mock_memo])
        st.cache_data.clear()
        st.rerun()
        
    st.write("---")
    with st.expander("📋 모의고사 전체 기록 보기/관리"):
        manage_records("Mock", df_mock, "모의고사", "mock")

    st.write("<br>", unsafe_allow_html=True)
    if st.button(":material/sync: 전체 진도 클라우드 저장", use_container_width=True, key="sync_btn"):
        sheet.worksheet("Study").update_acell('A1', json.dumps(study_state, ensure_ascii=False))
        st.cache_data.clear()
        st.success("클라우드 동기화 완료!", icon=":material/cloud_done:")

# TAB 2: 러닝 기록
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        run_date = st.date_input("훈련 날짜", today_kst, key="run_date_in")
        weight = st.number_input("체중 (kg)", value=float(last_weight), step=0.1, key="run_weight_in")
        avg_hr = st.number_input("평균 심박 (bpm)", min_value=60, max_value=200, value=140, key="run_avghr_in")
        cadence = st.number_input("케이던스 (spm)", min_value=100, max_value=250, value=170, step=1, key="run_cadence_in")
    with c2:
        duty_type = st.selectbox("근무 패턴", ["데이", "이브닝", "나이트", "더블 (16시간)", "오프"], key="run_duty_in")
        vo2max = st.number_input("VO2 Max", value=float(last_vo2), step=0.1, key="run_vo2_in")
        max_hr = st.number_input("최대 심박 (bpm)", min_value=60, max_value=220, value=150, key="run_maxhr_in")

    shoe_used = st.selectbox("착용 러닝화", ["선택 안함", "아디다스 하이퍼부스트 런", "노바 블라스트 5", "아디제로 에보 SL (1)", "아디제로 에보 SL (2)", "클라우드 몬스터 3 하이퍼"], key="run_shoe_in")
    
    shoe_img_map = {
        "아디다스 하이퍼부스트 런": "hyperboost.png", 
        "노바 블라스트 5": "nova5.jpg", 
        "아디제로 에보 SL (1)": "evo1.png", 
        "아디제로 에보 SL (2)": "evo2.png", 
        "클라우드 몬스터 3 하이퍼": "cloudmonster.png"
    }
    if shoe_used != "선택 안함":
        img_filename = shoe_img_map.get(shoe_used)
        if img_filename and os.path.exists(img_filename): st.image(img_filename, width=300)

    target_hr = st.selectbox("훈련 타겟", ["150bpm 미만 (리커버리)", "159bpm 미만 (크루즈)", "자유 훈련"], key="run_target_in")
    condition = st.slider("피로도 (1:최악 ~ 5:최상)", 1, 5, 3, key="run_cond_in")
    with st.expander("특이사항"): 
        run_memo = st.text_area("메모", label_visibility="collapsed", key="run_memo_in")

    if st.button(":material/save: 러닝 기록 저장", use_container_width=True, key="run_save_btn"):
        if "150bpm" in target_hr and max_hr >= 150: st.error("심박 타겟 실패 (150 초과)", icon=":material/warning:")
        elif "159bpm" in target_hr and max_hr >= 160: st.error("심박 타겟 실패 (160 초과)", icon=":material/warning:")
        else: st.success("훈련 완료", icon=":material/check_circle:")
        sheet.worksheet("Run").append_row([str(run_date), duty_type, condition, weight, vo2max, shoe_used, target_hr, avg_hr, max_hr, cadence, run_memo])
        st.cache_data.clear()
        st.rerun()

    st.write("---")
    st.markdown("### :material/monitoring: 트렌드 분석")
    if not df_run.empty and '날짜' in df_run.columns:
        run_chart = df_run.copy()
        run_chart['날짜'] = pd.to_datetime(run_chart['날짜'], errors='coerce')
        run_chart = run_chart.dropna(subset=['날짜'])
        if not run_chart.empty:
            run_chart = run_chart.sort_values('날짜').set_index('날짜')
            if '체중' in run_chart.columns: st.line_chart(run_chart['체중'])
            if 'VO2Max' in run_chart.columns: st.line_chart(run_chart['VO2Max'])

    with st.expander("🏃‍♂️ 러닝 전체 기록 보기/관리"):
        manage_records("Run", df_run, "러닝", "run")

# TAB 3: 체력학원 기록
with tab3:
    df_gym = load_gym_data()
    if not df_gym.empty:
        st.markdown("#### 최근 측정 기록")
        last_grip, avg_grip = get_latest_and_avg(df_gym, '악력', 0)
        last_sit, avg_sit = get_latest_and_avg(df_gym, '좌전굴', 0)
        last_shut, avg_shut = get_latest_and_avg(df_gym, '왕오달', 0)
        gc1, gc2, gc3 = st.columns(3)
        gc1.metric("악력", f"{last_grip}kg", f"{last_grip - avg_grip:.1f}")
        gc2.metric("좌전굴", f"{last_sit}cm", f"{last_sit - avg_sit:.1f}")
        gc3.metric("왕오달", f"{last_shut}회", f"{last_shut - avg_shut:.1f}")
        st.write("---")

    gym_date = st.date_input("측정 날짜", today_kst, key="gym_date_tab3")
    
    st.markdown("#### 실시간 환산 점수")
    c_gym1, c_gym2 = st.columns(2)
    with c_gym1:
        grip = st.number_input("악력 (kg)", value=40.0, step=0.1, key="gym_grip_in")
        sit_reach = st.number_input("좌전굴 (cm)", value=10.0, step=0.1, key="gym_sit_in")
        shuttle = st.number_input("왕복오래달리기", value=40, step=1, key="gym_shut_in")
    with c_gym2:
        back_str = st.number_input("배근력 (kg)", value=150.0, step=0.1, key="gym_back_in")
        jump = st.number_input("제자리멀리뛰기 (cm)", value=200, step=1, key="gym_jump_in")
        situp = st.number_input("윗몸일으키기", value=40, step=1, key="gym_situp_in")
        
    total_score = get_score_grip(grip) + get_score_sit_reach(sit_reach) + get_score_shuttle(shuttle) + get_score_back(back_str) + get_score_jump(jump) + get_score_situp(situp)
    
    st.info(f"예상 총점: **{total_score}점** / 60점", icon=":material/military_tech:")
        
    with st.expander("강사 피드백"): 
        gym_memo = st.text_area("메모", label_visibility="collapsed", key="gym_memo_in")

    if st.button(":material/save: 체력 기록 저장", use_container_width=True, key="gym_save_btn"):
        sheet.worksheet("Gym").append_row([str(gym_date), grip, sit_reach, shuttle, jump, back_str, situp, gym_memo])
        st.cache_data.clear()
        st.rerun()

    st.write("---")
    st.markdown("### :material/show_chart: 성장 궤적")
    if not df_gym.empty and '날짜' in df_gym.columns:
        gym_chart = df_gym.copy()
        gym_chart['날짜'] = pd.to_datetime(gym_chart['날짜'], errors='coerce')
        gym_chart = gym_chart.dropna(subset=['날짜'])
        if not gym_chart.empty:
            gym_chart = gym_chart.sort_values('날짜').set_index('날짜')
            cols_gym1 = [c for c in ['악력', '배근력'] if c in gym_chart.columns]
            if cols_gym1: st.line_chart(gym_chart[cols_gym1])
            cols_gym2 = [c for c in ['좌전굴', '제멀'] if c in gym_chart.columns]
            if cols_gym2: st.line_chart(gym_chart[cols_gym2])
            cols_gym3 = [c for c in ['왕오달', '윗몸'] if c in gym_chart.columns]
            if cols_gym3: st.line_chart(gym_chart[cols_gym3])

    with st.expander("🏋️ 체력 전체 기록 보기/관리"):
        manage_records("Gym", df_gym, "체력", "gym")

# TAB 4: 리포트 (피드백)
with tab4:
    st.markdown("### :material/share: 공유용 리포트")
    try: feedback_memo = run_memo
    except NameError: feedback_memo = ""
    safe_duty = duty_type if 'duty_type' in locals() else "-"
    safe_weight = weight if 'weight' in locals() else "-"
    safe_vo2 = vo2max if 'vo2max' in locals() else "-"
    safe_shoe = shoe_used if 'shoe_used' in locals() else "-"
    safe_avg = avg_hr if 'avg_hr' in locals() else "0"
    safe_max = max_hr if 'max_hr' in locals() else "0"
    safe_cadence = cadence if 'cadence' in locals() else "0"

    st.code(f"""[TRAINING REPORT]
DATE: {today_kst}
DUTY: {safe_duty}
BODY: {safe_weight}kg / VO2Max: {safe_vo2}
GEAR: {safe_shoe}
HR: AVG {safe_avg}bpm / MAX {safe_max}bpm
CADENCE: {safe_cadence}spm
NOTE: {feedback_memo}""", language="markdown")

# TAB 5: 플래너
with tab5:
    st.markdown("### :material/event_note: 마스터 플랜")
    df_plan = load_plan_data()

    # --- 1. 월간 목표 ---
    st.markdown("#### 월간 미션")
    c_m1, c_m2 = st.columns([1, 2])
    with c_m1:
        m_date = st.date_input("월 선택", today_kst, key="m_date")
        m_str = m_date.strftime("%Y년 %m월")
    df_m = df_plan[(df_plan['구분'] == '월간') & (df_plan['지정일'] == m_str)]
    m_val = df_m.iloc[-1]['내용'] if not df_m.empty else ""
    with c_m2: m_goal = st.text_area("내용", value=m_val, label_visibility="collapsed", key="m_goal_in")
    if st.button(":material/save: 월간 저장", key="btn_m", use_container_width=True):
        sheet.worksheet("Plan").append_row(["월간", m_str, m_goal])
        st.cache_data.clear()
        st.rerun()

    st.write("---")

    # --- 2. 주간 목표 ---
    st.markdown("#### 주간 미션")
    w_dates = st.date_input("기간 선택", [today_kst, today_kst], key="w_date")
    if len(w_dates) == 2: w_str = f"{w_dates[0].strftime('%Y/%m/%d')} ~ {w_dates[1].strftime('%Y/%m/%d')}"
    else: w_str = f"{w_dates[0].strftime('%Y/%m/%d')} ~ (-)"
    df_w = df_plan[(df_plan['구분'] == '주간') & (df_plan['지정일'] == w_str)]
    w_val = df_w.iloc[-1]['내용'] if not df_w.empty else ""
    w_goal = st.text_area("내용", value=w_val, label_visibility="collapsed", key="w_goal_in")
    if st.button(":material/save: 주간 저장", key="btn_w", use_container_width=True):
        sheet.worksheet("Plan").append_row(["주간", w_str, w_goal])
        st.cache_data.clear()
        st.rerun()

    st.write("---")

    # --- 3. 일간 체크리스트 ---
    st.markdown("#### 데일리 체크")
    d_date = st.date_input("날짜 선택", today_kst, key="d_date")
    d_str = d_date.strftime("%Y-%m-%d")
    df_d = df_plan[(df_plan['구분'] == '일간') & (df_plan['지정일'] == d_str)]
    try: daily_tasks = json.loads(df_d.iloc[-1]['내용']) if not df_d.empty else {}
    except: daily_tasks = {}
    
    tasks, checks = [], []
    existing_keys = list(daily_tasks.keys())
    
    for i in range(5):
        dt = existing_keys[i] if i < len(existing_keys) else ""
        dc = daily_tasks.get(dt, False) if dt else False
        
        c_chk, c_txt = st.columns([1, 8])
        with c_chk: is_done = st.checkbox("완료", value=dc, key=f"chk_{i}", label_visibility="collapsed")
        with c_txt: task_name = st.text_input(f"할 일", value=dt, label_visibility="collapsed", key=f"task_{i}", placeholder="할 일 입력")
        
        if task_name.strip():
            tasks.append(task_name.strip())
            checks.append(is_done)
            
    completed, total = sum(checks), len(tasks)
    prog = completed / total if total > 0 else 0.0
    
    st.progress(prog)
    st.caption(f"달성률: {int(prog * 100)}% ({completed}/{total})")
    
    if st.button(":material/save: 체크리스트 저장", key="btn_d", use_container_width=True):
        sheet.worksheet("Plan").append_row(["일간", d_str, json.dumps({tasks[i]: checks[i] for i in range(len(tasks))}, ensure_ascii=False)])
        st.cache_data.clear()
        st.rerun()

    st.write("---")
    with st.expander("📅 플래너 전체 기록 보기/관리"):
        manage_records("Plan", df_plan, "플래너", "plan")
