import streamlit as st
import requests
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────
#  KONFIGURASI FIREBASE
#  Ganti dengan URL Firebase Realtime Database kamu
# ─────────────────────────────────────────
FIREBASE_URL = "https://your-project-default-rtdb.firebaseio.com"
# Kalau pakai autentikasi, tambahkan:
# FIREBASE_SECRET = "your-database-secret"

# ─────────────────────────────────────────
#  FUNGSI AMBIL DATA DARI FIREBASE
# ─────────────────────────────────────────
def get_firebase_data(path):
    """Ambil data dari Firebase Realtime Database"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

def get_all_data():
    """Ambil semua data sistem dari Firebase"""
    data = get_firebase_data("smartbin")
    if data is None:
        # Data simulasi kalau Firebase belum terhubung
        data = {
            "sensor": {
                "infrared": 1,
                "induktif": 0,
                "kapasitif": 1,
                "ultrasonik_organik": 12.5,
                "ultrasonik_anorganik": 18.3
            },
            "kapasitas": {
                "organik": 80,
                "anorganik": 48
            },
            "klasifikasi": {
                "hasil": "anorganik",
                "sudut_servo": 8.2,
                "rule_aktif": 2,
                "alpha1": 0.15,
                "alpha2": 0.85,
                "alpha3": 0.05
            },
            "statistik": {
                "total": 128,
                "organik": 54,
                "anorganik": 74,
                "akurasi": 96
            },
            "firebase_connected": False
        }
    else:
        data["firebase_connected"] = True
    return data

def get_log_data():
    """Ambil log aktivitas dari Firebase"""
    logs = get_firebase_data("smartbin/log")
    if logs is None:
        # Data simulasi
        logs = {
            "log1": {"jenis": "anorganik", "material": "Plastik botol", "waktu": "09:41", "servo": "0°"},
            "log2": {"jenis": "organik",   "material": "Daun kering",   "waktu": "09:38", "servo": "130°"},
            "log3": {"jenis": "anorganik", "material": "Kaleng aluminium","waktu": "09:35", "servo": "0°"},
            "log4": {"jenis": "organik",   "material": "Sisa makanan",  "waktu": "09:30", "servo": "130°"},
            "log5": {"jenis": "anorganik", "material": "Botol kaca",    "waktu": "09:25", "servo": "0°"},
        }
    return logs

def get_history_data():
    """Ambil data historis 7 hari"""
    history = get_firebase_data("smartbin/history")
    if history is None:
        days = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        history = {
            d: {
                "organik": random.randint(5, 18),
                "anorganik": random.randint(7, 16)
            } for d in days
        }
    return history

# ─────────────────────────────────────────
#  KONFIGURASI HALAMAN STREAMLIT
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SmartBin Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS kustom
st.markdown("""
<style>
    /* Font dan warna utama */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Sembunyikan menu bawaan Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container utama */
    .main .block-container {
        padding: 1.5rem 2rem;
        max-width: 1400px;
    }
    
    /* Metric card kustom */
    .metric-box {
        background: #f8fafb;
        border: 1px solid #e8ecf0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }
    
    /* Badge status */
    .badge-live {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #EAF3DE;
        color: #3B6D11;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .badge-warn {
        background: #FAEEDA;
        color: #854F0B;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .badge-danger {
        background: #FCEBEB;
        color: #A32D2D;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    /* Card sensor */
    .sensor-card {
        background: #f8fafb;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Notifikasi */
    .notif-warn {
        background: #FAEEDA;
        border-left: 4px solid #BA7517;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
    }
    
    .notif-info {
        background: #E6F1FB;
        border-left: 4px solid #378ADD;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
    }
    
    .notif-ok {
        background: #EAF3DE;
        border-left: 4px solid #1D9E75;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
    }
    
    /* Log aktivitas */
    .log-item {
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    
    /* Fuzzy rule */
    .rule-active {
        background: #E6F1FB;
        border-left: 3px solid #378ADD;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 6px;
    }
    
    .rule-inactive {
        background: #f8fafb;
        border-left: 3px solid #e0e0e0;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 6px;
    }
    
    /* Topbar */
    .topbar {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  HEADER / TOPBAR
# ─────────────────────────────────────────
now = datetime.now()
data = get_all_data()
firebase_ok = data.get("firebase_connected", False)

col_logo, col_title, col_right = st.columns([1, 6, 3])

with col_logo:
    st.markdown("## ♻️")

with col_title:
    st.markdown("### SmartBin Dashboard")
    st.caption("Sistem Tempat Sampah Otomatis Berbasis IoT · Politeknik Negeri Samarinda")

with col_right:
    firebase_badge = "🟢 Firebase terhubung" if firebase_ok else "🔴 Mode simulasi"
    st.markdown(f"""
    <div style="text-align:right; margin-top:8px;">
        <span style="font-size:12px; color:#666;">{firebase_badge}</span><br>
        <span style="font-size:13px; font-weight:500;">🔴 Live · {now.strftime('%H:%M:%S WIB')}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────
#  METRIC CARDS
# ─────────────────────────────────────────
statistik = data.get("statistik", {})
total     = statistik.get("total", 0)
org_count = statistik.get("organik", 0)
anorg_count = statistik.get("anorganik", 0)
akurasi   = statistik.get("akurasi", 0)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📦 Total Sampah Masuk",
        value=f"{total} item",
        delta="+14 hari ini"
    )

with col2:
    st.metric(
        label="🍃 Sampah Organik",
        value=f"{org_count} item",
        delta=f"{round(org_count/total*100) if total>0 else 0}% dari total"
    )

with col3:
    st.metric(
        label="🔵 Sampah Anorganik",
        value=f"{anorg_count} item",
        delta=f"{round(anorg_count/total*100) if total>0 else 0}% dari total"
    )

with col4:
    st.metric(
        label="✅ Akurasi Klasifikasi",
        value=f"{akurasi}%",
        delta="Fuzzy Sugeno"
    )

st.markdown("---")

# ─────────────────────────────────────────
#  ROW 1: KAPASITAS WADAH + STATUS SENSOR
# ─────────────────────────────────────────
col_kap, col_sensor = st.columns([1, 1])

with col_kap:
    st.markdown("#### 🗑️ Kapasitas Wadah")
    
    kapasitas = data.get("kapasitas", {})
    org_pct   = kapasitas.get("organik", 0)
    anorg_pct = kapasitas.get("anorganik", 0)
    
    c1, c2 = st.columns(2)
    
    with c1:
        # Gauge organik
        fig_org = go.Figure(go.Indicator(
            mode="gauge+number",
            value=org_pct,
            title={"text": "Organik", "font": {"size": 14}},
            number={"suffix": "%", "font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#1D9E75"},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 60],  "color": "#E1F5EE"},
                    {"range": [60, 80], "color": "#FAEEDA"},
                    {"range": [80, 100],"color": "#FCEBEB"},
                ],
                "threshold": {
                    "line": {"color": "#A32D2D", "width": 3},
                    "thickness": 0.75,
                    "value": 90
                }
            }
        ))
        fig_org.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_org, use_container_width=True)
        
        if org_pct >= 90:
            st.markdown('<span class="badge-danger">🔴 Penuh! Segera dikosongkan</span>', unsafe_allow_html=True)
        elif org_pct >= 70:
            st.markdown('<span class="badge-warn">⚠️ Hampir Penuh</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-live">✓ Normal</span>', unsafe_allow_html=True)
    
    with c2:
        # Gauge anorganik
        fig_anorg = go.Figure(go.Indicator(
            mode="gauge+number",
            value=anorg_pct,
            title={"text": "Anorganik", "font": {"size": 14}},
            number={"suffix": "%", "font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#378ADD"},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 60],  "color": "#E6F1FB"},
                    {"range": [60, 80], "color": "#FAEEDA"},
                    {"range": [80, 100],"color": "#FCEBEB"},
                ],
                "threshold": {
                    "line": {"color": "#A32D2D", "width": 3},
                    "thickness": 0.75,
                    "value": 90
                }
            }
        ))
        fig_anorg.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_anorg, use_container_width=True)
        
        if anorg_pct >= 90:
            st.markdown('<span class="badge-danger">🔴 Penuh! Segera dikosongkan</span>', unsafe_allow_html=True)
        elif anorg_pct >= 70:
            st.markdown('<span class="badge-warn">⚠️ Hampir Penuh</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-live">✓ Normal</span>', unsafe_allow_html=True)
    
    st.caption("📡 Sensor HC-SR04 · diperbarui setiap 5 detik")

with col_sensor:
    st.markdown("#### 📡 Status Sensor (ESP32)")
    
    sensor = data.get("sensor", {})
    
    sensor_data = [
        {
            "nama":  "Proximity Infrared",
            "desc":  "Pendeteksi kehadiran objek",
            "nilai": "Terdeteksi" if sensor.get("infrared", 0) == 1 else "Tidak Ada",
            "aktif": sensor.get("infrared", 0) == 1,
            "icon":  "🟡"
        },
        {
            "nama":  "Proximity Induktif",
            "desc":  "Deteksi material logam",
            "nilai": "Logam Terdeteksi" if sensor.get("induktif", 1) == 0 else "Tidak Ada Logam",
            "aktif": sensor.get("induktif", 1) == 0,
            "icon":  "🔴"
        },
        {
            "nama":  "Proximity Kapasitif",
            "desc":  "Deteksi material non-logam",
            "nilai": "Terdeteksi" if sensor.get("kapasitif", 1) == 0 else "Tidak Terdeteksi",
            "aktif": sensor.get("kapasitif", 1) == 0,
            "icon":  "🔵"
        },
        {
            "nama":  "Ultrasonik Organik",
            "desc":  "Monitor kapasitas wadah organik",
            "nilai": f"{sensor.get('ultrasonik_organik', 0):.1f} cm",
            "aktif": True,
            "icon":  "🟢"
        },
        {
            "nama":  "Ultrasonik Anorganik",
            "desc":  "Monitor kapasitas wadah anorganik",
            "nilai": f"{sensor.get('ultrasonik_anorganik', 0):.1f} cm",
            "aktif": True,
            "icon":  "🟢"
        },
    ]
    
    for s in sensor_data:
        status_color = "#3B6D11" if s["aktif"] else "#888"
        status_text  = "● Aktif" if s["aktif"] else "● Standby"
        st.markdown(f"""
        <div style="background:#f8fafb; border-radius:10px; padding:10px 14px; 
                    margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:13px; font-weight:500;">{s['icon']} {s['nama']}</div>
                <div style="font-size:11px; color:#888;">{s['desc']}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:13px; font-weight:500;">{s['nilai']}</div>
                <div style="font-size:11px; color:{status_color};">{status_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────
#  ROW 2: GRAFIK HISTORIS + LOG AKTIVITAS
# ─────────────────────────────────────────
col_chart, col_log = st.columns([1.2, 1])

with col_chart:
    st.markdown("#### 📊 Riwayat Pemilahan (7 Hari)")
    
    history = get_history_data()
    days_list = list(history.keys())
    org_hist  = [history[d].get("organik", 0) for d in days_list]
    anorg_hist= [history[d].get("anorganik", 0) for d in days_list]
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name="Organik",
        x=days_list,
        y=org_hist,
        marker_color="#1D9E75",
        marker_cornerradius=4
    ))
    fig_bar.add_trace(go.Bar(
        name="Anorganik",
        x=days_list,
        y=anorg_hist,
        marker_color="#378ADD",
        marker_cornerradius=4
    ))
    fig_bar.update_layout(
        barmode="group",
        height=260,
        margin=dict(t=10, b=10, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0", title="Jumlah item"),
        xaxis=dict(gridcolor="#f0f0f0")
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_log:
    st.markdown("#### 📋 Aktivitas Terkini")
    
    logs = get_log_data()
    
    for key in list(logs.keys())[:5]:
        log = logs[key]
        jenis   = log.get("jenis", "")
        material= log.get("material", "")
        waktu   = log.get("waktu", "")
        servo   = log.get("servo", "")
        
        if jenis == "organik":
            dot_color = "#1D9E75"
            tag_bg    = "#E1F5EE"
            tag_color = "#085041"
            tag_label = "Organik"
        elif jenis == "anorganik":
            dot_color = "#378ADD"
            tag_bg    = "#E6F1FB"
            tag_color = "#0C447C"
            tag_label = "Anorganik"
        else:
            dot_color = "#BA7517"
            tag_bg    = "#FAEEDA"
            tag_color = "#412402"
            tag_label = "Peringatan"
        
        st.markdown(f"""
        <div style="display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #f0f0f0; align-items:flex-start;">
            <div style="width:8px;height:8px;border-radius:50%;background:{dot_color};margin-top:5px;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
                    <span style="background:{tag_bg};color:{tag_color};font-size:10px;padding:2px 8px;border-radius:20px;font-weight:500;">{tag_label}</span>
                    <span style="font-size:13px;">{material}</span>
                </div>
                <div style="font-size:11px;color:#888;">{waktu} WIB · Servo → {servo}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────
#  ROW 3: FUZZY LOGIC + NOTIFIKASI
# ─────────────────────────────────────────
col_fuzzy, col_notif = st.columns([1.1, 1])

with col_fuzzy:
    st.markdown("#### 🧠 Fuzzy Sugeno — Inferensi Aktif")
    
    klasifikasi = data.get("klasifikasi", {})
    rule_aktif  = klasifikasi.get("rule_aktif", 0)
    alpha1      = klasifikasi.get("alpha1", 0)
    alpha2      = klasifikasi.get("alpha2", 0)
    alpha3      = klasifikasi.get("alpha3", 0)
    sudut       = klasifikasi.get("sudut_servo", 0)
    hasil       = klasifikasi.get("hasil", "")
    
    sensor = data.get("sensor", {})
    ir_val  = sensor.get("infrared", 0)
    ind_val = sensor.get("induktif", 1)
    kap_val = sensor.get("kapasitif", 1)
    
    st.caption(f"Nilai input saat ini: IR={ir_val} · Induktif={ind_val} · Kapasitif={kap_val}")
    
    rules = [
        {
            "no": 1,
            "label": "Rule 1 — Anorganik (Logam)",
            "kondisi": "IF IR DEKAT AND Induktif RENDAH",
            "alpha": alpha1,
            "z": "0° (wadah anorganik)",
            "aktif": rule_aktif == 1
        },
        {
            "no": 2,
            "label": "Rule 2 — Anorganik (Plastik/Kaca)",
            "kondisi": "IF IR DEKAT AND Induktif TINGGI AND Kapasitif RENDAH",
            "alpha": alpha2,
            "z": "0° (wadah anorganik)",
            "aktif": rule_aktif == 2
        },
        {
            "no": 3,
            "label": "Rule 3 — Organik",
            "kondisi": "IF IR DEKAT AND Induktif TINGGI AND Kapasitif TINGGI",
            "alpha": alpha3,
            "z": "130° (wadah organik)",
            "aktif": rule_aktif == 3
        },
    ]
    
    for r in rules:
        style = "rule-active" if r["aktif"] else "rule-inactive"
        border_color = "#378ADD" if r["aktif"] else "#e0e0e0"
        bg_color     = "#E6F1FB" if r["aktif"] else "#f8fafb"
        st.markdown(f"""
        <div style="background:{bg_color};border-left:3px solid {border_color};
                    padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:500;">{'🔵 ' if r['aktif'] else ''}{r['label']}</div>
            <div style="font-size:11px;color:#888;margin-top:2px;">{r['kondisi']}</div>
            <div style="background:#e0e0e0;border-radius:20px;height:4px;margin-top:6px;">
                <div style="background:{'#378ADD' if r['aktif'] else '#aaa'};width:{int(r['alpha']*100)}%;
                            height:4px;border-radius:20px;"></div>
            </div>
            <div style="font-size:11px;color:#888;margin-top:3px;">α = {r['alpha']} · z = {r['z']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    hasil_color = "#185FA5" if hasil == "anorganik" else "#1D9E75"
    st.markdown(f"""
    <div style="background:#f0f4f8;border-radius:10px;padding:12px 14px;margin-top:4px;">
        <div style="font-size:12px;color:#888;">Output defuzzifikasi (weighted average)</div>
        <div style="font-size:18px;font-weight:600;color:{hasil_color};margin-top:4px;">
            Z = {sudut:.1f}° → Servo ke wadah <span style="text-transform:capitalize;">{hasil}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_notif:
    st.markdown("#### 🔔 Notifikasi Sistem")
    
    kapasitas = data.get("kapasitas", {})
    org_pct   = kapasitas.get("organik", 0)
    anorg_pct = kapasitas.get("anorganik", 0)
    
    if org_pct >= 90:
        st.markdown(f"""
        <div class="notif-warn">
            <div style="font-size:13px;font-weight:500;">⚠️ Wadah Organik Penuh!</div>
            <div style="font-size:12px;color:#666;margin-top:2px;">Kapasitas {org_pct}% — segera dikosongkan</div>
            <div style="font-size:11px;color:#BA7517;margin-top:3px;">{now.strftime('%H:%M')} WIB · HC-SR04 Organik</div>
        </div>
        """, unsafe_allow_html=True)
    elif org_pct >= 70:
        st.markdown(f"""
        <div class="notif-warn">
            <div style="font-size:13px;font-weight:500;">⚠️ Wadah Organik Hampir Penuh</div>
            <div style="font-size:12px;color:#666;margin-top:2px;">Kapasitas mencapai {org_pct}%</div>
            <div style="font-size:11px;color:#BA7517;margin-top:3px;">{now.strftime('%H:%M')} WIB · HC-SR04 Organik</div>
        </div>
        """, unsafe_allow_html=True)
    
    if anorg_pct >= 90:
        st.markdown(f"""
        <div class="notif-warn">
            <div style="font-size:13px;font-weight:500;">⚠️ Wadah Anorganik Penuh!</div>
            <div style="font-size:12px;color:#666;margin-top:2px;">Kapasitas {anorg_pct}% — segera dikosongkan</div>
            <div style="font-size:11px;color:#BA7517;margin-top:3px;">{now.strftime('%H:%M')} WIB · HC-SR04 Anorganik</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="notif-info">
        <div style="font-size:13px;font-weight:500;">📦 Sampah Berhasil Dipilah</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">Motor servo bergerak ke posisi {data.get('klasifikasi',{}).get('sudut_servo',0):.1f}°</div>
        <div style="font-size:11px;color:#185FA5;margin-top:3px;">{now.strftime('%H:%M')} WIB · Fuzzy Sugeno</div>
    </div>
    
    <div class="notif-ok">
        <div style="font-size:13px;font-weight:500;">✅ Sistem Berjalan Normal</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">Semua sensor aktif · ESP32 online</div>
        <div style="font-size:11px;color:#3B6D11;margin-top:3px;">{now.strftime('%H:%M')} WIB · Inisialisasi sistem</div>
    </div>
    
    <div class="notif-info">
        <div style="font-size:13px;font-weight:500;">☁️ Data Terkirim ke Firebase</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">Organik {org_pct}% · Anorganik {anorg_pct}%</div>
        <div style="font-size:11px;color:#185FA5;margin-top:3px;">{now.strftime('%H:%M')} WIB · ESP32 → HTTPS</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
#  FOOTER + AUTO REFRESH
# ─────────────────────────────────────────
st.markdown("---")
st.caption(f"SmartBin IoT Dashboard · Irma Suryani · 23662002 · Politeknik Negeri Samarinda · {now.strftime('%d %B %Y %H:%M:%S')}")

# Auto refresh setiap 5 detik
time.sleep(5)
st.rerun()
