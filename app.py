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
from datetime import datetime

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

# --- 3. CSS PRINCIPAL COM FOCO EM DISPOSITIVOS MÓVEIS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@700&display=swap');
* { 
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}

/* Reset e configurações base - OTIMIZADO PARA MOBILE */
.block-container { 
    padding-top: 0.25rem !important; 
    padding-bottom: 0 !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
}

/* Remove espaçamento extra */
.main > div {
    padding-top: 0 !important;
}

/* Esconde o header padrão do Streamlit */
header {
    display: none !important;
}

/* Sidebar responsiva */
[data-testid="stSidebar"] {
    min-width: 200px !important;
    width: auto !important;
    max-width: 250px !important;
    background-color: rgba(11, 15, 25, 0.95) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* Ajuste para telas pequenas */
@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        min-width: 100% !important;
        max-width: 100% !important;
        position: fixed !important;
        z-index: 999 !important;
        height: 100vh !important;
    }
    
    .block-container {
        padding-top: 0.25rem !important;
        margin-top: 0 !important;
    }
}

/* CONFIGURAÇÃO DO GRÁFICO PARA MOBILE */
.stPlotlyChart {
    width: 100% !important;
    height: auto !important;
    flex: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.stPlotlyChart > div {
    width: 100% !important;
    height: 100% !important;
}

/* Desktop */
@media (min-width: 1024px) {
    .stPlotlyChart,
    .stPlotlyChart > div {
        min-height: calc(100vh - 300px) !important;
    }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
    .stPlotlyChart,
    .stPlotlyChart > div {
        min-height: calc(100vh - 280px) !important;
    }
}

/* Mobile - O MAIS IMPORTANTE */
@media (max-width: 767px) {
    .stPlotlyChart,
    .stPlotlyChart > div {
        min-height: calc(100vh - 220px) !important;
        height: calc(100vh - 220px) !important;
        max-height: calc(100vh - 220px) !important;
    }
    
    /* Força o container a não ter scroll */
    .main .block-container {
        overflow-y: visible !important;
        height: auto !important;
    }
}

/* Ajuste para mobile muito pequeno */
@media (max-width: 480px) {
    .stPlotlyChart,
    .stPlotlyChart > div {
        min-height: calc(100vh - 200px) !important;
        height: calc(100vh - 200px) !important;
        max-height: calc(100vh - 200px) !important;
    }
}

/* Container flexível */
div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}

/* Container do gráfico ocupa todo espaço */
.element-container:has(.stPlotlyChart) {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}

/* Botões das abas - Estilizados */
.tab-buttons-container {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}

.tab-button {
    flex: 1;
    min-width: 120px;
    padding: 0.75rem 1rem;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: #1E293B;
    color: #94A3B8;
}

.tab-button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.tab-button:hover:not(.active) {
    background-color: #334155;
    color: #F1F5F9;
}

/* Títulos responsivos */
.modern-title {
    font-size: clamp(1rem, 4vw, 2rem) !important;
    margin: 0 !important;
}

.title-date {
    font-size: clamp(0.7rem, 3vw, 1.2rem) !important;
    margin-left: 8px !important;
}

/* Remove scroll horizontal */
.main {
    overflow-x: hidden !important;
    overflow-y: auto !important;
}

/* Esconde scroll vertical desnecessário */
::-webkit-scrollbar {
    width: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)

# --- 4. CSS PARA O CABEÇALHO (RESPONSIVO) ---
st.markdown("""
<style>
/* Fixa o layout das colunas */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
    flex-shrink: 0 !important;
}

.stColumns {
    flex-wrap: nowrap !important;
    min-width: 100% !important;
    margin-bottom: 0.5rem !important;
    gap: 0.5rem !important;
}

/* Larguras responsivas para colunas */
.stColumns > div:nth-child(1) { 
    min-width: 180px !important; 
    max-width: 280px !important; 
}

.stColumns > div:nth-child(2) { 
    min-width: 100px !important; 
    max-width: 130px !important; 
}

.stColumns > div:nth-child(3) { 
    min-width: 80px !important; 
    max-width: 95px !important; 
}

.stColumns > div:nth-child(4) { 
    min-width: 80px !important; 
    max-width: 95px !important; 
}

.stColumns > div:nth-child(5) { 
    min-width: 150px !important; 
    flex: 1 !important;
}

/* Cards DI responsivos */
div[style*="text-align: center; background-color: #1E293B"] {
    min-width: 70px !important;
    padding: 6px 4px !important;
}

div[style*="text-align: center; background-color: #1E293B"] > div:first-child {
    font-size: 10px !important;
}

div[style*="text-align: center; background-color: #1E293B"] > div:last-child {
    font-size: 14px !important;
}

/* Popover responsivo */
.stPopover {
    min-width: 100px !important;
}

.stPopover button {
    width: 100% !important;
    min-width: 100px !important;
    color: #94A3B8 !important;
    background-color: #1E293B !important;
    font-size: 12px !important;
    padding: 4px 8px !important;
}

/* Mobile: cabeçalho com scroll horizontal */
@media (max-width: 768px) {
    .stColumns {
        overflow-x: auto !important;
        overflow-y: hidden !important;
        white-space: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        gap: 0.25rem !important;
    }
    
    .stColumns > div {
        display: inline-block !important;
        float: none !important;
    }
    
    /* Reduz ainda mais em mobile pequeno */
    .stColumns > div:nth-child(1) { min-width: 150px !important; }
    .stColumns > div:nth-child(2) { min-width: 90px !important; }
    .stColumns > div:nth-child(3) { min-width: 70px !important; }
    .stColumns > div:nth-child(4) { min-width: 70px !important; }
    .stColumns > div:nth-child(5) { min-width: 120px !important; }
}

@media (max-width: 480px) {
    .stColumns > div:nth-child(1) { min-width: 130px !important; }
    .stColumns > div:nth-child(2) { min-width: 80px !important; }
    .stColumns > div:nth-child(3) { min-width: 65px !important; }
    .stColumns > div:nth-child(4) { min-width: 65px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 5. INTERFACE PRINCIPAL ---
st_autorefresh(interval=60000, key="data_refresh")
datas_disponiveis = gerar_dias_uteis()

# --- CONTROLE DE ATUALIZAÇÃO DOS DADOS (60s) ---
if "last_data_update" not in st.session_state:
    st.session_state.last_data_update = datetime.now()
    atualizar_dados = True
else:
    atualizar_dados = (datetime.now() - st.session_state.last_data_update).total_seconds() >= 60

if atualizar_dados:
    st.session_state.last_data_update = datetime.now()
    
    with st.spinner(""):
        di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
        di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")
    
    st.session_state.di_34 = di_34
    st.session_state.di_35 = di_35
else:
    di_34 = st.session_state.get("di_34", 0)
    di_35 = st.session_state.get("di_35", 0)

di_variacao = di_34
cor_34 = "#10B981" if di_34 >= 0 else "#EF4444"
cor_35 = "#10B981" if di_35 >= 0 else "#EF4444"

# Define colunas
c_tit, c_fd1, c_di34, c_di35, c_dados = st.columns([280, 130, 95, 95, 400])

with c_tit:
    st.markdown("""
    <h1 class='modern-title' style='text-align: left; display: flex; align-items: center; margin: 0; padding: 0; white-space: nowrap;'>
        TREND AXIS
        <span id='digital-clock' class='title-date' style='margin-left: 8px; color: #94A3B8; white-space: nowrap;'>| --:--:--</span>
    </h1>
    """, unsafe_allow_html=True)

with c_fd1:
    with st.popover("📅 Período", width='stretch'):
        start_date = st.selectbox(
            "📅 Início",
            options=datas_disponiveis,
            format_func=lambda d: "Hoje" if str(d) == str(pd.Timestamp.now(tz=BRT).date()) else pd.to_datetime(d).strftime("%d/%m/%y"),
            index=0,
            key="start_date_fixed"
        )
        start_time = st.time_input("🕐 Hora Início", value=time(0, 0), key="start_time_fixed")
        
        end_date = st.selectbox(
            "📅 Fim",
            options=datas_disponiveis,
            format_func=lambda d: "Hoje" if str(d) == str(pd.Timestamp.now(tz=BRT).date()) else pd.to_datetime(d).strftime("%d/%m/%y"),
            index=0,
            key="end_date_fixed"
        )
        end_time = st.time_input("🕐 Hora Fim", value=time(23, 59), key="end_time_fixed")

animacao_34 = checar_e_enviar_alerta_di("DI34", di_34)
animacao_35 = checar_e_enviar_alerta_di("DI35", di_35)

with c_di34:
    st.markdown(f"""
    <div style='text-align: center; background-color: #1E293B; padding: 8px 4px; border-radius: 8px; {animacao_34}; width: 100%; box-sizing: border-box;'>
        <div style='color: #94A3B8; font-size: 10px; font-weight: 600; white-space: nowrap;'>DI1F34</div>
        <div style='color: {cor_34}; font-size: 14px; font-weight: bold; white-space: nowrap;'>{di_34:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c_di35:
    st.markdown(f"""
    <div style='text-align: center; background-color: #1E293B; padding: 8px 4px; border-radius: 8px; {animacao_35}; width: 100%; box-sizing: border-box;'>
        <div style='color: #94A3B8; font-size: 10px; font-weight: 600; white-space: nowrap;'>DI1F35</div>
        <div style='color: {cor_35}; font-size: 14px; font-weight: bold; white-space: nowrap;'>{di_35:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

placeholder_dados = c_dados.empty()

start_dt = pd.Timestamp(f"{start_date} {start_time}").tz_localize(BRT)
end_dt = pd.Timestamp(f"{end_date} {end_time}").tz_localize(BRT)

if start_dt > end_dt:
    start_dt, end_dt = end_dt, start_dt

if atualizar_dados:
    verde_count = ativos(VERDE_TICKERS, start_dt, end_dt, modo='alta')
    vermelha_count = ativos(VERMELHA_TICKERS, start_dt, end_dt, modo='baixa')

    st.session_state.verde_count = verde_count
    st.session_state.vermelha_count = vermelha_count
else:
    verde_count = st.session_state.get("verde_count", 0)
    vermelha_count = st.session_state.get("vermelha_count", 0)
    
# --- CONTROLE DE ABA ATIVA (SOLUÇÃO 2 - ESTILO ORIGINAL) ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Gráfico"

# --- CRIAR ABAS NO ESTILO ORIGINAL STREAMLIT ---
st.markdown("""
<style>
/* Estilo das abas similar ao original do Streamlit */
.original-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid #3E3E3E;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}

.original-tab {
    padding: 0.5rem 1rem;
    font-size: 1rem;
    font-weight: 500;
    color: #9E9E9E;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.original-tab:hover {
    color: #E0E0E0;
    border-bottom-color: #666;
}

.original-tab.active {
    color: #FFFFFF;
    border-bottom-color: #FF4B4B;
}

/* Responsivo para mobile */
@media (max-width: 768px) {
    .original-tab {
        padding: 0.4rem 0.8rem;
        font-size: 0.85rem;
    }
}

@media (max-width: 480px) {
    .original-tab {
        padding: 0.35rem 0.6rem;
        font-size: 0.75rem;
    }
}
</style>
""", unsafe_allow_html=True)

# Criar as abas no estilo original
col1, col2, col3 = st.columns([1, 1.2, 1.2])

with col1:
    if st.button("📈 Gráfico", 
                 key="tab_grafico",
                 use_container_width=True,
                 type="primary" if st.session_state.active_tab == "Gráfico" else "secondary"):
        st.session_state.active_tab = "Gráfico"
        st.rerun()

with col2:
    if st.button("🎯 Backtest de Correlação", 
                 key="tab_backtest",
                 use_container_width=True,
                 type="primary" if st.session_state.active_tab == "Backtest" else "secondary"):
        st.session_state.active_tab = "Backtest"
        st.rerun()

with col3:
    if st.button("🔥 Mapa de Calor Abertura", 
                 key="tab_heatmap",
                 use_container_width=True,
                 type="primary" if st.session_state.active_tab == "Mapa de Calor" else "secondary"):
        st.session_state.active_tab = "Mapa de Calor"
        st.rerun()

# Adicionar uma linha sutil abaixo das abas
st.markdown('<hr style="margin: 0.5rem 0 1rem 0; opacity: 0.3;">', unsafe_allow_html=True)

# --- RENDERIZAR APENAS A ABA SELECIONADA ---
if st.session_state.active_tab == "Gráfico":
    render_grafico(start_dt, end_dt, placeholder_dados)
elif st.session_state.active_tab == "Backtest":
    render_backtest(start_dt, end_dt)
elif st.session_state.active_tab == "Mapa de Calor":
    render_heatmap(start_dt, end_dt)

# --- RELÓGIO JS ---
components.html("""
<script>
function updateClock() {
    const now = new Date();
    const options = {
        timeZone: 'America/Sao_Paulo',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    const timeString = now.toLocaleTimeString('pt-BR', options);
    const clockElement = window.parent.document.querySelector('#digital-clock');
    if (clockElement) {
        clockElement.innerText = '| ' + timeString;
    }
}
setInterval(updateClock, 1000);
updateClock();
</script>
""", height=0)

# --- JAVASCRIPT PARA AJUSTAR GRÁFICO NO MOBILE ---
components.html("""
<script>
function resizeChartsForMobile() {
    setTimeout(function() {
        var isMobile = window.innerWidth <= 768;
        var charts = document.querySelectorAll('.stPlotlyChart');
        var windowHeight = window.innerHeight;
        
        // Calcula altura disponível baseado no dispositivo
        var headerHeight = isMobile ? 180 : 300;
        var newHeight = windowHeight - headerHeight;
        
        charts.forEach(function(chart) {
            if (chart && chart.style) {
                // Força altura exata
                chart.style.height = newHeight + 'px';
                chart.style.minHeight = newHeight + 'px';
                chart.style.maxHeight = newHeight + 'px';
                
                // Redimensiona o Plotly se existir
                if (chart.children[0] && chart.children[0]._fullLayout) {
                    try {
                        Plotly.relayout(chart.children[0], {
                            autosize: true,
                            height: newHeight
                        });
                    } catch(e) {
                        console.log("Plotly not ready yet");
                    }
                }
            }
        });
    }, 200);
}

// Executa no carregamento e redimensionamento
window.addEventListener('load', resizeChartsForMobile);
window.addEventListener('resize', function() {
    setTimeout(resizeChartsForMobile, 150);
});

// Força redimensionamento quando a aba muda
var observer = new MutationObserver(function(mutations) {
    resizeChartsForMobile();
});
observer.observe(document.body, { childList: true, subtree: true, attributes: true });
</script>
""", height=0)

# Função principal
def main():
    pass

if __name__ == "__main__":
    main()