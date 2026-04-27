# tab_grafico.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import time
from functools import lru_cache

# Imports dos helpers
from helpers import (
    ativos, fetch_mxn_brl, ultimo_candle_real, BRT, VERDE_TICKERS, VERMELHA_TICKERS,
    fetch_di_variacao, gerar_dias_uteis
)

# ==========================================
# FUNÇÕES DE CACHE PARA DADOS HISTÓRICOS
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)  # Cache de 1 hora para dados históricos
def get_historico_ativos_cache(tickers_tuple, start_dt_str, end_dt_str, modo):
    """
    Busca dados históricos de ativos com cache baseado nas strings das datas.
    Isso garante que os dados do passado NUNCA mudem.
    
    Parâmetros:
    - tickers_tuple: tupla de tickers (para ser hashable pelo cache)
    - start_dt_str: string da data de início
    - end_dt_str: string da data de fim
    - modo: 'alta' ou 'baixa'
    """
    # Converte strings para Timestamp com timezone de forma segura
    start_dt = pd.Timestamp(start_dt_str)
    end_dt = pd.Timestamp(end_dt_str)
    
    # Se já tem timezone, usa tz_convert; senão, usa tz_localize
    if start_dt.tz is None:
        start_dt = start_dt.tz_localize(BRT)
    else:
        start_dt = start_dt.tz_convert(BRT)
    
    if end_dt.tz is None:
        end_dt = end_dt.tz_localize(BRT)
    else:
        end_dt = end_dt.tz_convert(BRT)
    
    # Converte tupla de volta para lista
    tickers = list(tickers_tuple)
    
    # Busca os dados históricos
    df = ativos(tickers, start_dt, end_dt, modo)
    
    # Retorna uma cópia para evitar modificações
    return df.copy() if df is not None else df

@st.cache_data(ttl=60, show_spinner=False)  # Cache curto para dados do dia atual
def get_ativos_hoje_cache(tickers_tuple, modo):
    """
    Busca apenas dados de hoje (que podem ser atualizados a cada 60 segundos)
    """
    hoje = pd.Timestamp.now(tz=BRT).normalize()
    amanha = hoje + pd.Timedelta(days=1)
    
    tickers = list(tickers_tuple)
    df = ativos(tickers, hoje, amanha, modo)
    return df.copy() if df is not None else df

def get_ativos_com_cache(tickers, start_dt, end_dt, modo):
    """
    Combina dados históricos (cache longo) com dados atuais (cache curto)
    """
    hoje = pd.Timestamp.now(tz=BRT).normalize()
    tickers_tuple = tuple(tickers)  # Converte para tupla (hashable)
    
    # Converte para strings de forma segura (sem timezone na string)
    start_dt_str = start_dt.tz_convert(BRT).strftime('%Y-%m-%d %H:%M:%S')
    end_dt_str = end_dt.tz_convert(BRT).strftime('%Y-%m-%d %H:%M:%S')
    
    # Se o período é totalmente no passado (end_dt < hoje)
    if end_dt < hoje:
        return get_historico_ativos_cache(
            tickers_tuple, 
            start_dt_str, 
            end_dt_str, 
            modo
        )
    
    # Se o período inclui hoje, separa histórico + hoje
    if start_dt < hoje:
        # Parte histórica (antes de hoje)
        historico_end = hoje - pd.Timedelta(seconds=1)
        historico_end_str = historico_end.strftime('%Y-%m-%d %H:%M:%S')
        
        historico = get_historico_ativos_cache(
            tickers_tuple,
            start_dt_str,
            historico_end_str,
            modo
        )
        
        # Dados de hoje (atualizáveis)
        hoje_df = get_ativos_hoje_cache(tickers_tuple, modo)
        
        # Combina os dados
        if historico is not None and hoje_df is not None and not historico.empty and not hoje_df.empty:
            return pd.concat([historico, hoje_df]).drop_duplicates().sort_index()
        elif historico is not None and not historico.empty:
            return historico
        elif hoje_df is not None and not hoje_df.empty:
            return hoje_df
    
    # Apenas dados de hoje
    return get_ativos_hoje_cache(tickers_tuple, modo)

@st.cache_data(ttl=30, show_spinner=False)  # Cache de 30 segundos para o último candle
def get_ultimo_candle_cacheado():
    """
    Retorna o último candle real com cache curto.
    Isso evita recálculos constantes durante o autorefresh.
    """
    return ultimo_candle_real()

def get_ultimo_candle_para_periodo(end_dt):
    """
    Retorna o último candle apropriado para o período.
    Para períodos passados, o valor é imutável (usa end_dt).
    Para períodos atuais, o valor pode ser atualizado com cache.
    """
    agora = pd.Timestamp.now(tz=BRT)
    
    # Converte end_dt para timezone BRT se necessário
    if end_dt.tz is None:
        end_dt = end_dt.tz_localize(BRT)
    else:
        end_dt = end_dt.tz_convert(BRT)
    
    # Se o período termina antes de agora (dados históricos completos)
    if end_dt < agora:
        # Usa o fim do período como referência fixa
        return end_dt
    
    # Se inclui o presente, usa o último candle real com cache
    return get_ultimo_candle_cacheado()

@st.cache_data(ttl=3600, show_spinner=False)
def processar_dados_historicos(start_dt, end_dt):
    """
    Processa APENAS dados históricos (imutáveis) do MXN/BRL
    Aceita Timestamps diretamente (com ou sem timezone)
    """
    # Converte para timezone BRT de forma segura
    if start_dt.tz is None:
        start_dt = start_dt.tz_localize(BRT)
    else:
        start_dt = start_dt.tz_convert(BRT)
    
    if end_dt.tz is None:
        end_dt = end_dt.tz_localize(BRT)
    else:
        end_dt = end_dt.tz_convert(BRT)
    
    # Busca dados do MXN/BRL
    mxn_bruto, brl_bruto, mxn_ref, brl_ref = fetch_mxn_brl(start_dt, end_dt)
    
    return {
        'mxn_bruto': mxn_bruto,
        'brl_bruto': brl_bruto,
        'mxn_ref': mxn_ref,
        'brl_ref': brl_ref
    }


# ==========================================
# FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO
# ==========================================

def render_grafico(start_dt, end_dt, placeholder_dados):
    """
    Renderiza o gráfico com dados históricos imutáveis e dados atuais atualizáveis
    """
    
    # Garante que as datas estão no timezone correto
    if start_dt.tz is None:
        start_dt = start_dt.tz_localize(BRT)
    else:
        start_dt = start_dt.tz_convert(BRT)
    
    if end_dt.tz is None:
        end_dt = end_dt.tz_localize(BRT)
    else:
        end_dt = end_dt.tz_convert(BRT)
    
    # --- PROCESSAMENTO DOS DADOS COM CACHE ---
    with st.spinner("Processando Inteligência de Gráfico..."):
        # Dados históricos dos ativos (com cache inteligente)
        verde_count = get_ativos_com_cache(VERDE_TICKERS, start_dt, end_dt, modo='alta')
        vermelha_count = get_ativos_com_cache(VERMELHA_TICKERS, start_dt, end_dt, modo='alta')
        
        # Dados do MXN/BRL (históricos imutáveis) - passa os Timestamps diretamente
        dados_mxn = processar_dados_historicos(start_dt, end_dt)
        mxn_bruto = dados_mxn['mxn_bruto']
        brl_bruto = dados_mxn['brl_bruto']
        mxn_ref = dados_mxn['mxn_ref']
        brl_ref = dados_mxn['brl_ref']

    # Verificação de dados após processamento
    if verde_count is None or verde_count.empty or vermelha_count is None or vermelha_count.empty or mxn_bruto is None or mxn_bruto.empty:
        motivos = []
        hoje = pd.Timestamp.now(tz=BRT).date()
        if end_dt.date() > hoje:
            motivos.append("datas futuras (yfinance não tem dados reais)")
        if start_dt.weekday() >= 5 or end_dt.weekday() >= 5:
            motivos.append("fins de semana/feriados (sem negociações)")
        if (end_dt - start_dt).total_seconds() < 3600:
            motivos.append("período muito curto")
        
        motivo_str = "; ".join(motivos) if motivos else "erro na API ou período sem negociações"
        st.warning(f"⚠️ Dados insuficientes para montar o gráfico ({motivo_str}). Tente datas recentes úteis (seg-sex, últimos 5-10 dias, 9h-17h) no popover.")
        
        # Placeholder gráfico com sugestão
        fig_placeholder = go.Figure()
        fig_placeholder.add_annotation(
            text="Aguardando dados válidos...\nSugestão: Use datas recentes (ex: 25/03/2024 a 29/03/2024, 9h-17h)",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=14, font_color="#94A3B8"
        )
        fig_placeholder.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_placeholder, width='stretch')
        return

    # --- TRUNCAGEM INTELIGENTE (usa cache para último candle) ---
    agora_idx = get_ultimo_candle_para_periodo(end_dt)
    
    
    # Verifica se precisa truncar (apenas para dados do período atual)
    if end_dt > agora_idx and isinstance(agora_idx, pd.Timestamp):
        if verde_count is not None and not verde_count.empty:
            verde_count = verde_count[verde_count.index <= agora_idx]
        if vermelha_count is not None and not vermelha_count.empty:
            vermelha_count = vermelha_count[vermelha_count.index <= agora_idx]
        if mxn_bruto is not None and not mxn_bruto.empty:
            mxn_bruto = mxn_bruto[mxn_bruto.index <= agora_idx]
        if brl_bruto is not None and not brl_bruto.empty:
            brl_bruto = brl_bruto[brl_bruto.index <= agora_idx]

    # --- CÁLCULOS DAS MÉTRICAS (RSI, PPO, etc) ---
    if mxn_bruto is not None and not mxn_bruto.dropna().empty:
        mxn_df = pd.DataFrame(mxn_bruto, columns=['Close'])
        delta = mxn_df['Close'].diff()
        gain, loss = delta.where(delta > 0, 0.0), -delta.where(delta < 0, 0.0)
        avg_gain, avg_loss = gain.ewm(alpha=1/14, min_periods=1, adjust=False).mean(), loss.ewm(alpha=1/14, min_periods=1, adjust=False).mean()
        mxn_df['RSI_14'] = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        exp1, exp2 = mxn_df['Close'].ewm(span=12, adjust=False).mean(), mxn_df['Close'].ewm(span=26, adjust=False).mean()
        ppo_line = ((exp1 - exp2) / exp2) * 100 
        ppo_hist = (ppo_line - ppo_line.ewm(span=9, adjust=False).mean()).fillna(0)
        
        pct_mxn = (((mxn_bruto - mxn_ref) / mxn_ref) * 100) if mxn_ref != 0 else (mxn_bruto * 0)
        pct_brl = (((brl_bruto - brl_ref) / brl_ref) * 100) if brl_ref != 0 else (brl_bruto * 0) 
        
        rastro_azul = ((pct_mxn * 40) * (1 + (ppo_hist * 10))).round(0)
        linha_cinza = (pct_mxn * 40).round(0) 
        linha_ambar = (pct_brl * 40).round(0) 
        rsi_atual_mxn, ppo_atual = mxn_df['RSI_14'].iloc[-1], ppo_hist.iloc[-1]
    else:
        # Fallback para quando não há dados MXN
        if verde_count is not None and not verde_count.empty:
            rastro_azul = pd.Series(0, index=verde_count.index)
            linha_cinza = pd.Series(0, index=verde_count.index)
            linha_ambar = pd.Series(0, index=verde_count.index)
        else:
            rastro_azul = pd.Series(dtype=float)
            linha_cinza = pd.Series(dtype=float)
            linha_ambar = pd.Series(dtype=float)
        rsi_atual_mxn, ppo_atual = 50, 0

    # --- MÉTRICAS ATUAIS ---
    verde_atual = verde_count.iloc[-1] if verde_count is not None and not verde_count.empty else 0
    verm_atual = vermelha_count.iloc[-1] if vermelha_count is not None and not vermelha_count.empty else 0
    azul_atual = rastro_azul.iloc[-1] if rastro_azul is not None and not rastro_azul.empty else 0
    
    spread = verde_atual - verm_atual 
    cor_spread = "#10B981" if spread > 0 else "#EF4444" if spread < 0 else "#94A3B8"
    
    prob_alta = min(max(50.0 + min(max(spread * 0.4, -30), 30) + (10 if ppo_atual > 0.01 else -10 if ppo_atual < -0.01 else 0) + (10 if rsi_atual_mxn > 55 else -10 if rsi_atual_mxn < 45 else 0), 5), 95)
    prob_baixa = 100 - prob_alta
    
    trava_alerta = ""
    if rsi_atual_mxn >= 70: 
        trava_alerta = "⚠️ TRAVA: COMPRA EXAUSTA"
        prob_alta = min(prob_alta, 40) 
    elif rsi_atual_mxn <= 30: 
        trava_alerta = "⚠️ TRAVA: VENDA EXAUSTA"
        prob_baixa = min(prob_baixa, 40)

    limite_forte, limite_normal = 30, 10
    limite_leilao = 35 
    
    if spread >= limite_forte: 
        status_color, status_text = "#10B981", "🟢 FORTE PRESSÃO COMPRADORA"
    elif spread >= limite_normal: 
        status_color, status_text = "#34D399", "🟢 PRESSÃO COMPRADORA"
    elif spread <= -limite_forte: 
        status_color, status_text = "#EF4444", "🔴 FORTE PRESSÃO VENDEDORA"
    elif spread <= -limite_normal: 
        status_color, status_text = "#F87171", "🔴 PRESSÃO VENDEDORA"
    else: 
        status_color, status_text = "#94A3B8", "⚪ CONSOLIDAÇÃO / NEUTRO"

    # --- LÓGICA DE LEILÃO ---
    agora = pd.Timestamp.now(tz=BRT).time()
    inicio_leilao = time(8, 55)
    fim_leilao = time(9, 0)
    alerta_leilao_html = ""

    if inicio_leilao <= agora <= fim_leilao:
        if spread >= limite_leilao and azul_atual > 0:
            alerta_leilao_html = f"<div class='leilao-box' style='border-left-color: #10B981;'><span class='leilao-pulse' style='color: #10B981; font-weight: bold; font-size: 15px;'>⏳ LEILÃO (08:55): ✅ COMPRA HABILITADA (Spread: {spread:+.0f} | Azul: {azul_atual:+.0f})</span></div>"
        elif spread <= -limite_leilao and azul_atual < 0:
            alerta_leilao_html = f"<div class='leilao-box' style='border-left-color: #EF4444;'><span class='leilao-pulse' style='color: #EF4444; font-weight: bold; font-size: 15px;'>⏳ LEILÃO (08:55): 🚨 VENDA HABILITADA (Spread: {spread:+.0f} | Azul: {azul_atual:+.0f})</span></div>"
        else: 
            alerta_leilao_html = f"<div class='leilao-box' style='border-left-color: #94A3B8;'><span style='color: #94A3B8; font-size: 14px;'>⏳ LEILÃO (08:55): </span><span style='color: #94A3B8; font-weight: bold; font-size: 15px;'>Aguardando spread (+{limite_leilao} ou -{limite_leilao}) e alinhamento do Azul</span></div>"

    # --- RENDERIZAÇÃO DO CABEÇALHO ---
    placeholder_dados.markdown(f"""
        <div style='display: flex; justify-content: space-around; align-items: center; background: rgba(15, 23, 42, 0.6); border-radius: 8px; padding: 5px 10px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
            <div style='text-align: center;'><span style='color: #94A3B8; font-size: 10px;'>VERDE</span><br><span style='color: #10B981; font-weight: bold; font-size: 15px;'>🟢 {verde_atual:.0f}</span></div>
            <div style='text-align: center;'><span style='color: #94A3B8; font-size: 10px;'>VERMELHA</span><br><span style='color: #EF4444; font-weight: bold; font-size: 15px;'>🔴 {verm_atual:.0f}</span></div>
            <div style='text-align: left;'><span style='color: #94A3B8; font-size: 10px;'>Δ</span><br><span style='color: {cor_spread}; font-weight: bold; font-size: 15px;'>Δ {spread:+.0f}</span></div>
            <div style='text-align: center;'><span style='color: #94A3B8; font-size: 10px;'>AZUL</span><br><span style='color: #38BDF8; font-weight: bold; font-size: 15px;'>🔵 {azul_atual:+.0f}</span></div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(alerta_leilao_html, unsafe_allow_html=True)

    # --- PROBABILIDADE E STATUS ---
    c_prob, c_status = st.columns([1, 1])
    with c_prob:
        st.markdown(f"""
        <div class='prob-box'>
            <div style='width: 100%;'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 2px;'>
                    <span style='color: #10B981; font-weight: bold; font-size: 12px;'>📈 {prob_alta:.0f}% Alta</span>
                    <span style='color: #EF4444; font-weight: bold; font-size: 12px;'>Baixa {prob_baixa:.0f}% 📉</span>
                </div>
                <div style='width: 100%; background-color: rgba(239, 68, 68, 0.3); height: 8px; border-radius: 4px; overflow: hidden; display: flex;'>
                    <div style='width: {prob_alta}%; background-color: #10B981; height: 100%; transition: width 0.5s ease-in-out;'></div>
                </div>
                <div style='text-align: center; margin-top: 2px;'><span style='color: #F59E0B; font-size: 10px; font-weight: bold;'>{trava_alerta}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_status:
        st.markdown(f"""
        <div class='prob-box' style='justify-content: center; height: 100%; border-color: {status_color}40;'>
            <span style='color: {status_color}; font-weight: bold; font-size: 14px; text-align: center;'>{status_text}</span>
        </div>
        """, unsafe_allow_html=True)

    # --- GRÁFICO PRINCIPAL ---
    # Verifica se todos os DataFrames são válidos antes de prosseguir
    if verde_count is None or vermelha_count is None or rastro_azul is None:
        st.warning("⚠️ Dados insuficientes para desenhar o gráfico.")
        return
        
    common_idx = verde_count.index.intersection(vermelha_count.index).intersection(rastro_azul.index)
    
    if common_idx.empty:
        st.warning("⚠️ Sem dados em comum para desenhar o gráfico.")
        return

    delta_series = (verde_count[common_idx] - vermelha_count[common_idx]).round(0).astype(int)
    
    fig = go.Figure()

    # 1. SPREAD (Invisível, só para tooltip)
    fig.add_trace(go.Scatter(
        x=common_idx,
        y=verde_count[common_idx],
        customdata=delta_series,
        mode='lines',
        name='📊 Spread',
        line=dict(color='rgba(0,0,0,0)', width=0),
        showlegend=False,
        hovertemplate='📊 Spread: %{customdata:.0f}<extra></extra>'
    ))

    # 2. VERMELHA
    fig.add_trace(go.Scatter(
        x=common_idx,
        y=vermelha_count[common_idx],
        mode='lines+markers',
        name='🔴 Vermelha',
        line=dict(color='#EF4444', width=3, shape='spline', smoothing=1.1),
        marker=dict(size=5, symbol='circle'),
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.05)',
        hovertemplate='%{y:.0f}<extra></extra>'
    ))

    # 3. VERDE
    fig.add_trace(go.Scatter(
        x=common_idx,
        y=verde_count[common_idx],
        mode='lines+markers',
        name='🟢 Verde',
        line=dict(color='#10B981', width=3, shape='spline', smoothing=1.1),
        marker=dict(size=5, symbol='circle'),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.05)',
        hovertemplate='%{y:.0f}<extra></extra>'
    ))

    # 4. FLUXO BASE (Cinza)
    if linha_cinza is not None and not linha_cinza.empty:
        fig.add_trace(go.Scatter(
            x=linha_cinza.index,
            y=linha_cinza,
            mode='lines',
            name='⚪ (Fluxo Base)',
            line=dict(color='rgba(148, 163, 184, 0.6)', width=1.2, dash='solid', shape='spline', smoothing=0.6),
            hoverinfo='skip'
        ))

    # 5. WDO (Âmbar)
    if linha_ambar is not None and not linha_ambar.empty:
        fig.add_trace(go.Scatter(
            x=linha_ambar.index,
            y=linha_ambar,
            mode='lines',
            name='🟠 (WDO)',
            line=dict(color='#F59E0B', width=1.2, dash='solid', shape='spline', smoothing=0.6),
            hoverinfo='skip'
        ))

    # 6. AZUL
    fig.add_trace(go.Scatter(
        x=rastro_azul.index,
        y=rastro_azul,
        mode='lines+markers',
        name='🔵',
        line=dict(color='#38BDF8', width=2.0, shape='spline', smoothing=0.8, dash='dot'),
        marker=dict(size=5, symbol='circle'),
        yaxis='y2',
        hovertemplate='Azul: %{y:.0f}<extra></extra>'
    ))

    # Folga automática para evitar corte
    all_vals_list = []
    if verde_count is not None and not verde_count.empty:
        all_vals_list.append(verde_count[common_idx])
    if vermelha_count is not None and not vermelha_count.empty:
        all_vals_list.append(vermelha_count[common_idx])
    if linha_cinza is not None and not linha_cinza.empty:
        all_vals_list.append(linha_cinza.reindex(common_idx))
    if linha_ambar is not None and not linha_ambar.empty:
        all_vals_list.append(linha_ambar.reindex(common_idx))
    if rastro_azul is not None and not rastro_azul.empty:
        all_vals_list.append(rastro_azul.reindex(common_idx))
    
    all_vals = pd.concat(all_vals_list, axis=0).dropna() if all_vals_list else pd.Series(dtype=float)
    
    if not all_vals.empty:
        y_max = all_vals.max()
        y_min = all_vals.min()
        padding = max((y_max - y_min) * 0.08, 5)
    else:
        y_max, y_min, padding = 10, -10, 5

    # LAYOUT DO GRÁFICO
    fig.update_layout(
        dragmode=False,
        clickmode="none",
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color="white",
            bordercolor="rgba(255,255,255,0.2)",
            align="left"
        ),
        height=380,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(color="white", size=11),
            bgcolor="rgba(0,0,0,0)"
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=50, t=30, b=20),
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            automargin=True,
            showticklabels=True,
            tickfont=dict(color="#F8FAFC", size=10),
            hoverformat='%H:%M',
            showspikes=True,
            spikemode='across',
            spikecolor='rgba(255,255,255,0.12)',
            spikethickness=0.3,
            spikesnap='cursor',
            tickangle=-45 if len(common_idx) > 20 else 0
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            side='left',
            automargin=True,
            showticklabels=True,
            tickfont=dict(color="#F8FAFC", size=10),
            range=[y_min - padding, y_max + padding]
        ),
        yaxis2=dict(
            title=dict(text="Azul", font=dict(color="#F8FAFC", size=10)),
            overlaying='y',
            side='right',
            showticklabels=True,
            tickfont=dict(color="#F8FAFC", size=10),
            range=[
                (rastro_azul.min() * 1.2 if not rastro_azul.empty else -75),
                (rastro_azul.max() * 1.2 if not rastro_azul.empty else 75)
            ]
        ),
        autosize=True,
        width=None
    )
    
    # Ajuste de tamanho dos marcadores
    num_points = len(common_idx)
    if num_points > 50:
        fig.update_traces(marker=dict(size=3))
    elif num_points > 100:
        fig.update_traces(marker=dict(size=2))

    st.plotly_chart(
        fig,
        width='stretch',
        theme=None,
        config={
            'displayModeBar': False,
            'scrollZoom': False,
            'displaylogo': False,
            'responsive': True,
            "staticPlot": False,
            "editable": False,
            "showAxisDragHandles": False,
            "showAxisRangeEntryBoxes": False
        }
    )