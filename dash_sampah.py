import threading
import requests
import streamlit as st
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv

# Load file .env jika running secara lokal
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("8402326442:AAEHf63VFu1-dSTsQ0ywkP0rMv95fN93-D8")
TELEGRAM_CHAT_ID = os.getenv("5187138976")


# --- KONFIGURASI TELEGRAM & FIREBASE ---
TELEGRAM_BOT_TOKEN = "8402326442:AAEHf63VFu1-dSTsQ0ywkP0rMv95fN93-D8"
TELEGRAM_CHAT_ID = "5187138976"
TELEGRAM_BOT_URL = "https://t.me/maaury_bot"
STREAMLIT_URL = "https://trashbinfuzzy.streamlit.app/"  # Sesuaikan jika sudah di-deploy (misal: Streamlit Community Cloud)
FIREBASE_KEY = "UVmxCY8ZivzNaSTMRU1bJJcTHRiy2oOjEMsOxw1U"

# --- INISIALISASI FIREBASE ADMIN SDK ---
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["FIREBASE_KEY"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://pemilah-sampah-otomatis-c8d2e-default-rtdb.firebaseio.com/'
    })

# --- FUNGSI BACA DATA FIREBASE ---
def load_firebase_data():
    ref = db.reference('/trash_bin')
    return ref.get() or {}

def get_trash_status_text():
    """Fungsi helper untuk format status teks yang dikirim ke Telegram"""
    data = load_firebase_data()
    cap_org = data.get("kapasitas_organik", 0)
    cap_anorg = data.get("kapasitas_anorganik", 0)
    trash_type = data.get("sampah_terakhir", "Belum ada")
    
    status_msg = (
        "📊 *STATUS TEMPAT SAMPAH REALTIME*\n\n"
        f"🌱 *Organik:* {cap_org}%\n"
        f"📦 *Anorganik:* {cap_anorg}%\n"
        f"🔍 *Deteksi Terakhir:* {trash_type}\n\n"
    )
    if cap_org >= 90 or cap_anorg >= 90:
        status_msg += "⚠️ *PERINGATAN:* Tempat sampah hampir/sudah penuh!"
    else:
        status_msg += "✅ *Status:* Kapasitas masih aman."
    
    return status_msg

def send_telegram_message(message):
    """Fungsi kirim notifikasi manual dari Streamlit"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Gagal mengirim pesan Telegram: {e}")
        return False

# --- THREAD BOT LISTENER TELEGRAM ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn_check = InlineKeyboardButton("📊 Cek Kapasitas Sampah", callback_data="check_status")
    btn_dashboard = InlineKeyboardButton("🌐 Buka Web Dashboard", url=STREAMLIT_URL)
    markup.add(btn_check)
    markup.add(btn_dashboard)

    welcome_text = (
        f"Halo *{message.from_user.first_name}*! 👋\n\n"
        "Selamat datang di Bot Monitoring *Trash Bin*.\n"
        "Pilih menu di bawah ini untuk melihat status atau membuka dashboard:"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def callback_check(call):
    status_text = get_trash_status_text()
    
    markup = InlineKeyboardMarkup()
    btn_check = InlineKeyboardButton("🔄 Refresh Status", callback_data="check_status")
    btn_dashboard = InlineKeyboardButton("🌐 Buka Web Dashboard", url=STREAMLIT_URL)
    markup.add(btn_check)
    markup.add(btn_dashboard)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=status_text,
        parse_mode="Markdown",
        reply_markup=markup
    )

# Jalankan polling bot di background thread agar Streamlit tidak terblokir
@st.cache_resource
def start_bot_thread():
    thread = threading.Thread(target=bot.infinity_polling, daemon=True)
    thread.start()
    return thread

start_bot_thread()


# --- TAMPILAN DASHBOARD STREAMLIT ---
st.set_page_config(page_title="Smart Trash Bin - Realtime", page_icon="♻️", layout="wide")

# STYLESHEET BADGE
st.markdown("""
<style>
    .badge-green { background-color: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
    .badge-red { background-color: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
    .badge-blue { background-color: #3b82f6; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

data = load_firebase_data()

# HEADER CARD
with st.container(border=True):
    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
    with col_h1:
        st.title("♻️ Realtime Monitoring Pemilah Sampah")
        st.caption("Terhubung dengan ESP32, Firebase & Telegram Bot")
    with col_h2:
        st.write("")
        st.link_button("💬 Buka Bot Telegram", TELEGRAM_BOT_URL, use_container_width=True)
    with col_h3:
        st.write("")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

# ROW 1: STATUS REALTIME
st.subheader("📡 Status Sensor & Servo")
col1, col2 = st.columns(2)

trash_type = data.get("sampah_terakhir", "Tidak Ada Data")
servo_pos = data.get("posisi_servo", "Standby")

with col1:
    with st.container(border=True):
        st.caption("DETEKSI SAMPAH TERAKHIR")
        st.markdown(f"### 📦 {trash_type}")
        st.markdown('<span class="badge-blue">Realtime Sync</span>', unsafe_allow_html=True)

with col2:
    with st.container(border=True):
        st.caption("POSISI SERVO MOTOR")
        st.markdown(f"### ⚙️ {servo_pos}")
        st.markdown('<span class="badge-blue">Pin 25</span>', unsafe_allow_html=True)

st.divider()

# ROW 2: KAPASITAS TONG SAMPAH
st.subheader("📊 Kapasitas Tempat Sampah")
col_org, col_anorg = st.columns(2)

cap_org = data.get("kapasitas_organik", 0)
cap_anorg = data.get("kapasitas_anorganik", 0)

with col_org:
    with st.container(border=True):
        st.markdown("### 🌱 Tempat Sampah Organik")
        st.caption("Ultrasonic 1 (Trig: 5, Echo: 18)")
        st.metric("Tingkat Kepenuhan", f"{cap_org}%")
        st.progress(cap_org / 100.0)
        
        if cap_org >= 90:
            st.markdown('<span class="badge-red">⚠️ PENUH (Notif Telegram Terkirim)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-green">Aman</span>', unsafe_allow_html=True)

with col_anorg:
    with st.container(border=True):
        st.markdown("### 📦 Tempat Sampah Anorganik")
        st.caption("Ultrasonic 2 (Trig: 33, Echo: 32)")
        st.metric("Tingkat Kepenuhan", f"{cap_anorg}%")
        st.progress(cap_anorg / 100.0)
        
        if cap_anorg >= 90:
            st.markdown('<span class="badge-red">⚠️ PENUH (Notif Telegram Terkirim)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-green">Aman</span>', unsafe_allow_html=True)

st.divider()

# ROW 3: FITUR UJI COBA TELEGRAM
st.subheader("🔔 Uji Coba Notifikasi Telegram")
with st.container(border=True):
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        custom_msg = st.text_input("Pesan Tes Notifikasi", "⚠️ Tes Peringatan: Tempat sampah mendekati kapasitas penuh!")
    with col_t2:
        st.write("")
        st.write("")
        if st.button("📤 Kirim Ke Telegram", use_container_width=True):
            if send_telegram_message(custom_msg):
                st.success("Notifikasi berhasil dikirim!")
            else:
                st.error("Gagal mengirim notifikasi.")