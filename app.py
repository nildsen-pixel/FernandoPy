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

# NOTA: Assumindo que os imports abaixo existem no ambiente original do usuário
# Caso contrário, o código precisará de ajustes nos mocks de dados.
try:
    from tab_grafico import render_grafico
    from tab_backtest import render_backtest
    from tab_heatmap import render_heatmap
    from helpers import (
        VERDE_TICKERS, VERMELHA_TICKERS, TODOS_TICKERS, BRT,
        get_historico_base, get_dados_recentes, ativos, fetch_mxn_brl,
        gerar_dias_uteis, ultimo_candle_real, fetch_di_variacao, checar_e_enviar_alerta_di
    )
except ImportError:
    # Mocks para evitar erro de execução durante o desenvolvimento se os arquivos não estiverem presentes
    BRT = pytz.timezone('America/Sao_Paulo')
    def gerar_dias_uteis(): return [datetime.now(tz=BRT).date()]
    def fetch_di_variacao(ticker, name): return 0.0
    def checar_e_enviar_alerta_di(name, val): return ""
    def ativos(tickers, start, end, modo): return 0
    def render_grafico(start, end, placeholder): st.info("Gráfico será renderizado aqui")
    def render_backtest(start, end): st.info("Backtest será renderizado aqui")
    def render_heatmap(start, end): st.info("Heatmap será renderizado aqui")
    VERDE_TICKERS = []
    VERMELHA_TICKERS = []

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Trend Axis WDO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SISTEMA DE BACKGROUND ---
bg_file = Path(__file__).parent / "upload" / "fundo.png"
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
                filter: blur(15px) brightness(0.25);
                z-index: -1;
                pointer-events: none;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

# --- 3. CSS GLOBAL E MELHORIAS DE COMPONENTES ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@700&display=swap');

:root {
    --bg-card: rgba(30, 41, 59, 0.7);
    --border-card: rgba(255, 255, 255, 0.1);
    --accent-color: #3B82F6;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
}

* { 
    font-family: 'Inter', sans-serif;
}

/* Ajustes Gerais de Layout */
.block-container { 
    padding: 1rem 2rem !important;
    max-width: 100% !important;
}

header { visibility: hidden; }

/* Estilização de Cards de Indicadores */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    backdrop-filter: blur(8px);
    transition: transform 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.2);
}

.metric-label {
    color: var(--text-muted);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 1.25rem;
    font-weight: 700;
    font-family: 'Orbitron', sans-serif;
}

/* Estilização das Abas (Pills) */
div[data-baseweb="button-group"] {
    background: rgba(15, 23, 42, 0.6);
    padding: 4px;
    border-radius: 12px;
    border: 1px solid var(--border-card);
    margin-bottom: 20px;
}

div[data-baseweb="button-group"] button {
    border: none !important;
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    font-weight: 500 !important;
}

div[data-baseweb="button-group"] button[aria-selected="true"] {
    background: var(--accent-color) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* Melhoria no Popover de Período */
.stPopover button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 8px !important;
    color: var(--text-main) !important;
}

/* Customização do Relógio */
#digital-clock {
    font-family: 'Orbitron', sans-serif;
    color: var(--accent-color);
    text-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
}

/* Ajustes para Mobile */
@media (max-width: 768px) {
    .block-container { padding: 0.5rem !important; }
    .modern-title { font-size: 1.2rem !important; }
    .stColumns { gap: 0.5rem !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 4. LÓGICA DE DADOS ---
st_autorefresh(interval=60000, key="data_refresh")
datas_disponiveis = gerar_dias_uteis()

if "last_data_update" not in st.session_state:
    st.session_state.last_data_update = datetime.now()
    atualizar_dados = True
else:
    atualizar_dados = (datetime.now() - st.session_state.last_data_update).total_seconds() >= 60

if atualizar_dados:
    st.session_state.last_data_update = datetime.now()
    with st.spinner("Atualizando indicadores..."):
        di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
        di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")
    st.session_state.di_34 = di_34
    st.session_state.di_35 = di_35
else:
    di_34 = st.session_state.get("di_34", 0)
    di_35 = st.session_state.get("di_35", 0)

# --- 5. CABEÇALHO REORGANIZADO ---
# Usando colunas para melhor distribuição espacial
c_tit, c_spacer, c_di34, c_di35, c_periodo = st.columns([1.5, 0.5, 0.8, 0.8, 1])

with c_tit:
    st.markdown(f"""
    <div style='display: flex; flex-direction: column;'>
        <h1 class='modern-title' style='margin: 0; color: white; font-size: 1.8rem; font-weight: 800;'>
            TREND AXIS
        </h1>
        <div id='digital-clock' style='font-size: 1.1rem; font-weight: 500; margin-top: -5px;'>
            --:--:--
        </div>
    </div>
    """, unsafe_allow_html=True)

animacao_34 = checar_e_enviar_alerta_di("DI34", di_34)
animacao_35 = checar_e_enviar_alerta_di("DI35", di_35)

with c_di34:
    cor_34 = "#10B981" if di_34 >= 0 else "#EF4444"
    st.markdown(f"""
    <div class="metric-card" style="{animacao_34}">
        <div class="metric-label">DI1F34</div>
        <div class="metric-value" style="color: {cor_34};">{di_34:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c_di35:
    cor_35 = "#10B981" if di_35 >= 0 else "#EF4444"
    st.markdown(f"""
    <div class="metric-card" style="{animacao_35}">
        <div class="metric-label">DI1F35</div>
        <div class="metric-value" style="color: {cor_35};">{di_35:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c_periodo:
    with st.popover("📅 Configurar Período", use_container_width=True):
        st.subheader("Intervalo de Tempo")
        start_date = st.selectbox("Início", options=datas_disponiveis, index=0, key="sd")
        start_time = st.time_input("Hora Início", value=time(9, 0), key="st")
        st.divider()
        end_date = st.selectbox("Fim", options=datas_disponiveis, index=0, key="ed")
        end_time = st.time_input("Hora Fim", value=time(18, 0), key="et")

# --- 6. INDICADORES DE FLUXO (VERDE/VERMELHA/AZUL) ---
start_dt = pd.Timestamp(f"{start_date} {start_time}").tz_localize(BRT)
end_dt = pd.Timestamp(f"{end_date} {end_time}").tz_localize(BRT)
if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt

if atualizar_dados:
    verde_count = ativos(VERDE_TICKERS, start_dt, end_dt, modo='alta')
    vermelha_count = ativos(VERMELHA_TICKERS, start_dt, end_dt, modo='baixa')
    st.session_state.verde_count = verde_count
    st.session_state.vermelha_count = vermelha_count
else:
    verde_count = st.session_state.get("verde_count", 0)
    vermelha_count = st.session_state.get("vermelha_count", 0)

# Linha de resumo de ativos (Nova Seção)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Ativos em Alta</div><div class='metric-value' style='color: #10B981;'>{verde_count}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Ativos em Baixa</div><div class='metric-value' style='color: #EF4444;'>{vermelha_count}</div></div>", unsafe_allow_html=True)
with c3:
    diff = verde_count - vermelha_count
    cor_diff = "#10B981" if diff >= 0 else "#EF4444"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Saldo Δ</div><div class='metric-value' style='color: {cor_diff};'>{diff:+}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Status</div><div class='metric-value' style='color: #3B82F6;'>ATIVO</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 7. NAVEGAÇÃO E CONTEÚDO ---
opcoes_abas = ["📈 Gráfico", "🎯 Backtest de Correlação", "🔥 Mapa de Calor Abertura"]
aba_selecionada = st.pills(
    "Navegação",
    options=opcoes_abas,
    selection_mode="single",
    default=st.session_state.get("active_tab", opcoes_abas[0]),
    label_visibility="collapsed"
)
st.session_state.active_tab = aba_selecionada

# Placeholder para dados específicos da aba de gráfico
placeholder_dados = st.empty()

# Renderização condicional
if aba_selecionada == "📈 Gráfico":
    render_grafico(start_dt, end_dt, placeholder_dados)
elif aba_selecionada == "🎯 Backtest de Correlação":
    render_backtest(start_dt, end_dt)
elif aba_selecionada == "🔥 Mapa de Calor Abertura":
    render_heatmap(start_dt, end_dt)

# --- 8. SCRIPTS (Relógio e Ajustes) ---
components.html("""
<script>
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false
    });
    const clockElement = window.parent.document.querySelector('#digital-clock');
    if (clockElement) clockElement.innerText = timeString;
}
setInterval(updateClock, 1000);
updateClock();

// Ajuste automático de altura para o gráfico
function adjustChartHeight() {
    const charts = window.parent.document.querySelectorAll('.stPlotlyChart');
    charts.forEach(chart => {
        chart.style.height = 'calc(100vh - 400px)';
    });
}
setTimeout(adjustChartHeight, 1000);
</script>
""", height=0)
