import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. API 키 설정 (보안: Streamlit Secrets에서 불러오기)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("보안 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일 또는 Streamlit Cloud의 Secrets를 확인하세요.")
    st.stop()

# 2. AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 구글 시트 인증 (비밀번호 보안화)
def get_gsheet_client():
    try:
        # 클라우드 배포용: Streamlit 비밀금고(Secrets)에 구글 인증정보가 있다면 사용
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        # 로컬 테스트용: 컴퓨터에 있는 key.json 파일을 사용
        else:
            creds = Credentials.from_service_account_file('key.json', 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"구글 인증 오류: {e}")
        return None

# 4. 화면 구성
st.title("🤖 Daniel's English AI")

# 입력 칸 구성: 날짜, 영상 소스, 문장
col1, col2 = st.columns([1, 2])
with col1:
    input_date = st.date_input("날짜", datetime.now().date())
with col2:
    video_url = st.text_input("영상 소스 (링크)")

new_sentence = st.text_input("영어 문장 입력")

if st.button("🪄 해석하기"):
    if new_sentence:
        try:
            # AI 호출: 해석과 상황 설명만 간단하게 요청하는 프롬프트
            prompt = f"다음 영어 문장의 의미와 사용되는 상황을 아주 간단하게 1~2줄로 설명해줘: '{new_sentence}'"
            response = model.generate_content(prompt)
            
            st.session_state['date'] = input_date.strftime("%Y-%m-%d")
            st.session_state['video'] = video_url
            st.session_state['sentence'] = new_sentence
            st.session_state['result'] = response.text
        except Exception as e:
            st.error(f"오류 발생: {e}")

if 'result' in st.session_state:
    st.markdown("---")
    # 날짜와 연결된 결과를 보기 좋게 출력
    st.markdown(f"**🗓️ 날짜:** {st.session_state['date']}")
    if st.session_state['video']:
        st.markdown(f"[🔗 영상 소스 링크]({st.session_state['video']})")
    st.info(f"🗣️ **문장:** {st.session_state['sentence']}  \n\n💡 **해석/설명:** {st.session_state['result']}")

    if st.button("💾 시트에 저장"):
        client = get_gsheet_client()
        if client:
            try:
                sh = client.open("English_Practice_DB").get_worksheet(0)
                # 영상 소스도 시트에 함께 저장되도록 추가
                sh.append_row([
                    st.session_state['date'], 
                    st.session_state['sentence'], 
                    st.session_state['result'],
                    st.session_state['video']
                ])
                st.success("저장 완료!")
            except Exception as e:
                st.error(f"저장 오류: {e}")