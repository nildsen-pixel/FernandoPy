# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, time
import pytz
import base64
from pathlib import Path
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# Abas
from tab_grafico import render_grafico
from tab_backtest import render_backtest
from tab_heatmap import render_heatmap

# Helpers
from helpers import (
    VERDE_TICKERS, VERMELHA_TICKERS, BRT,
    ativos, fetch_di_variacao,
    gerar_dias_uteis, checar_e_enviar_alerta_di
)

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Trend Axis WDO",
    page_icon="📈",
    layout="wide"
)

# ---------------- BACKGROUND SUAVE ----------------
bg_file = Path(__file__).with_name("fundo.png")
if bg_file.exists():
    with open(bg_file, "rb") as img_file:
        img_b64 = base64.b64encode(img_file.read()).decode()

    st.markdown(f"""
    <style>
    .stApp {{
        background: #0E1117;
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("data:image/png;base64,{img_b64}");
        background-size: cover;
        filter: blur(18px) brightness(0.18);
        z-index: -1;
    }}
    </style>
    """, unsafe_allow_html=True)

# ---------------- CSS LIMPO ----------------
st.markdown("""
<style>

/* esconder header padrão */
header {visibility: hidden;}

/* layout base */
.block-container {
    padding-top: 0.5rem;
    max-width: 100%;
}

/* HEADER */
.header {
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.title {
    font-size:1.6rem;
    font-weight:700;
    color:#E5E7EB;
}

.clock {
    color:#9CA3AF;
}

/* KPIs */
.kpi-box {
    background: rgba(30,41,59,0.6);
    padding:10px;
    border-radius:8px;
    text-align:center;
}

.kpi-title {
    font-size:11px;
    color:#94A3B8;
}

.kpi-value {
    font-size:16px;
    font-weight:bold;
}

/* gráfico dominante */
.stPlotlyChart {
    height: 72vh !important;
}

/* pills */
div[data-baseweb="button-group"] {
    margin-top:10px;
    border-bottom:1px solid rgba(255,255,255,0.1);
}

</style>
""", unsafe_allow_html=True)

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=60000, key="refresh")

# ---------------- HEADER ----------------
c1, c2 = st.columns([3,1])

with c1:
    st.markdown("""
    <div class="title">
        TREND AXIS <span id="clock" class="clock">--:--:--</span>
    </div>
    """, unsafe_allow_html=True)

with c2:
    datas = gerar_dias_uteis()

    start_date = st.selectbox("Início", datas)
    end_date = st.selectbox("Fim", datas)

start_dt = pd.Timestamp(f"{start_date} 00:00").tz_localize(BRT)
end_dt = pd.Timestamp(f"{end_date} 23:59").tz_localize(BRT)

# ---------------- CONTROLE DE UPDATE ----------------
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now()
    atualizar = True
else:
    atualizar = (datetime.now() - st.session_state.last_update).seconds >= 60

if atualizar:
    st.session_state.last_update = datetime.now()

    di_34 = fetch_di_variacao("BMFBOVESPA:DI1F2034", "DI1F34")
    di_35 = fetch_di_variacao("BMFBOVESPA:DI1F2035", "DI1F35")

    st.session_state.di_34 = di_34
    st.session_state.di_35 = di_35
else:
    di_34 = st.session_state.di_34
    di_35 = st.session_state.di_35

cor_34 = "#00C853" if di_34 >= 0 else "#FF5252"
cor_35 = "#00C853" if di_35 >= 0 else "#FF5252"

# ---------------- KPIs ----------------
k1, k2, k3 = st.columns(3)

with k1:
    st.markdown(f"""
    <div class="kpi-box">
        <div class="kpi-title">DI1F34</div>
        <div class="kpi-value" style="color:{cor_34}">
            {di_34:+.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-box">
        <div class="kpi-title">DI1F35</div>
        <div class="kpi-value" style="color:{cor_35}">
            {di_35:+.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

# fluxo
verde = ativos(VERDE_TICKERS, start_dt, end_dt, modo='alta')
vermelho = ativos(VERMELHA_TICKERS, start_dt, end_dt, modo='baixa')
delta = verde - vermelho

cor_delta = "#00C853" if delta >= 0 else "#FF5252"

with k3:
    st.markdown(f"""
    <div class="kpi-box">
        <div class="kpi-title">Fluxo</div>
        <div class="kpi-value">
            🟢 {verde} | 🔴 {vermelho} |
            <span style="color:{cor_delta}">Δ {delta}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- ABAS ----------------
if "tab" not in st.session_state:
    st.session_state.tab = "📈 Gráfico"

tab = st.pills(
    "",
    ["📈 Gráfico", "🎯 Backtest", "🔥 Heatmap"],
    default=st.session_state.tab
)

st.session_state.tab = tab

# ---------------- CONTEÚDO ----------------
if tab == "📈 Gráfico":
    render_grafico(start_dt, end_dt, st.empty())

elif tab == "🎯 Backtest":
    render_backtest(start_dt, end_dt)

elif tab == "🔥 Heatmap":
    render_heatmap(start_dt, end_dt)

# ---------------- CLOCK ----------------
components.html("""
<script>
setInterval(()=>{
    const now=new Date();
    const t=now.toLocaleTimeString('pt-BR');
    const el=window.parent.document.querySelector('#clock');
    if(el){el.innerText=" | "+t;}
},1000);
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