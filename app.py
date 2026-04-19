import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import pytz
import base64
from pathlib import Path
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import requests

# Imports das abas
from tab_grafico import render_grafico
from tab_backtest import render_backtest
from tab_heatmap import render_heatmap

# Imports dos helpers
from helpers import (
    VERDE_TICKERS, VERMELHA_TICKERS, TODOS_TICKERS, BRT,
    get_historico_base, get_dados_recentes, ativos, fetch_mxn_brl,
    gerar_dias_uteis, ultimo_candle_real, fetch_di_variacao, checar_e_enviar_alerta_di
)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Trend Axis WDO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- BACKGROUND ---
bg_file = Path(__file__).with_name("fundo.png")
if bg_file.exists():
    with open(bg_file, "rb") as img_file:
        img_b64 = base64.b64encode(img_file.read()).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background: transparent !important;
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("data:image/png;base64,{img_b64}");
        background-size: cover;
        filter: blur(10px) brightness(0.3);
        z-index: -1;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- CSS GLOBAL CORRIGIDO ---
st.markdown("""
<style>

/* FULLSCREEN SEM SCROLL */
html, body, .stApp {
    height: 100%;
    overflow: hidden;
}

.block-container { 
    padding: 0.5rem 1rem !important;
    max-width: 100% !important;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    min-width: 200px !important;
    max-width: 250px !important;
}

/* MOBILE SIDEBAR */
@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        position: fixed !important;
        width: 100% !important;
        height: 100vh !important;
        z-index: 999;
    }
}

/* COLUNAS RESPONSIVAS (CORREÇÃO PRINCIPAL) */
.stColumns {
    flex-wrap: wrap !important;
}

.stColumns > div {
    flex: 1 1 auto !important;
    min-width: 120px !important;
}

/* GRÁFICO FULLSCREEN */
.stPlotlyChart {
    height: calc(100vh - 160px) !important;
}

.stPlotlyChart > div {
    height: 100% !important;
    width: 100% !important;
}

/* TABLET */
@media (max-width: 1024px) {
    .stPlotlyChart {
        height: calc(100vh - 140px) !important;
    }
}

/* MOBILE */
@media (max-width: 768px) {
    .stPlotlyChart {
        height: calc(100vh - 120px) !important;
    }
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    flex-wrap: wrap !important;
}

/* REMOVE SCROLL HORIZONTAL */
.main {
    overflow-x: hidden !important;
}

</style>
""", unsafe_allow_html=True)

# --- AUTO REFRESH ---
st_autorefresh(interval=60000, key="data_refresh")

datas_disponiveis = gerar_dias_uteis()

# --- DADOS DI ---
di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")

cor_34 = "#10B981" if di_34 >= 0 else "#EF4444"
cor_35 = "#10B981" if di_35 >= 0 else "#EF4444"

# --- HEADER SIMPLIFICADO E RESPONSIVO ---
col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

with col1:
    st.markdown("""
    <h2 style='margin:0;'>TREND AXIS</h2>
    """, unsafe_allow_html=True)

with col2:
    start_date = st.date_input("Início", value=pd.Timestamp.now(tz=BRT))

with col3:
    end_date = st.date_input("Fim", value=pd.Timestamp.now(tz=BRT))

with col4:
    st.markdown(f"""
    <div style='display:flex;gap:10px;'>
        <div style='color:{cor_34};font-weight:bold;'>DI34 {di_34:+.2f}%</div>
        <div style='color:{cor_35};font-weight:bold;'>DI35 {di_35:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

# --- DATETIME ---
start_dt = pd.Timestamp(start_date).tz_localize(BRT)
end_dt = pd.Timestamp(end_date).tz_localize(BRT)

if start_dt > end_dt:
    start_dt, end_dt = end_dt, start_dt

# --- RELÓGIO ---
components.html("""
<script>
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('pt-BR', {hour12:false});
    const el = window.parent.document.querySelector('#clock');
    if (el) el.innerText = timeString;
}
setInterval(updateClock,1000);
</script>
""", height=0)

# --- ABAS ---
tab1, tab2, tab3 = st.tabs([
    "📈 Gráfico",
    "🎯 Backtest",
    "🔥 Heatmap"
])

with tab1:
    render_grafico(start_dt, end_dt, None)

with tab2:
    render_backtest(start_dt, end_dt)

with tab3:
    render_heatmap(start_dt, end_dt)

def main():
    pass

if __name__ == "__main__":
    main()