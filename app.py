import streamlit as st
import plotly.graph_objects as go
import numpy as np
import requests
import pandas as pd
from datetime import datetime, timedelta

# ── Sayfa ayarları ────────────────────────────────────────────
st.set_page_config(page_title="Döviz Dashboard", page_icon="💱", layout="wide")
st.title("💱 Canlı Döviz Dashboard")

# ── API Fonksiyonları ─────────────────────────────────────────
@st.cache_data(ttl=1800)  # 30 dakikada bir yenile
def tarihsel_veri_cek(para_birimi, gun=90):
    try:
        baslangic = (datetime.today() - timedelta(days=gun)).strftime("%Y-%m-%d")
        bitis     = datetime.today().strftime("%Y-%m-%d")
        url       = f"https://api.frankfurter.app/{baslangic}..{bitis}?from={para_birimi}&to=TRY"
        r         = requests.get(url, timeout=10)
        data      = r.json()["rates"]
        tarihler  = sorted(data.keys())
        kurlar    = [data[t]["TRY"] for t in tarihler]
        return tarihler, kurlar
    except Exception as e:
        st.error(f"API hatası ({para_birimi}): {e}")
        return [], []

@st.cache_data(ttl=1800)
def guncel_kur_cek(para_birimi):
    try:
        url = f"https://api.frankfurter.app/latest?from={para_birimi}&to=TRY"
        r   = requests.get(url, timeout=5)
        return r.json()["rates"]["TRY"]
    except:
        return None

# ── Veri Çek ─────────────────────────────────────────────────
with st.spinner("Veriler yükleniyor..."):
    t_usd, y_usd = tarihsel_veri_cek("USD")
    t_eur, y_eur = tarihsel_veri_cek("EUR")
    t_gbp, y_gbp = tarihsel_veri_cek("GBP")

    guncel_usd = guncel_kur_cek("USD")
    guncel_eur = guncel_kur_cek("EUR")
    guncel_gbp = guncel_kur_cek("GBP")

if not y_usd:
    st.error("Veri çekilemedi.")
    st.stop()

# ── Yardımcı Hesaplamalar ─────────────────────────────────────
def hareketli_ortalama(veri, pencere):
    return [
        sum(veri[i - pencere:i]) / pencere
        if i >= pencere else None
        for i in range(len(veri))
    ]

def bollinger(veri, pencere=20):
    ort  = hareketli_ortalama(veri, pencere)
    band = []
    for i in range(len(veri)):
        if i >= pencere:
            std = np.std(veri[i - pencere:i])
            band.append(std)
        else:
            band.append(None)
    ust  = [o + 2 * b if o and b else None for o, b in zip(ort, band)]
    alt  = [o - 2 * b if o and b else None for o, b in zip(ort, band)]
    return ort, ust, alt

def yuzde_degisim(veri):
    return [
        round((veri[i] - veri[i - 1]) / veri[i - 1] * 100, 4)
        if i > 0 else 0
        for i in range(len(veri))
    ]

def normalize(veri):
    base = veri[0]
    return [round(v / base * 100, 4) for v in veri]

# Hesapla
ma7_usd,  ma30_usd  = hareketli_ortalama(y_usd, 7),  hareketli_ortalama(y_usd, 30)
ma7_eur,  ma30_eur  = hareketli_ortalama(y_eur, 7),  hareketli_ortalama(y_eur, 30)
bol_ort,  bol_ust,  bol_alt  = bollinger(y_usd)
degisim_usd = yuzde_degisim(y_usd)
degisim_eur = yuzde_degisim(y_eur)
norm_usd    = normalize(y_usd)
norm_eur    = normalize(y_eur)
norm_gbp    = normalize(y_gbp)

delta_usd = round(guncel_usd - y_usd[-2], 4) if len(y_usd) > 1 else 0
delta_eur = round(guncel_eur - y_eur[-2], 4) if len(y_eur) > 1 else 0
delta_gbp = round(guncel_gbp - y_gbp[-2], 4) if len(y_gbp) > 1 else 0

# ── KPI Kartları ──────────────────────────────────────────────
st.subheader("📊 Güncel Kurlar")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("USD/TRY",       f"{guncel_usd:.4f}", f"{delta_usd:+.4f}")
k2.metric("EUR/TRY",       f"{guncel_eur:.4f}", f"{delta_eur:+.4f}")
k3.metric("GBP/TRY",       f"{guncel_gbp:.4f}", f"{delta_gbp:+.4f}")
k4.metric("USD Ort.(90g)", f"{np.mean(y_usd):.4f}")
k5.metric("EUR Ort.(90g)", f"{np.mean(y_eur):.4f}")
k6.metric("USD Volatilite",f"{np.std(y_usd):.4f}")

st.divider()

# ── 1. Tarihsel Trend ─────────────────────────────────────────
st.subheader("📈 90 Günlük Tarihsel Trend")
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_usd, y=y_usd, name="USD/TRY",
                          line=dict(color="steelblue", width=2)))
fig.add_trace(go.Scatter(x=t_eur, y=y_eur, name="EUR/TRY",
                          line=dict(color="orange", width=2)))
fig.add_trace(go.Scatter(x=t_gbp, y=y_gbp, name="GBP/TRY",
                          line=dict(color="green", width=2)))
fig.update_layout(height=350, xaxis_title="Tarih", yaxis_title="TRY",
                  hovermode="x unified")
st.plotly_chart(fig, use_container_width=True, key="trend")

st.divider()

# ── 2. Günlük % Değişim ───────────────────────────────────────
st.subheader("📉 Günlük % Değişim")
c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=t_usd, y=degisim_usd, name="USD % Değişim",
        marker_color=["#1D9E75" if d >= 0 else "#D85A30" for d in degisim_usd]
    ))
    fig.update_layout(title="USD/TRY Günlük % Değişim", height=300,
                      xaxis_title="Tarih", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True, key="degisim_usd")

with c2:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=t_eur, y=degisim_eur, name="EUR % Değişim",
        marker_color=["#1D9E75" if d >= 0 else "#D85A30" for d in degisim_eur]
    ))
    fig.update_layout(title="EUR/TRY Günlük % Değişim", height=300,
                      xaxis_title="Tarih", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True, key="degisim_eur")

st.divider()

# ── 3. Normalize Karşılaştırma ────────────────────────────────
st.subheader("🔀 Çoklu Kur Karşılaştırması (Baz=100)")
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_usd, y=norm_usd, name="USD",
                          line=dict(color="steelblue", width=2)))
fig.add_trace(go.Scatter(x=t_eur, y=norm_eur, name="EUR",
                          line=dict(color="orange", width=2)))
fig.add_trace(go.Scatter(x=t_gbp, y=norm_gbp, name="GBP",
                          line=dict(color="green", width=2)))
fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
fig.update_layout(height=350, xaxis_title="Tarih",
                  yaxis_title="Endeks (Başlangıç=100)",
                  hovermode="x unified")
st.plotly_chart(fig, use_container_width=True, key="normalize")

st.divider()

# ── 4. Hareketli Ortalama ─────────────────────────────────────
st.subheader("〰️ Hareketli Ortalama (MA7 / MA30)")
c3, c4 = st.columns(2)

with c3:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_usd, y=y_usd, name="USD/TRY",
                              line=dict(color="lightblue", width=1), opacity=0.6))
    fig.add_trace(go.Scatter(x=t_usd, y=ma7_usd, name="MA7",
                              line=dict(color="steelblue", width=2)))
    fig.add_trace(go.Scatter(x=t_usd, y=ma30_usd, name="MA30",
                              line=dict(color="darkblue", width=2, dash="dash")))
    fig.update_layout(title="USD/TRY Hareketli Ortalama",
                      height=300, xaxis_title="Tarih", yaxis_title="TRY")
    st.plotly_chart(fig, use_container_width=True, key="ma_usd")

with c4:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_eur, y=y_eur, name="EUR/TRY",
                              line=dict(color="moccasin", width=1), opacity=0.6))
    fig.add_trace(go.Scatter(x=t_eur, y=ma7_eur, name="MA7",
                              line=dict(color="orange", width=2)))
    fig.add_trace(go.Scatter(x=t_eur, y=ma30_eur, name="MA30",
                              line=dict(color="darkorange", width=2, dash="dash")))
    fig.update_layout(title="EUR/TRY Hareketli Ortalama",
                      height=300, xaxis_title="Tarih", yaxis_title="TRY")
    st.plotly_chart(fig, use_container_width=True, key="ma_eur")

st.divider()

# ── 5. Bollinger Bandı ────────────────────────────────────────
st.subheader("📐 Bollinger Bandı (USD/TRY, 20 günlük)")
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_usd, y=bol_ust, name="Üst Bant",
                          line=dict(color="lightblue", dash="dash"), opacity=0.7))
fig.add_trace(go.Scatter(x=t_usd, y=bol_alt, name="Alt Bant",
                          line=dict(color="lightblue", dash="dash"), opacity=0.7,
                          fill="tonexty", fillcolor="rgba(70,130,180,0.1)"))
fig.add_trace(go.Scatter(x=t_usd, y=bol_ort, name="MA20 (Orta)",
                          line=dict(color="steelblue", width=2)))
fig.add_trace(go.Scatter(x=t_usd, y=y_usd, name="USD/TRY",
                          line=dict(color="navy", width=1.5)))
fig.update_layout(height=350, xaxis_title="Tarih", yaxis_title="TRY",
                  hovermode="x unified")
st.plotly_chart(fig, use_container_width=True, key="bollinger")

st.divider()

# ── 6. Korelasyon Isı Haritası ────────────────────────────────
st.subheader("🌡️ Korelasyon Isı Haritası")

min_len = min(len(y_usd), len(y_eur), len(y_gbp))
df_corr = pd.DataFrame({
    "USD": y_usd[-min_len:],
    "EUR": y_eur[-min_len:],
    "GBP": y_gbp[-min_len:]
}).corr().round(4)

fig = go.Figure(go.Heatmap(
    z=df_corr.values,
    x=df_corr.columns.tolist(),
    y=df_corr.columns.tolist(),
    colorscale="Blues",
    zmin=0, zmax=1,
    text=df_corr.values.round(2),
    texttemplate="%{text}",
    showscale=True
))
fig.update_layout(title="USD / EUR / GBP Korelasyon Matrisi", height=350)
st.plotly_chart(fig, use_container_width=True, key="korelasyon")

st.divider()

# ── 7. Volatilite Grafiği ─────────────────────────────────────
st.subheader("⚡ 10 Günlük Yuvarlanan Volatilite")
pencere = 10

def volatilite(veri, pencere):
    return [
        round(np.std(veri[i - pencere:i]), 4) if i >= pencere else None
        for i in range(len(veri))
    ]

vol_usd = volatilite(y_usd, pencere)
vol_eur = volatilite(y_eur, pencere)
vol_gbp = volatilite(y_gbp, pencere)

fig = go.Figure()
fig.add_trace(go.Scatter(x=t_usd, y=vol_usd, name="USD Volatilite",
                          line=dict(color="steelblue", width=2), fill="tozeroy",
                          fillcolor="rgba(70,130,180,0.1)"))
fig.add_trace(go.Scatter(x=t_eur, y=vol_eur, name="EUR Volatilite",
                          line=dict(color="orange", width=2)))
fig.add_trace(go.Scatter(x=t_gbp, y=vol_gbp, name="GBP Volatilite",
                          line=dict(color="green", width=2)))
fig.update_layout(height=300, xaxis_title="Tarih",
                  yaxis_title="Standart Sapma", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True, key="volatilite")

st.divider()

# ── 8. Histogram ──────────────────────────────────────────────
st.subheader("📊 Kur Dağılımı (Histogram)")
fig = go.Figure()
fig.add_trace(go.Histogram(x=y_usd, name="USD/TRY", opacity=0.7,
                            marker_color="steelblue", nbinsx=20))
fig.add_trace(go.Histogram(x=y_eur, name="EUR/TRY", opacity=0.7,
                            marker_color="orange", nbinsx=20))
fig.add_trace(go.Histogram(x=y_gbp, name="GBP/TRY", opacity=0.7,
                            marker_color="green", nbinsx=20))
fig.update_layout(barmode="overlay", height=300,
                  xaxis_title="Kur", yaxis_title="Frekans")
st.plotly_chart(fig, use_container_width=True, key="histogram")

# ── Yenile Butonu ─────────────────────────────────────────────
st.divider()
if st.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

st.caption(f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} · Kaynak: frankfurter.app")