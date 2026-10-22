import json  # <--- DITAMBAHKAN (mencegah NameError pada json.loads)
import os
import threading
import time  # <--- DITAMBAHKAN (mencegah NameError pada time.time)
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
import requests
import streamlit as st
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from streamlit_autorefresh import st_autorefresh

# Load file .env jika running secara lokal
load_dotenv()

# --- KONFIGURASI TELEGRAM & FIREBASE ---
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8402326442:AAEHf63VFu1-dSTsQ0ywkP0rMv95fN93-D8"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5187138976")
TELEGRAM_BOT_URL = "https://t.me/maaury_bot"
STREAMLIT_URL = "https://trashbinfuzzy.streamlit.app/"

# --- INISIALISASI FIREBASE ADMIN SDK ---
if not firebase_admin._apps:
    key_dict = None

    # 1. Cek jika FIREBASE_KEY ada di st.secrets sebagai string JSON
    if "FIREBASE_KEY" in st.secrets:
        key_dict = json.loads(st.secrets["FIREBASE_KEY"])

    # 2. Cek jika firebase_key ada di st.secrets sebagai dict/TOML table
    elif "firebase_key" in st.secrets:
        key_dict = dict(st.secrets["firebase_key"])
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace(
                "\\n", "\n"
            )

    # 3. Fallback jika running di lokal (dan file json memang ada)
    elif os.path.exists("serviceAccountKey.json"):
        with open("serviceAccountKey.json") as f:
            key_dict = json.load(f)

    # Jika kredensial berhasil dimuat
    if key_dict:
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(
            cred,
            {
                "databaseURL": "https://pemilah-sampah-otomatis-c8d2e-default-rtdb.firebaseio.com/"
            },
        )
    else:
        st.error(
            "Kredensial Firebase tidak ditemukan! Periksa konfigurasi Secrets di Streamlit Cloud."
        )

ref = db.reference("/")

# --- FUNGSI BACA DATA FIREBASE ---
@st.cache_data(ttl=2)
def load_firebase_data():
    """Baca data ESP32 dari Firebase, sekaligus tandai apakah koneksi berhasil."""
    try:
        tong = db.reference("/Tong_Sampah").get() or {}
        klasifikasi = db.reference("/Klasifikasi_Terakhir").get() or {}
        ts = db.reference("/terakhir_update").get()

        if ts is not None:
            ts = float(ts)
            if ts > 1e11:  # timestamp Firebase dalam milidetik
                ts = ts / 1000.0

        org = tong.get("Organik", {})
        anorg = tong.get("Anorganik", {})

        return {
            "firebase_ok": True,
            "kapasitas_organik": int(org.get("kapasitas_persen", 0)),
            "kapasitas_anorganik": int(anorg.get("kapasitas_persen", 0)),
            "ultra_organik": "kapasitas_persen" in org,
            "ultra_anorganik": "kapasitas_persen" in anorg,
            "sampah_terakhir": klasifikasi.get("kategori", "Belum ada"),
            "terakhir_update": ts,
        }
    except Exception as e:
        print(f"Gagal memuat data dari Firebase: {e}")
        return {"firebase_ok": False}

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
st.set_page_config(page_title="Trash Bin", page_icon="♻️", layout="wide")

st_autorefresh(interval=2000, key="auto_refresh")  # refresh tiap 3 detik

st.markdown("""
<style>
    :root {
        --hijau: #2e7d32;
        --hijau-muda: #e8f5e9;
        --kuning: #fbc02d;
        --kuning-tua: #8a6d00;
        --kuning-muda: #fff8e1;
        --merah: #e53935;
    }

    .stApp { background-color: #ffffff; }
    .block-container { padding-top: 2rem; max-width: 1000px; }
    h1 { color: var(--hijau) !important; }

    /* CARD ORGANIK - HIJAU */
    .st-key-card_organik {
        background-color: var(--hijau-muda);
        border: 2px solid var(--hijau) !important;
        border-radius: 16px !important;
        padding: 0.5rem 1rem;
    }
    .st-key-card_organik h3,
    .st-key-card_organik [data-testid="stMetricValue"] { color: var(--hijau) !important; }
    .st-key-card_organik .stProgress > div > div > div { background-color: #c8e6c9; }
    .st-key-card_organik .stProgress > div > div > div > div { background-color: var(--hijau); }

    /* CARD ANORGANIK - KUNING */
    .st-key-card_anorganik {
        background-color: var(--kuning-muda);
        border: 2px solid var(--kuning) !important;
        border-radius: 16px !important;
        padding: 0.5rem 1rem;
    }
    .st-key-card_anorganik h3,
    .st-key-card_anorganik [data-testid="stMetricValue"] { color: var(--kuning-tua) !important; }
    .st-key-card_anorganik .stProgress > div > div > div { background-color: #ffecb3; }
    .st-key-card_anorganik .stProgress > div > div > div > div { background-color: var(--kuning); }

    /* Card deteksi terakhir */
    .st-key-card_deteksi {
        border: 1px solid #e5e7eb !important;
        border-radius: 16px !important;
    }

    /* Tombol */
    .stButton > button, .stLinkButton > a {
        background-color: var(--kuning) !important;
        color: #1b1b1b !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover, .stLinkButton > a:hover {
        background-color: #f9a825 !important;
        color: #000 !important;
    }

    /* Badge */
    .badge-green  { background-color: #ffffff; color: var(--hijau); padding: 4px 14px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
    .badge-yellow { background-color: #ffffff; color: var(--kuning-tua); padding: 4px 14px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
    .badge-red    { background-color: #ffebee; color: var(--merah); padding: 4px 14px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }

    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

data = load_firebase_data()
cap_org = data.get("kapasitas_organik", 0)
cap_anorg = data.get("kapasitas_anorganik", 0)
last_trash = data.get("sampah_terakhir", "Belum ada")
last_seen = data.get("terakhir_update")  # epoch detik, dikirim oleh ESP32

# --- POP UP STATUS WIFI ---
# --- STATUS KONEKSI ---
WIFI_TIMEOUT = 30  # detik; lewat dari ini dianggap ESP32 offline

firebase_ok = data.get("firebase_ok", False)

if last_seen is None:
    esp_status = "unknown"
elif time.time() - float(last_seen) <= WIFI_TIMEOUT:
    esp_status = "online"
else:
    esp_status = "offline"

# Pop up hanya muncul saat pertama dibuka atau saat status berubah
if st.session_state.get("firebase_ok") != firebase_ok:
    st.session_state["firebase_ok"] = firebase_ok
    if firebase_ok:
        st.toast("Web terhubung ke Firebase", icon="✅")
    else:
        st.toast("Web gagal terhubung ke Firebase", icon="❌")

if st.session_state.get("esp_status") != esp_status:
    st.session_state["esp_status"] = esp_status
    if esp_status == "online":
        st.toast("ESP32 online, data masuk ke Firebase", icon="✅")
    elif esp_status == "offline":
        st.toast("ESP32 offline, tidak ada data baru", icon="❌")
    else:
        st.toast("ESP32 belum pernah mengirim data", icon="⚠️")


def status_badge(label, kondisi):
    """kondisi: True = hijau, False = merah, None = kuning"""
    if kondisi is True:
        kelas = "badge-green"
    elif kondisi is False:
        kelas = "badge-red"
    else:
        kelas = "badge-yellow"
    return f'<span class="{kelas}" style="border:1px solid #e5e7eb;margin-right:8px;">{label}</span>'


def badge(persen):
    if persen >= 90:
        return '<span class="badge-red">Penuh</span>'
    elif persen >= 70:
        return '<span class="badge-yellow">Hampir penuh</span>'
    return '<span class="badge-green">Aman</span>'


# HEADER
col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
with col_h1:
    st.title("♻️ Trash Bin")
with col_h2:
    st.write("")
    st.link_button("💬 Telegram Bot", TELEGRAM_BOT_URL, use_container_width=True)
with col_h3:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.write("")

# BARIS STATUS KONEKSI
esp_kondisi = True if esp_status == "online" else (False if esp_status == "offline" else None)

st.markdown(
    status_badge("Firebase: terhubung" if firebase_ok else "Firebase: gagal", firebase_ok)
    + status_badge(
        {"online": "ESP32: online", "offline": "ESP32: offline", "unknown": "ESP32: belum ada data"}[esp_status],
        esp_kondisi,
    )
    + status_badge(
        "Ultrasonik organik: ada data" if data.get("ultra_organik") else "Ultrasonik organik: belum ada data",
        True if data.get("ultra_organik") else False,
    )
    + status_badge(
        "Ultrasonik anorganik: ada data" if data.get("ultra_anorganik") else "Ultrasonik anorganik: belum ada data",
        True if data.get("ultra_anorganik") else False,
    ),
    unsafe_allow_html=True,
)
st.write("")

# KAPASITAS
col_org, col_anorg = st.columns(2)

with col_org:
    with st.container(border=True, key="card_organik"):
        st.markdown("### 🌱 Organik")
        st.metric("Kepenuhan", f"{cap_org}%")
        st.progress(min(cap_org, 100) / 100.0)
        st.markdown(badge(cap_org), unsafe_allow_html=True)

with col_anorg:
    with st.container(border=True, key="card_anorganik"):
        st.markdown("### 📦 Anorganik")
        st.metric("Kepenuhan", f"{cap_anorg}%")
        st.progress(min(cap_anorg, 100) / 100.0)
        st.markdown(badge(cap_anorg), unsafe_allow_html=True)

@st.cache_data(ttl=10)
def load_history(limit=10):
    """Ambil riwayat klasifikasi terbaru dari /History."""
    try:
        raw = db.reference("/History").order_by_key().limit_to_last(limit).get() or {}
        rows = []
        for item in reversed(list(raw.values())):  # terbaru di atas
            rows.append({
                "Kategori": item.get("kategori", "-"),
                "Skor fuzzy": round(float(item.get("skor_fuzzy", 0)), 1),
            })
        return rows
    except Exception as e:
        print(f"Gagal memuat history: {e}")
        return []
        
# RIWAYAT DETEKSI
with st.container(border=True, key="card_history"):
    st.markdown("### 🕒 Riwayat Deteksi")
    riwayat = load_history(10)
    if riwayat:
        st.dataframe(riwayat, use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada riwayat deteksi.")
