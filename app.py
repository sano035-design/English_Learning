import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re
import requests

# 1. API Key Setup
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


# 4. YouTube transcript helper
def get_youtube_transcript(url):
    """Extract video ID from URL and fetch transcript. Returns transcript text or None."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptList
        # Extract video ID from various YouTube URL formats
        match = re.search(r"(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})", url)
        if not match:
            return None
        video_id = match.group(1)

        # List all available transcripts and pick the best one automatically
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        # Priority 1: manually created English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            pass
        # Priority 2: auto-generated English transcript
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                pass
        # Priority 3: any available transcript (any language)
        if not transcript:
            try:
                transcript = next(iter(transcript_list))
            except Exception:
                return None

        data = transcript.fetch()
        full_text = " ".join([t['text'] for t in data])
        return full_text[:3000]
    except Exception:
        return None


# 5. YouTube video title helper (fallback when transcript is unavailable)
def get_youtube_title(url):
    """Fetch the YouTube video title from the page metadata."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        match = re.search(r'<title>(.*?) - YouTube</title>', response.text)
        if match:
            return match.group(1).strip()
        # Fallback: og:title meta tag
        match = re.search(r'property="og:title" content="(.*?)"', response.text)
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


# 6. UI Layout
st.title("🤖 Daniel's English AI")

col1, col2 = st.columns([1, 2])
with col1:
    input_date = st.date_input("Date", datetime.now().date())
with col2:
    video_url = st.text_input("Video Source (link)")

new_sentence = st.text_input("Enter an English sentence")

if st.button("🪄 Interpret"):
    if new_sentence:
        try:
            # Fetch YouTube transcript if URL is provided
            transcript_context_kr = ""

            if video_url and "youtu" in video_url:
                with st.spinner("📺 Fetching video transcript for context..."):
                    transcript = get_youtube_transcript(video_url)
                if transcript:
                    transcript_context_kr = f"\n\n[참고: 아래는 이 문장이 나온 유튜브 영상의 실제 자막입니다. 이 맥락 속에서 문장을 설명해줘]\n\"{transcript}\""
                    st.info("✅ Video transcript loaded! Explanation will use the actual video context.")
                else:
                    # Fallback: fetch video title for context
                    video_title = get_youtube_title(video_url)
                    if video_title:
                        transcript_context_kr = f"\n\n참고: 이 문장은 유튜브 영상 \"{video_title}\"에서 나온 것입니다. 이 영상의 제목과 주제를 고려해서 맥락을 설명해줘."
                        transcript_context_en = f"\n\nContext: This sentence is from a YouTube video titled \"{video_title}\". Use what you know about this title/topic to provide relevant context."
                        st.info(f"📌 Using video title as context: **{video_title}**")
                    else:
                        transcript_context_kr = f"\n\n참고: 이 문장은 다음 유튜브 영상에서 나온 것입니다: {video_url}\n자막을 가져올 수 없어서 일반적인 맥락으로 설명해줘."
                        st.warning("⚠️ Could not load transcript or title. Using general context instead.")
            elif video_url:
                transcript_context_kr = f"\n\n참고: 이 문장은 다음 출처에서 나온 것입니다: {video_url}\n출처의 주제나 분위기를 고려해서 설명해줘."

            # Korean prompt
            korean_prompt = f"""다음 영어 문장에 대해 아래 형식으로 설명해줘:{transcript_context_kr}

문장: '{new_sentence}'

1. 📌 상황과 맥락: 이 문장이 어떤 상황에서 쓰이는지 2~3줄로 설명해줘.
2. 🧠 영어식 사고방식: 문장의 각 부분을 영어 원어민의 시각으로 분석해줘. (예: 주어/동사/표현 의미 등)
3. 💬 예문: 비슷한 상황에서 쓸 수 있는 예문을 하나 만들어줘."""

            with st.spinner("🤖 AI is analyzing..."):
                korean_result = model.generate_content(korean_prompt).text

            st.session_state['date'] = input_date.strftime("%Y-%m-%d")
            st.session_state['video'] = video_url
            st.session_state['sentence'] = new_sentence
            st.session_state['result_korean'] = korean_result

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a sentence first.")

if 'result_korean' in st.session_state:
    st.markdown("---")
    st.markdown(f"**🗓️ Date:** {st.session_state['date']}")
    if st.session_state['video']:
        st.markdown(f"[🔗 Video Source]({st.session_state['video']})")
    st.info(f"🗣️ **Sentence:** {st.session_state['sentence']}\n\n💡 **Interpretation:**\n{st.session_state['result_korean']}")

    if st.button("💾 Save to Sheet"):
        client = get_gsheet_client()
        if client:
            try:
                sh = client.open("English_Practice_DB").get_worksheet(0)
                sh.append_row([
                    st.session_state['date'],
                    st.session_state['sentence'],
                    st.session_state['result_korean'],  # Korean only ✅
                    st.session_state['video']
                ])
                st.success("Saved successfully!")
            except Exception as e:
                st.error(f"Save error: {e}")