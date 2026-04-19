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

# --- 2. SISTEMA DE BACKGROUND E OCULTAÇÃO DO "RUNNING" ---
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

# --- 3. CSS AVANÇADO E COMPACTAÇÃO COM ALTURA TOTAL ---
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@700&display=swap');
* {{ 
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}}

/* Reset e configurações base - OTIMIZADO PARA ALTURA TOTAL */
.block-container {{ 
    padding-top: 0.5rem !important; 
    padding-bottom: 0 !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
}}

/* Remove espaçamento extra do main */
.main > div {{
    padding-top: 0 !important;
}}

/* Sidebar responsiva */
[data-testid="stSidebar"] {{
    min-width: 200px !important;
    width: auto !important;
    max-width: 250px !important;
    background-color: rgba(11, 15, 25, 0.95) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255,255,255,0.05);
}}

/* Ajuste para telas pequenas */
@media (max-width: 768px) {{
    [data-testid="stSidebar"] {{
        min-width: 100% !important;
        max-width: 100% !important;
        position: fixed !important;
        z-index: 999 !important;
        height: 100vh !important;
    }}
    
    .block-container {{
        padding-top: 0.5rem !important;
        margin-top: 0 !important;
    }}
}}

/* GRÁFICO RESPONSIVO - OCUPA ALTURA TOTAL DISPONÍVEL */
.stPlotlyChart {{
    width: 100% !important;
    height: auto !important;
    min-height: calc(100vh - 280px) !important;
    flex: 1 !important;
}}

.stPlotlyChart > div {{
    height: 100% !important;
    min-height: calc(100vh - 280px) !important;
    width: 100% !important;
}}

@media (max-width: 1200px) {{
    .stPlotlyChart,
    .stPlotlyChart > div {{
        min-height: calc(100vh - 260px) !important;
    }}
}}

@media (max-width: 992px) {{
    .stPlotlyChart,
    .stPlotlyChart > div {{
        min-height: calc(100vh - 240px) !important;
    }}
}}

@media (max-width: 768px) {{
    .stPlotlyChart,
    .stPlotlyChart > div {{
        min-height: calc(100vh - 200px) !important;
    }}
}}

@media (max-width: 576px) {{
    .stPlotlyChart,
    .stPlotlyChart > div {{
        min-height: calc(100vh - 180px) !important;
    }}
}}

/* Grid responsivo para colunas */
[data-testid="column"] {{
    min-width: 0 !important;
    flex: 1 1 auto !important;
}}

/* Cards responsivos */
.prob-box, .leilao-box, .bt-card {{
    width: 100%;
    margin-bottom: 10px;
}}

/* Títulos responsivos */
.modern-title {{
    font-size: clamp(1.2rem, 5vw, 2.5rem) !important;
}}

.title-date {{
    font-size: clamp(0.8rem, 3vw, 1.5rem) !important;
    margin-left: 10px !important;
}}

/* Tabs responsivas - OTIMIZADAS */
.stTabs {{
    margin-top: 0 !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    flex-wrap: wrap !important;
    gap: 5px !important;
    background-color: transparent !important;
}}

.stTabs [data-baseweb="tab"] {{
    padding: 8px 12px !important;
    font-size: clamp(12px, 3vw, 14px) !important;
}}

.stTabs [data-baseweb="tab-panel"] {{
    padding-top: 0.5rem !important;
    padding-bottom: 0 !important;
    height: auto !important;
    flex: 1 !important;
}}

/* Remove scroll horizontal */
.main {{
    overflow-x: hidden !important;
}}

/* Container principal das abas ocupa altura total */
div[data-testid="stVerticalBlock"] {{
    gap: 0 !important;
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}}

/* Container do gráfico ocupa espaço disponível */
.element-container:has(.stPlotlyChart) {{
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}}
</style>
""", unsafe_allow_html=True)

# --- 4. CSS PARA FIXAR LAYOUT DO CABEÇALHO ---
st.markdown("""
<style>
/* Fixa o layout das colunas para não alterar com redimensionamento */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
    flex-shrink: 0 !important;
    flex-grow: 0 !important;
}

/* Impede que o container principal redimensione as colunas */
.stColumns {
    flex-wrap: nowrap !important;
    min-width: 100% !important;
    margin-bottom: 0.5rem !important;
}

/* Larguras responsivas para colunas */
.stColumns > div:nth-child(1) { 
    min-width: 250px !important; 
    max-width: 320px !important; 
} /* Título */

.stColumns > div:nth-child(2) { 
    min-width: 120px !important; 
    max-width: 150px !important; 
} /* Período */

.stColumns > div:nth-child(3) { 
    min-width: 90px !important; 
    max-width: 110px !important; 
} /* DI34 */

.stColumns > div:nth-child(4) { 
    min-width: 90px !important; 
    max-width: 110px !important; 
} /* DI35 */

.stColumns > div:nth-child(5) { 
    min-width: 200px !important; 
    max-width: auto !important; 
    flex: 1 !important;
} /* Dados */

/* Impede quebra de linha nos textos */
.modern-title, .title-date {
    white-space: nowrap !important;
}

/* Mantém os cards DI com tamanho fixo */
div[style*="text-align: center; background-color: #1E293B"] {
    min-width: 80px !important;
    width: 100% !important;
}

/* Fixa o tamanho do popover */
.stPopover {
    min-width: 120px !important;
}

.stPopover button {
    width: 100% !important;
    min-width: 120px !important;
    color: #94A3B8 !important;
    background-color: #1E293B !important;
    white-space: nowrap !important;
}

/* Ajuste para mobile - adiciona scroll horizontal no cabeçalho */
@media (max-width: 800px) {
    .stColumns {
        overflow-x: auto !important;
        overflow-y: hidden !important;
        white-space: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
    }
    
    .stColumns > div {
        display: inline-block !important;
        float: none !important;
    }
    
    /* Reduz padding em mobile */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.25rem !important;
    }
}

@media (max-width: 480px) {
    .stColumns > div:nth-child(1) { min-width: 200px !important; }
    .stColumns > div:nth-child(2) { min-width: 100px !important; }
    .stColumns > div:nth-child(3) { min-width: 80px !important; }
    .stColumns > div:nth-child(4) { min-width: 80px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 5. INTERFACE PRINCIPAL E FILTROS ---
st_autorefresh(interval=60000, key="data_refresh")
datas_disponiveis = gerar_dias_uteis()

with st.spinner(""):
    di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
    di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")

di_variacao = di_34
cor_34 = "#10B981" if di_34 >= 0 else "#EF4444"
cor_35 = "#10B981" if di_35 >= 0 else "#EF4444"

# Define colunas com larguras fixas
c_tit, c_fd1, c_di34, c_di35, c_dados = st.columns([280, 130, 95, 95, 400])

with c_tit:
    st.markdown(f"""
    <h1 class='modern-title' style='text-align: left; display: flex; align-items: center; margin: 0; padding: 0; font-size: 2.5rem; white-space: nowrap; overflow: visible;'>
        TREND AXIS
        <span id='digital-clock' class='title-date' style='margin-left: 15px; font-size: 1.5rem; color: #94A3B8; white-space: nowrap; display: inline-block;'>| --:--:--</span>
    </h1>
    """, unsafe_allow_html=True)

with c_fd1:
    with st.popover("📅 Período", use_container_width=True):
        start_date = st.selectbox(
            "📅 Início",
            options=datas_disponiveis,
            format_func=lambda d: "Hoje" if str(d) == str(pd.Timestamp.now(tz=BRT).date()) else pd.to_datetime(d).strftime("%d/%m/%y"),
            index=0,
            key="start_date_fixed"
        )
        start_time = st.time_input("🕐 Hora Início", value=time(0, 0), key="start_time_fixed")
        
        st.markdown(f"""
        <div style='margin: 10px 0px; opacity: 0.2;'>           
        </div>
        """, unsafe_allow_html=True)
        
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
    <div style='text-align: center; background-color: #1E293B; padding: 10px 5px; border-radius: 8px; {animacao_34}; width: 100%; min-width: 95px; box-sizing: border-box;'>
        <div style='color: #94A3B8; font-size: 11px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>DI1F34</div>
        <div style='color: {cor_34}; font-size: 16px; font-weight: bold; white-space: nowrap;'>{di_34:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c_di35:
    st.markdown(f"""
    <div style='text-align: center; background-color: #1E293B; padding: 10px 5px; border-radius: 8px; {animacao_35}; width: 100%; min-width: 95px; box-sizing: border-box;'>
        <div style='color: #94A3B8; font-size: 11px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>DI1F35</div>
        <div style='color: {cor_35}; font-size: 16px; font-weight: bold; white-space: nowrap;'>{di_35:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

placeholder_dados = c_dados.empty()

start_dt = pd.Timestamp(f"{start_date} {start_time}").tz_localize(BRT)
end_dt = pd.Timestamp(f"{end_date} {end_time}").tz_localize(BRT)

if start_dt > end_dt:
    start_dt, end_dt = end_dt, start_dt

# Substitua as chamadas originais por estas:
verde_count = ativos(VERDE_TICKERS, start_dt, end_dt, modo='alta')
vermelha_count = ativos(VERMELHA_TICKERS, start_dt, end_dt, modo='baixa')

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

# --- JAVASCRIPT PARA REDIMENSIONAMENTO DINÂMICO DO GRÁFICO ---
components.html("""
<script>
function resizeAllCharts() {
    setTimeout(function() {
        // Encontra todos os containers de gráfico
        var chartContainers = document.querySelectorAll('.stPlotlyChart');
        var windowHeight = window.innerHeight;
        var headerHeight = 250; // Altura estimada do cabeçalho + abas
        
        chartContainers.forEach(function(container) {
            if (container && container.style) {
                var newHeight = (windowHeight - headerHeight) + 'px';
                container.style.height = newHeight;
                container.style.minHeight = newHeight;
                
                // Força o redimensionamento do Plotly
                if (container.children[0] && container.children[0]._fullLayout) {
                    Plotly.relayout(container.children[0], {
                        autosize: true,
                        height: windowHeight - headerHeight
                    });
                }
            }
        });
    }, 100);
}

// Executa no carregamento
window.addEventListener('load', resizeAllCharts);

// Executa quando a janela for redimensionada
window.addEventListener('resize', function() {
    setTimeout(resizeAllCharts, 100);
});

// Observa mudanças na DOM
var observer = new MutationObserver(function(mutations) {
    resizeAllCharts();
});
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", height=0)

# --- ABAS ---
tab1, tab2, tab3 = st.tabs(["📈 Gráfico", "🎯 Backtest de Correlação", "🔥 Mapa de Calor Abertura"])

with tab1:
    render_grafico(start_dt, end_dt, placeholder_dados)

with tab2:
    render_backtest(start_dt, end_dt)

with tab3:
    render_heatmap(start_dt, end_dt)

# Função principal
def main():
    pass  # Tudo já executado acima

if __name__ == "__main__":
    main()
