# app.py
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

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Trend Axis WDO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SISTEMA DE BACKGROUND ---
bg_file = Path(__file__).with_name("fundo.png")
if bg_file.exists():
    try:
        with open(bg_file, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background: transparent !important;
            }}
            .stApp::before {{
                content: "";
                position: fixed;
                inset: 0;
                background-image: url("data:image/png;base64,{img_b64}");
                background-repeat: no-repeat;
                background-position: center center;
                background-size: cover;
                filter: blur(10px) brightness(0.3);
                z-index: -1;
                pointer-events: none;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

# --- 3. CSS RADICAL PARA ELIMINAR ROLAGEM NO MOBILE ---
st.markdown("""
<style>
/* Reset completo */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* Remove todos os paddings e margins extras */
html, body, .stApp, .main, .block-container {
    margin: 0 !important;
    padding: 0 !important;
}

.block-container {
    padding: 0 0.5rem !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    height: 100vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}

/* Esconde headers e elementos desnecessários */
header, .stApp header, .st-emotion-cache-1avcm0n {
    display: none !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    min-width: 200px !important;
    width: auto !important;
    max-width: 250px !important;
    background-color: rgba(11, 15, 25, 0.95) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255,255,255,0.05);
    z-index: 1000 !important;
}

@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        min-width: 100% !important;
        max-width: 100% !important;
        position: fixed !important;
        height: 100vh !important;
    }
}

/* Container principal - FORÇA SEM ROLAGEM */
.main > div {
    padding: 0 !important;
}

/* CONFIGURAÇÃO CRÍTICA DO GRÁFICO */
.stPlotlyChart {
    width: 100% !important;
    flex: 1 !important;
    min-height: 0 !important;
}

.stPlotlyChart > div {
    width: 100% !important;
    height: 100% !important;
}

/* Desktop */
@media (min-width: 1024px) {
    .stPlotlyChart {
        height: calc(100vh - 200px) !important;
    }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
    .stPlotlyChart {
        height: calc(100vh - 180px) !important;
    }
}

/* Mobile - SOLUÇÃO DEFINITIVA */
@media (max-width: 767px) {
    .stPlotlyChart {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: calc(100vh - 120px) !important;
        top: 120px !important;
        z-index: 1 !important;
    }
    
    .stPlotlyChart > div {
        height: 100% !important;
    }
}

/* Ajuste para mobile pequeno */
@media (max-width: 480px) {
    .stPlotlyChart {
        top: 100px !important;
        height: calc(100vh - 100px) !important;
    }
}

/* Container vertical flexível */
div[data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    min-height: 100vh !important;
}

/* Tabs ocupam espaço fixo no topo */
.stTabs {
    position: relative !important;
    z-index: 2 !important;
    background: transparent !important;
    margin-top: 0 !important;
    flex-shrink: 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    flex-wrap: wrap !important;
    gap: 4px !important;
    background: rgba(0,0,0,0.5) !important;
    backdrop-filter: blur(10px) !important;
    padding: 4px !important;
    border-radius: 8px !important;
}

.stTabs [data-baseweb="tab"] {
    padding: 6px 12px !important;
    font-size: 12px !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding: 0 !important;
    flex: 1 !important;
}

/* Cabeçalho fixo no topo */
.stColumns {
    position: sticky !important;
    top: 0 !important;
    background: rgba(0,0,0,0.8) !important;
    backdrop-filter: blur(10px) !important;
    z-index: 10 !important;
    padding: 8px 0 !important;
    margin-bottom: 8px !important;
    border-radius: 0 !important;
}

/* Títulos menores no mobile */
.modern-title {
    font-size: 1rem !important;
}

.title-date {
    font-size: 0.7rem !important;
    margin-left: 5px !important;
}

/* Cards DI compactos */
div[style*="text-align: center; background-color: #1E293B"] {
    padding: 4px 2px !important;
}

div[style*="text-align: center; background-color: #1E293B"] > div:first-child {
    font-size: 8px !important;
}

div[style*="text-align: center; background-color: #1E293B"] > div:last-child {
    font-size: 11px !important;
}

/* Botões compactos */
.stPopover button {
    font-size: 10px !important;
    padding: 2px 6px !important;
    min-width: 70px !important;
}
</style>
""", unsafe_allow_html=True)

# --- 4. CSS PARA O CABEÇALHO ---
st.markdown("""
<style>
/* Colunas responsivas */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.stColumns {
    flex-wrap: nowrap !important;
    gap: 4px !important;
}

.stColumns > div:nth-child(1) { min-width: 120px !important; max-width: 180px !important; }
.stColumns > div:nth-child(2) { min-width: 70px !important; max-width: 90px !important; }
.stColumns > div:nth-child(3) { min-width: 55px !important; max-width: 65px !important; }
.stColumns > div:nth-child(4) { min-width: 55px !important; max-width: 65px !important; }
.stColumns > div:nth-child(5) { min-width: 80px !important; flex: 1 !important; }

/* Scroll horizontal no cabeçalho se necessário */
@media (max-width: 600px) {
    .stColumns {
        overflow-x: auto !important;
        white-space: nowrap !important;
    }
    
    .stColumns > div {
        display: inline-block !important;
        float: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- 5. INTERFACE PRINCIPAL ---
st_autorefresh(interval=60000, key="data_refresh")
datas_disponiveis = gerar_dias_uteis()

with st.spinner(""):
    di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
    di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")

cor_34 = "#10B981" if di_34 >= 0 else "#EF4444"
cor_35 = "#10B981" if di_35 >= 0 else "#EF4444"

# Define colunas com tamanhos menores para mobile
c_tit, c_fd1, c_di34, c_di35, c_dados = st.columns([180, 90, 65, 65, 200])

with c_tit:
    st.markdown("""
    <h1 class='modern-title' style='margin:0; padding:0; font-size:1rem; white-space:nowrap;'>
        TA 
        <span id='digital-clock' style='font-size:0.7rem; color:#94A3B8;'>--:--:--</span>
    </h1>
    """, unsafe_allow_html=True)

with c_fd1:
    with st.popover("📅", use_container_width=True):
        start_date = st.selectbox(
            "Início",
            options=datas_disponiveis,
            format_func=lambda d: "Hoje" if str(d) == str(pd.Timestamp.now(tz=BRT).date()) else pd.to_datetime(d).strftime("%d/%m"),
            index=0,
            key="start_date_fixed",
            label_visibility="collapsed"
        )
        start_time = st.time_input("Hora", value=time(0, 0), key="start_time_fixed", label_visibility="collapsed")
        
        end_date = st.selectbox(
            "Fim",
            options=datas_disponiveis,
            format_func=lambda d: "Hoje" if str(d) == str(pd.Timestamp.now(tz=BRT).date()) else pd.to_datetime(d).strftime("%d/%m"),
            index=0,
            key="end_date_fixed",
            label_visibility="collapsed"
        )
        end_time = st.time_input("Hora Fim", value=time(23, 59), key="end_time_fixed", label_visibility="collapsed")

animacao_34 = checar_e_enviar_alerta_di("DI34", di_34)
animacao_35 = checar_e_enviar_alerta_di("DI35", di_35)

with c_di34:
    st.markdown(f"""
    <div style='text-align:center; background:#1E293B; padding:4px 2px; border-radius:6px; {animacao_34}'>
        <div style='color:#94A3B8; font-size:8px;'>34</div>
        <div style='color:{cor_34}; font-size:11px; font-weight:bold;'>{di_34:+.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c_di35:
    st.markdown(f"""
    <div style='text-align:center; background:#1E293B; padding:4px 2px; border-radius:6px; {animacao_35}'>
        <div style='color:#94A3B8; font-size:8px;'>35</div>
        <div style='color:{cor_35}; font-size:11px; font-weight:bold;'>{di_35:+.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

placeholder_dados = c_dados.empty()

start_dt = pd.Timestamp(f"{start_date} {start_time}").tz_localize(BRT)
end_dt = pd.Timestamp(f"{end_date} {end_time}").tz_localize(BRT)

if start_dt > end_dt:
    start_dt, end_dt = end_dt, start_dt

verde_count = ativos(VERDE_TICKERS, start_dt, end_dt, modo='alta')
vermelha_count = ativos(VERMELHA_TICKERS, start_dt, end_dt, modo='baixa')

# --- RELÓGIO JS ---
components.html("""
<script>
function updateClock() {
    const now = new Date();
    const options = {timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false};
    const timeString = now.toLocaleTimeString('pt-BR', options);
    const clockElement = window.parent.document.querySelector('#digital-clock');
    if (clockElement) clockElement.innerText = timeString;
}
setInterval(updateClock, 1000);
updateClock();
</script>
""", height=0)

# --- JAVASCRIPT FORÇANDO GRÁFICO OCUPAR TELA INTEIRA NO MOBILE ---
components.html("""
<script>
function fixChartHeight() {
    setTimeout(function() {
        const isMobile = window.innerWidth <= 768;
        const charts = document.querySelectorAll('.stPlotlyChart');
        const viewportHeight = window.innerHeight;
        
        if (isMobile) {
            // No mobile, posiciona o gráfico para ocupar toda área disponível
            const tabs = document.querySelector('.stTabs');
            const tabsHeight = tabs ? tabs.offsetHeight : 80;
            const headerHeight = 80;
            const availableHeight = viewportHeight - headerHeight - tabsHeight;
            
            charts.forEach(function(chart) {
                if (chart && chart.style) {
                    chart.style.position = 'relative';
                    chart.style.height = availableHeight + 'px';
                    chart.style.minHeight = availableHeight + 'px';
                    
                    // Força o redimensionamento do Plotly
                    if (chart.children[0] && chart.children[0]._fullLayout) {
                        try {
                            Plotly.relayout(chart.children[0], {
                                autosize: true,
                                height: availableHeight
                            });
                        } catch(e) {}
                    }
                }
            });
        } else {
            // Desktop
            charts.forEach(function(chart) {
                if (chart && chart.style) {
                    chart.style.position = 'relative';
                    chart.style.height = (viewportHeight - 200) + 'px';
                }
            });
        }
    }, 300);
}

// Executa várias vezes para garantir
window.addEventListener('load', fixChartHeight);
window.addEventListener('resize', fixChartHeight);
setTimeout(fixChartHeight, 500);
setTimeout(fixChartHeight, 1000);

// Observa mudanças
const observer = new MutationObserver(fixChartHeight);
observer.observe(document.body, { childList: true, subtree: true, attributes: true });
</script>
""", height=0)

# --- ABAS ---
tab1, tab2, tab3 = st.tabs(["📈", "🎯", "🔥"])

with tab1:
    render_grafico(start_dt, end_dt, placeholder_dados)

with tab2:
    render_backtest(start_dt, end_dt)

with tab3:
    render_heatmap(start_dt, end_dt)

def main():
    pass

if __name__ == "__main__":
    main()