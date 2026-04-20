# tab_heatmap.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Imports dos helpers
from helpers import gerar_dias_uteis, ativos

def render_heatmap(start_dt, end_dt):
    st.markdown("<h3 style='color: #94A3B8; text-align: center; margin-bottom: 0px;'>🔥 Mapa de Calor Abertura</h3>", unsafe_allow_html=True)
    
    # Placeholder para o mapa de calor (baseado no código original, que não tinha conteúdo específico)
    # Aqui você pode adicionar a lógica real do mapa de calor
    st.info("Mapa de Calor da Abertura em desenvolvimento. Adicione aqui a análise de correlação ou volatilidade.")
    
    # Exemplo de mapa de calor básico para teste (volatilidade simulada)
    dias = pd.date_range(start=start_dt.date(), end=end_dt.date(), freq='D')
    horas = [f'{h:02d}:00' for h in range(9, 18)]  # Horas de negociação
    
    # Simulação de dados (substitua pela sua lógica)
    data = np.random.rand(len(dias), len(horas)) * 100  # Volatilidade %
    df_heatmap = pd.DataFrame(data, index=dias, columns=horas)
    
    # Transforma para formato longo para Plotly
    df_long = df_heatmap.reset_index().melt(id_vars='index', var_name='Hora', value_name='Volatilidade')
    df_long.rename(columns={'index': 'Data'}, inplace=True)
    
    if not df_long.empty:
        fig = px.density_heatmap(
            df_long,
            x="Hora",
            y="Data",
            z="Volatilidade",
            color_continuous_scale="Viridis",
            title="Mapa de Calor da Volatilidade Diária (Exemplo)"
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            xaxis_title="Hora do Dia",
            yaxis_title="Data",
            coloraxis_colorbar=dict(title="Volatilidade (%)")
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.warning("Nenhum dado disponível para o mapa de calor.")