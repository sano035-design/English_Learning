import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. API Key Setup (Security: Load from Streamlit Secrets)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("API key not found. Please check your .streamlit/secrets.toml file or Streamlit Cloud Secrets.")
    st.stop()

# 2. AI Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


# 3. Google Sheet Authentication
def get_gsheet_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        else:
            creds = Credentials.from_service_account_file('key.json',
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google authentication error: {e}")
        return None

# 4. UI Layout
st.title("🤖 Daniel's English AI")

# Input section: date, video source, sentence
col1, col2 = st.columns([1, 2])
with col1:
    input_date = st.date_input("Date", datetime.now().date())
with col2:
    video_url = st.text_input("Video Source (link)")

new_sentence = st.text_input("Enter an English sentence")

if st.button("🪄 Interpret"):
    if new_sentence:
        try:
            # Step 1: Get Korean interpretation
            korean_prompt = f"다음 영어 문장의 의미와 사용되는 상황을 아주 간단하게 1~2줄로 설명해줘: '{new_sentence}'"
            korean_response = model.generate_content(korean_prompt)
            korean_result = korean_response.text

            # Step 2: Translate that Korean result into English
            english_prompt = f"Translate the following Korean explanation into English in 1-2 sentences:\n\n{korean_result}"
            english_response = model.generate_content(english_prompt)
            english_result = english_response.text

            st.session_state['date'] = input_date.strftime("%Y-%m-%d")
            st.session_state['video'] = video_url
            st.session_state['sentence'] = new_sentence
            st.session_state['result_korean'] = korean_result      # saved to sheet
            st.session_state['result_english'] = english_result    # display only
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a sentence first.")

if 'result_korean' in st.session_state:
    st.markdown("---")
    st.markdown(f"**🗓️ Date:** {st.session_state['date']}")
    if st.session_state['video']:
        st.markdown(f"[🔗 Video Source]({st.session_state['video']})")
    st.info(f"🗣️ **Sentence:** {st.session_state['sentence']}\n\n💡 **Interpretation (Korean):**\n{st.session_state['result_korean']}")
    st.success(f"🌏 **Interpretation (English):**\n{st.session_state['result_english']}")

    if st.button("💾 Save to Sheet"):
        client = get_gsheet_client()
        if client:
            try:
                sh = client.open("English_Practice_DB").get_worksheet(0)
                # Only save Korean interpretation — NOT the English translation
                sh.append_row([
                    st.session_state['date'],
                    st.session_state['sentence'],
                    st.session_state['result_korean'],  # Korean only ✅
                    st.session_state['video']
                ])
                st.success("Saved successfully!")
            except Exception as e:
                st.error(f"Save error: {e}")