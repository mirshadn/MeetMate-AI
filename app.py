import streamlit as st
import os
import json
import time
import yt_dlp
from pathlib import Path
from groq import Groq
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 🔧 CONFIGURATION & KEYS
# ==========================================
GROQ_API_KEY = "REPLACE_WITH_ENV_VAR"
GROQ_MODEL = "llama-3.3-70b-versatile"

CEO_EMAIL = "srujanj246@gmail.com"
SENDER_EMAIL = "mdirshad6788@gmail.com"
SENDER_PASSWORD = "nsje qgnb lrld sfei" 

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ==========================================
# ⚙️ 1. DOWNLOADER
# ==========================================
def get_audio_from_youtube(url):
    ydl_opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "format": "worstaudio[ext=m4a]/worst", 
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            base = str(DOWNLOAD_DIR / info['id'])
            if not os.path.exists(filename):
                for ext in ['.m4a', '.webm', '.mp3', '.opus']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            return filename, info.get('title', 'Unknown'), size_mb
    except Exception as e:
        return None, str(e), 0

# ==========================================
# ⚙️ 2. TRANSCRIBER
# ==========================================
def transcribe_audio(file_path):
    client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(timeout=None))
    try:
        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3",
                response_format="json"
            )
        return transcription.text
    except Exception as e:
        return None

# ==========================================
# ⚙️ 3. INTELLIGENCE ENGINE
# ==========================================
def generate_intelligence(text, title):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"""
    Analyze this meeting/video transcript titled "{title}".
    
    Output STRICT JSON (No markdown):
    {{
        "summary": "Executive summary (professional business tone)",
        "key_decisions": ["Point 1", "Point 2", "Point 3"],
        "action_items": [
            {{"assignee": "Person/Team (Use 'All' if generic)", "task": "Action detail", "due": "Estimated Time"}}
        ],
        "sentiment_score": "Positive/Neutral/Critical",
        "efficiency": 92
    }}
    """
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": f"{prompt}\n{text}"}],
            model=GROQ_MODEL,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except:
        return None

# ==========================================
# ⚙️ 4. RICH HTML EMAIL (CEO GRADE)
# ==========================================
def send_email(report, url):
    
    # A. Build Decision List
    decisions_html = "".join([f"<li style='margin-bottom: 5px;'>✅ {d}</li>" for d in report.get('key_decisions', [])])
    
    # B. Build Action Item TABLE
    actions_rows = ""
    for t in report.get('action_items', []):
        actions_rows += f"""
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd; color: #333;"><b>{t['assignee']}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; color: #555;">{t['task']}</td>
            <td style="padding: 12px; border: 1px solid #ddd; color: #d9534f; font-weight: bold;">{t.get('due', 'ASAP')}</td>
        </tr>
        """

    # C. Full HTML Body (Blue Theme)
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px;">
        
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); overflow: hidden;">
            
            <!-- HEADER -->
            <div style="background-color: #0056b3; color: white; padding: 25px; text-align: center;">
                <h1 style="margin:0; font-size: 24px;">🚀 MeetMate Intelligence Report</h1>
                <p style="margin:5px 0 0; opacity: 0.9;">Automated Meeting Minutes</p>
            </div>

            <!-- METRICS BAR -->
            <div style="background-color: #eef2f7; padding: 15px; border-bottom: 1px solid #ddd; text-align: center; display: flex; justify-content: space-around;">
                <span style="margin: 0 10px;">📊 <b>Efficiency:</b> {report.get('efficiency')}/100</span>
                <span style="margin: 0 10px;">🧠 <b>Tone:</b> {report.get('sentiment_score')}</span>
            </div>

            <!-- MAIN CONTENT -->
            <div style="padding: 25px;">
                
                <p style="color: #777; font-size: 12px; text-align: right;">Source: <a href="{url}">Watch Recording</a></p>

                <h3 style="color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 10px;">📝 Executive Summary</h3>
                <div style="background-color: #fff8e1; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; color: #555;">
                    {report.get('summary')}
                </div>

                <h3 style="color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 10px;">📌 Key Decisions & Takeaways</h3>
                <ul style="padding-left: 20px;">
                    {decisions_html}
                </ul>

                <br>

                <h3 style="color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 10px;">🚀 Action Items</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #0056b3; color: white;">
                            <th style="padding: 10px; text-align: left; width: 25%;">Who</th>
                            <th style="padding: 10px; text-align: left; width: 55%;">What</th>
                            <th style="padding: 10px; text-align: left; width: 20%;">Deadline</th>
                        </tr>
                    </thead>
                    <tbody>
                        {actions_rows}
                    </tbody>
                </table>

            </div>
            
            <!-- FOOTER -->
            <div style="background-color: #333; color: #999; padding: 15px; text-align: center; font-size: 12px;">
                Generated by MeetMate AI for Hackathon Demo 2025
            </div>

        </div>
    </body>
    </html>
    """
    
    status = "Simulated"
    try:
        # REAL EMAIL SEND CHECK
        if len(SENDER_PASSWORD) > 12 and "7022" not in SENDER_PASSWORD:
            msg = MIMEMultipart()
            msg['Subject'] = f"Meeting Summary: {report.get('summary')[:40]}..."
            msg['From'] = SENDER_EMAIL
            msg['To'] = CEO_EMAIL
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, CEO_EMAIL, msg.as_string())
            server.quit()
            status = "Sent ✅"
        else:
            status = "Simulated (Auth Block)"
    except:
        status = "Delivery Failed"
        
    return status, body

# ==========================================
# 🎨 FRONTEND UI
# ==========================================

st.set_page_config(page_title="MeetMate AI", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #2E86C1; color: white; border-radius: 5px; width: 100%; font-size: 18px;}
    h1 { color: #FAFAFA; }
    </style>
    """, unsafe_allow_html=True)

# Header
col1, col2 = st.columns([1, 15])
with col1:
    st.write("# ⚡")
with col2:
    st.title("MeetMate AI")
    st.write("### Real-Time Meeting Intelligence & Decision Engine")

st.divider()

# Input
link = st.text_input("🔗 Paste Meeting Video URL (YouTube / Generic MP4)", placeholder="https://youtube.com/watch?v=...")

if st.button("Analyze Meeting Now 🚀"):
    if not link:
        st.error("⚠️ Please enter a valid video link.")
    else:
        # 1. Download
        status_bar = st.empty()
        progress = st.progress(0)
        
        status_bar.info(f"⏳ Connecting to Video stream...")
        audio_path, video_title, size_mb = get_audio_from_youtube(link)
        
        if not audio_path:
            status_bar.error("❌ Failed to download. Link must be Public/Unlisted (No Login).")
        else:
            progress.progress(25)
            
            # 2. Transcribe
            status_bar.info("🎙️ Transcribing Audio...")
            transcript = transcribe_audio(audio_path)
            
            if not transcript:
                status_bar.error("❌ Transcription failed.")
            else:
                progress.progress(50)
                
                # 3. Intelligence
                status_bar.info("🧠 Generative AI Analysis...")
                report = generate_intelligence(transcript, video_title)
                
                if not report:
                    status_bar.error("❌ AI Analysis failed.")
                else:
                    progress.progress(80)
                    
                    # 4. Email & Render
                    status_bar.info("📧 Creating Executive HTML Email...")
                    email_status, email_body = send_email(report, link)
                    
                    progress.progress(100)
                    time.sleep(0.5)
                    progress.empty()
                    status_bar.success("✅ Process Complete!")
                    
                    st.divider()
                    
                    # --- DASHBOARD ---
                    # Metrics Row
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Efficiency Score", f"{report.get('efficiency')}/100")
                    c2.metric("Sentiment", report.get('sentiment_score'))
                    c3.metric("Key Decisions", len(report.get('key_decisions', [])))
                    c4.metric("Email Delivery", email_status)
                    
                    # Main Split
                    left, right = st.columns([1.5, 1.5])
                    
                    with left:
                        st.subheader("📝 Summary")
                        st.info(report.get('summary'))
                        
                        st.subheader("📌 Key Decisions")
                        for d in report.get('key_decisions', []):
                            st.write(f"✅ {d}")

                    with right:
                        st.subheader("🚀 Action Plan")
                        # Iterate and make neat cards for tasks
                        for t in report.get('action_items', []):
                            with st.container():
                                st.markdown(f"""
                                <div style="padding:10px; border-radius:5px; border:1px solid #444; background-color:#222; margin-bottom:10px;">
                                    <strong style="color:#FF4B4B">{t['assignee']}</strong><br>
                                    {t['task']}<br>
                                    <small>🕒 {t.get('due','ASAP')}</small>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # 5. EMAIL PREVIEW (Important for the demo)
                    st.divider()
                    with st.expander("📨 See What Was Sent to CEO (Email Preview)", expanded=True):
                        st.components.v1.html(email_body, height=600, scrolling=True)
