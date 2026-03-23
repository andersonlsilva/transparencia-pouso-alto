import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Configuração de Layout e Estilo
st.set_page_config(page_title="Transparência Pouso Alto", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e9ecef; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE BUSCA ---
@st.cache_data(ttl=3600)
def get_data(url, params):
    try:
        # Nota: verify=False para evitar problemas de certificado da API municipal
        response = requests.get(url, params=params, verify=False, timeout=15)
        return response.json()
    except Exception as e:
        return None

# --- CABEÇALHO ---
st.title("🏦 Portal da Transparência: Pouso Alto - MG")
st.info(f"📍 **Entidade:** PREFEITURA MUNICIPAL DE POUSO ALTO (CNPJ: 18.667.212/0001-92)")

# --- PROCESSAMENTO DE DESPESAS ---
params_desp = {
    'cp_ano': '2026',
    'pec': '1',
    'ano': '2026-03-21',
    'id_entidade': '2'
}

data_raw = get_data("https://pmpousoalto.geosiap.net.br:8443/portal-transparencia/api/default/execucao/despesas_detalhadas/despesas_detalhadas", params_desp)

if data_raw and 'despesas_detalhadas' in data_raw:
    df = pd.DataFrame(data_raw['despesas_detalhadas'])
    
    # Conversão de valores conforme campos de saída reais
    df['valor_empenhado'] = pd.to_numeric(df['valor_empenhado'], errors='coerce').fillna(0)
    df['valor_liquidado'] = pd.to_numeric(df['valor_liquidado'], errors='coerce').fillna(0)
    df['vl_pago'] = pd.to_numeric(df['vl_pago'], errors='coerce').fillna(0)

    # --- MÉTRICAS TOPO ---
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Empenhado", f"R$ {df['valor_empenhado'].sum():,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
    with m2:
        st.metric("Total Pago", f"R$ {df['vl_pago'].sum():,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
    with m3:
        st.metric("Qtd. de Documentos", len(df))

    st.markdown("---")

    # --- GRÁFICOS INTERATIVOS ---
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader("🏢 Maiores Recebedores (Credores)")
        # Agrupamento por Credor
        df_credor = df.groupby('credor')['valor_empenhado'].sum().sort_values(ascending=True).tail(10).reset_index()
        fig_cred = px.bar(df_credor, x='valor_empenhado', y='credor', orientation='h',
                          color='valor_empenhado', color_continuous_scale='Blues',
                          labels={'valor_empenhado': 'Total (R$)', 'credor': 'Nome do Credor'})
        fig_cred.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_cred, use_container_width=True)

        st.subheader("📂 Gastos por Função (Área)")
        df_funcao = df.groupby('funcao')['valor_empenhado'].sum().reset_index()
        fig_fun = px.pie(df_funcao, values='valor_empenhado', names='funcao', hole=.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_fun, use_container_width=True)

    with col_dir:
        st.subheader("🔍 Detalhes por Credor")
        credor_lista = sorted(df['credor'].unique())
        selecionado = st.selectbox("Selecione um Credor:", ["Escolha..."] + credor_lista)

        if selecionado != "Escolha...":
            detalhe = df[df['credor'] == selecionado].iloc[0]
            st.success(f"**{selecionado}**")
            st.write(f"📅 **Data:** {detalhe['dt_doc_despesa']}")
            st.write(f"💰 **Valor Empenhado:** R$ {detalhe['valor_empenhado']:,.2f}")
            st.write(f"🏷️ **Função:** {detalhe['funcao']}")
            st.write(f"⚙️ **Programa:** {detalhe['programa']}")
            st.write(f"📄 **Nº Doc:** {detalhe['nr_doc_despesa']}")
            st.write(f"📝 **Histórico:**")
            st.caption(detalhe['historico'])
            
            # Botão para ver todos os processos deste credor
            if st.button("Ver todas as notas deste credor"):
                st.dataframe(df[df['credor'] == selecionado][['dt_doc_despesa', 'valor_empenhado', 'historico']])

# --- FOOTER ---
st.markdown("---")
st.caption("ℹ️ Dados atualizados via API Geosiap - Exercício 2026. Desenvolvido para Controle Social.")
