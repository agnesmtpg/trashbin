import streamlit as st
import pandas as pd
import plotly.express as px
import time
import requests

# URL SUDAH DIPERBAIKI: Ditambah "data_sampah.json" di akhir
FIREBASE_URL = "https://pemilah-sampah-otomatis-c8d2e-default-rtdb.firebaseio.com/data_sampah.json"

st.set_page_config(
    page_title="Dashboard Pemilah Sampah",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ Dashboard Sistem Pemilah Sampah Otomatis")
st.markdown("Memantau data pemilahan sampah Basah dan Kering secara real-time dari Firebase.")

def load_data():
    try:
        response = requests.get(FIREBASE_URL)
        data = response.json()
        
        if data:
            # Firebase menyimpan data dalam bentuk dictionary bersarang dengan ID unik
            # Kita ubah format dictionary tersebut menjadi list of dictionaries lalu ke DataFrame
            df = pd.DataFrame.from_dict(data, orient='index')
            return df
        else:
            return pd.DataFrame(columns=["Waktu", "Jarak_cm", "Kelembaban", "Tipe"])
    except Exception as e:
        st.error(f"Gagal mengambil data dari Firebase: {e}")
        return pd.DataFrame(columns=["Waktu", "Jarak_cm", "Kelembaban", "Tipe"])

placeholder = st.empty()

while True:
    df = load_data()
    
    with placeholder.container():
        if not df.empty:
            latest_data = df.iloc[-1]
            
            # 1. TAMPILAN METRIK KARTU
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Status Sensor Jarak", f"{latest_data.get('Jarak_cm', 0)} cm")
            col2.metric("Nilai Kelembaban Terakhir", f"{latest_data.get('Kelembaban', 0)}")
            
            if latest_data.get('Tipe') == "BASAH":
                col3.error(f"Tipe Terakhir: {latest_data['Tipe']} 💧")
            else:
                col3.success(f"Tipe Terakhir: {latest_data.get('Tipe', 'Tidak Diketahui')} 🍂")
                
            col4.metric("Total Sampah Diproses", f"{len(df)} item")

            st.markdown("---")

            # 2. GRAFIK DAN VISUALISASI
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("📊 Distribusi Sampah")
                if 'Tipe' in df.columns:
                    tipe_count = df['Tipe'].value_counts().reset_index()
                    tipe_count.columns = ['Tipe', 'Jumlah']
                    
                    fig_pie = px.pie(tipe_count, values='Jumlah', names='Tipe', 
                                     color='Tipe',
                                     color_discrete_map={'BASAH':'#3498db', 'KERING':'#e67e22'},
                                     hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_chart2:
                st.subheader("📈 Tren Kelembaban Sampah")
                df_tail = df.tail(20)
                
                # Menggunakan index sebagai sumbu X jika kolom Waktu dari millis() ESP32 kurang informatif
                fig_line = px.line(df_tail, x=df_tail.index, y='Kelembaban', markers=True,
                                   color_discrete_sequence=['#2ecc71'])
                fig_line.add_hline(y=2500, line_dash="dash", line_color="red", annotation_text="Batas Basah (2500)")
                
                # Sembunyikan label X axis karena isinya berupa push ID Firebase
                fig_line.update_xaxes(showticklabels=False, title_text="Waktu / Urutan Data")
                st.plotly_chart(fig_line, use_container_width=True)

            # 3. TABEL RIWAYAT
            st.subheader("📝 Riwayat Pemilahan Terakhir")
            st.dataframe(df.tail(10).sort_index(ascending=False), use_container_width=True)
            
        else:
            st.info("Menunggu data masuk ke Firebase... Pastikan ESP32 sudah mendeteksi sampah.")

    time.sleep(2)