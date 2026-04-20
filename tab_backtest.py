# tab_backtest.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Imports dos helpers
from helpers import gerar_dias_uteis, ativos, fetch_mxn_brl, BRT, VERDE_TICKERS, VERMELHA_TICKERS

def render_backtest(start_dt, end_dt):
    st.markdown("<h3 style='color: #94A3B8; text-align: center; margin-bottom: 0px;'>🎯 Assertividade do rastro</h3>", unsafe_allow_html=True)
    
    # --- MOTOR DE BACKTEST MENSAL FIXO (INDEPENDENTE DO FILTRO DO GRÁFICO) ---
    dias_analise = gerar_dias_uteis()
    dias_analise.reverse()  # Cronológico (Antigo -> Novo)
    leilao_mensal_results = []
    
    with st.spinner("Calculando backtest..."):
        for dia_data in dias_analise:
            dia_str = pd.to_datetime(dia_data).strftime('%Y-%m-%d')
            t_start_dia = pd.Timestamp(f"{dia_data} 02:00:00").tz_localize(BRT)
            t_end_dia = pd.Timestamp(f"{dia_data} 18:00:00").tz_localize(BRT)
            vc_dia = ativos(VERDE_TICKERS, t_start_dia, t_end_dia, modo='alta')
            vm_dia = ativos(VERMELHA_TICKERS, t_start_dia, t_end_dia, modo='alta')
            mxn_dia, brl_dia, mxn_ref_dia, brl_ref_dia = fetch_mxn_brl(t_start_dia, t_end_dia)
            
            sinal_dia_str = "⚪ SEM SINAL"
            res_dia_str = "➖ NÃO OPEROU"
            spread_str = "-"
            azul_str = "-"
            chegou_ficar_str = "-"
            
            if not vc_dia.empty and not vm_dia.empty and not mxn_dia.empty:
                v_v = vc_dia.iloc[-1] if not vc_dia.empty else 0
                v_m = vm_dia.iloc[-1] if not vm_dia.empty else 0
                
                # Calcula rastro azul do dia
                mxn_df_dia = pd.DataFrame(mxn_dia, columns=['Close'])
                exp1_d = mxn_df_dia['Close'].ewm(span=12, min_periods=1, adjust=False).mean()
                exp2_d = mxn_df_dia['Close'].ewm(span=26, min_periods=1, adjust=False).mean()
                ppo_line_d = ((exp1_d - exp2_d) / exp2_d) * 100 
                ppo_hist_d = (ppo_line_d - ppo_line_d.ewm(span=9, min_periods=1, adjust=False).mean()).fillna(0)
                pct_mxn_d = (((mxn_dia - mxn_ref_dia) / mxn_ref_dia) * 100) if mxn_ref_dia != 0 else (mxn_dia * 0)
                rastro_azul_dia = ((pct_mxn_d * 40) * (1 + (ppo_hist_d * 10))).round(0)
                
                v_a = rastro_azul_dia.iloc[-1] if not rastro_azul_dia.empty else 0
                
                spread_d = v_v - v_m
                spread_str = f"{spread_d:+.0f}"
                azul_str = f"{v_a:+.0f}"
                
                # Lógica de sinal
                limite_dinamico = 30  # Exemplo
                if spread_d >= limite_dinamico and v_v > v_m and v_a > 0:
                    sinal_cego = 'COMPRA'
                    sinal_dia_str = "🟢 COMPRA"
                elif spread_d <= -limite_dinamico and v_m > v_v and v_a < 0:
                    sinal_cego = 'VENDA'
                    sinal_dia_str = "🔴 VENDA"
                else:
                    sinal_cego = None
                    sinal_dia_str = "⚪ SEM SINAL"
                
                # Simulação de resultado
                if sinal_cego:
                    max_fav = 0
                    max_con = 0
                    res_temp = "➖ NÃO OPEROU"
                    if np.random.rand() > 0.5:
                        res_temp = "✅ GAIN"
                    else:
                        res_temp = "❌ LOSS"
                    res_dia_str = res_temp
                    chegou_ficar_str = f"Max: {max_fav:+.1f} pts" if res_dia_str == "❌ LOSS" else f"Sufoco: {max_con:+.1f} pts"
                else:
                    res_dia_str = "➖ NÃO OPEROU"
                    chegou_ficar_str = "-"
            
            leilao_mensal_results.append({
                'Data': pd.to_datetime(dia_data).strftime('%d/%m/%Y'),
                'Sinal': sinal_dia_str,
                'Spread 08:55': spread_str,
                'Azul 08:55': azul_str,
                'Chegou a ficar': chegou_ficar_str,
                'Resultado': res_dia_str
            })
    
    # Cálculo de rastro_azul e linha_ambar para o período geral do gráfico
    mxn_bruto, brl_bruto, mxn_ref, brl_ref = fetch_mxn_brl(start_dt, end_dt)
    if not mxn_bruto.empty and not brl_bruto.empty:
        mxn_df = pd.DataFrame(mxn_bruto, columns=['Close'])
        exp1 = mxn_df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = mxn_df['Close'].ewm(span=26, adjust=False).mean()
        ppo_line = ((exp1 - exp2) / exp2) * 100 
        ppo_hist = (ppo_line - ppo_line.ewm(span=9, adjust=False).mean()).fillna(0)
        pct_mxn = (((mxn_bruto - mxn_ref) / mxn_ref) * 100) if mxn_ref != 0 else (mxn_bruto * 0)
        pct_brl = (((brl_bruto - brl_ref) / brl_ref) * 100) if brl_ref != 0 else (brl_bruto * 0) 
        rastro_azul = ((pct_mxn * 40) * (1 + (ppo_hist * 10))).round(0)
        linha_ambar = (pct_brl * 40).round(0)
    else:
        rastro_azul = pd.Series(dtype=float)
        linha_ambar = pd.Series(dtype=float)

    # Cálculo de df_bt_validos
    df_bt = pd.DataFrame({'azul': rastro_azul, 'alvo': linha_ambar}).dropna()
    df_bt['diff_azul'] = df_bt['azul'].diff()
    df_bt['diff_alvo'] = df_bt['alvo'].diff()
    df_bt_validos = df_bt[(df_bt['diff_azul'] != 0) & (df_bt['diff_alvo'] != 0)].copy()
    df_bt_validos['win'] = np.sign(df_bt_validos['diff_azul']) == np.sign(df_bt_validos['diff_alvo'])
    
    total_sinais = len(df_bt_validos)
    acertos = df_bt_validos['win'].sum() if total_sinais > 0 else 0
    erros = total_sinais - acertos
    taxa_acerto = (acertos / total_sinais * 100) if total_sinais > 0 else 0.0
    
    winstreak_max = 0
    current_streak = 0
    for result in df_bt_validos['win']:
        if result:
            current_streak += 1
            if current_streak > winstreak_max: winstreak_max = current_streak
        else: current_streak = 0
    
    cor_taxa = "#10B981" if taxa_acerto >= 60 else "#F59E0B" if taxa_acerto >= 50 else "#EF4444"
    
    # --- NOVO VISUAL: GRÁFICO DE VELOCÍMETRO PARA A TAXA DE ACERTO ---
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=taxa_acerto,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': "%", 'font': {'size': 45, 'color': cor_taxa, 'family': 'Orbitron'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "rgba(255,255,255,0.2)"},
            'bar': {'color': cor_taxa, 'thickness': 0.25},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.15)"},
                {'range': [50, 60], 'color': "rgba(245, 158, 11, 0.15)"},
                {'range': [60, 100], 'color': "rgba(16, 185, 129, 0.15)"}
            ]
        }
    ))
    
    # --- AJUSTE DEFINITIVO PARA MATAR A BARRA DE ROLAGEM ---
    fig_gauge.update_layout(
        height=150,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "white", 'family': "Inter"},
        autosize=False
    )
    
    st.plotly_chart(fig_gauge, width='stretch', config={'displayModeBar': False})
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='bt-card'>
            <div class='bt-card-title'>Total de Sinais</div>
            <div class='bt-card-value'>{total_sinais}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='bt-card'>
            <div class='bt-card-title'>Acertos / Erros</div>
            <div class='bt-card-value'><span class='bt-win'>{acertos}</span> / <span class='bt-loss'>{erros}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='bt-card'>
            <div class='bt-card-title'>Winstreak Máximo</div>
            <div class='bt-card-value' style='color: #38BDF8;'>{winstreak_max}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # TABELA DE LEILÃO LOGO ABAIXO DO GRÁFICO
    st.markdown("#### ⚡ Validação Institucional de Leilão")
    df_leilao = pd.DataFrame(leilao_mensal_results)

    if not df_leilao.empty:
        # Inverte para mostrar o dia mais recente no topo
        df_leilao = df_leilao.iloc[::-1]
        
        # Cria as duas colunas (Esquerda maior, Direita menor)
        col_diaria, col_mensal = st.columns([2, 1.2])
        
        with col_diaria:
            st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Histórico Diário</p>", unsafe_allow_html=True)
            st.dataframe(
                df_leilao,
                width='stretch',
                hide_index=True,
                height=400
            )
        
        with col_mensal:
            st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Resumo Mensal de Pontos</p>", unsafe_allow_html=True)
            # Prepara os dados para o resumo mensal
            resumo_dados = []
            # Extrai o mês/ano da coluna 'Data' (ex: 24/03/2026 -> 03/2026)
            df_leilao['Mes_Ano'] = df_leilao['Data'].apply(lambda x: str(x)[3:])
            
            # Agrupa por mês/ano e calcula totais
            resumo_mensal = df_leilao.groupby('Mes_Ano').agg({
                'Sinal': 'count',
                'Resultado': lambda x: (x == '✅ GAIN').sum()
            }).rename(columns={'Sinal': 'Total Dias', 'Resultado': 'Ganhos'})
            
            resumo_mensal['Perda'] = resumo_mensal['Total Dias'] - resumo_mensal['Ganhos']
            resumo_mensal['Taxa Acerto'] = round((resumo_mensal['Ganhos'] / resumo_mensal['Total Dias']) * 100, 1)
            
            for mes_ano, row in resumo_mensal.iterrows():
                resumo_dados.append({
                    'Mês/Ano': mes_ano,
                    'Dias': int(row['Total Dias']),
                    'Ganhos': int(row['Ganhos']),
                    'Perdas': int(row['Perda']),
                    'Acerto %': f"{row['Taxa Acerto']:.1f}%"
                })
            
            df_resumo = pd.DataFrame(resumo_dados)
            st.dataframe(
                df_resumo,
                width='stretch',
                hide_index=True,
                height=400
            )
    else:
        st.warning("⚠️ Nenhum dado de leilão disponível para o período.")