import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. Configuração de Layout e Estilo
st.set_page_config(page_title="Transparência Pouso Alto", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        border: 1px solid #e9ecef; 
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Função de Busca de Dados (com Cache)
@st.cache_data(ttl=3600)
def get_data(url, params):
    try:
        # verify=False ignora erros de certificado SSL comuns em portais municipais
        response = requests.get(url, params=params, verify=False, timeout=20)
        return response.json()
    except Exception as e:
        return None

# 3. Cabeçalho Principal
st.title("🏦 Portal da Transparência: Pouso Alto - MG")
st.info("📍 **Entidade:** PREFEITURA MUNICIPAL DE POUSO ALTO (CNPJ: 18.667.212/0001-92)")

# --- SEÇÃO 1: DESPESAS DETALHADAS ---
st.header("📊 Execução de Despesas (2026)")

params_desp = {
    'cp_ano': '2026',
    'pec': '1',
    'ano': '2026-03-21',
    'id_entidade': '2'
}

data_desp_raw = get_data("https://pmpousoalto.geosiap.net.br:8443/portal-transparencia/api/default/execucao/despesas_detalhadas/despesas_detalhadas", params_desp)

if data_desp_raw:
    # Acessa a chave correta identificada anteriormente
    if isinstance(data_desp_raw, dict) and 'despesas_detalhadas' in data_desp_raw:
        df_desp = pd.DataFrame(data_desp_raw['despesas_detalhadas'])
    else:
        df_desp = pd.DataFrame(data_desp_raw)

    # Normalização e Detecção Dinâmica de Colunas
    df_desp.columns = [c.lower() for c in df_desp.columns]
    cols = df_desp.columns.tolist()

    c_valor = next((c for c in ['valor_empenhado', 'vl_empenhado', 'vlr_empenhado', 'valor'] if c in cols), None)
    c_credor = next((c for c in ['credor', 'nm_credor', 'nome_credor'] if c in cols), None)
    c_pago = next((c for c in ['vl_pago', 'valor_pago', 'vlr_pago'] if c in cols), None)
    c_funcao = next((c for c in ['funcao', 'ds_funcao', 'funcao_governo'] if c in cols), None)

    if c_valor and c_credor:
        # Conversão de tipos
        df_desp[c_valor] = pd.to_numeric(df_desp[c_valor], errors='coerce').fillna(0)
        if c_pago:
            df_desp[c_pago] = pd.to_numeric(df_desp[c_pago], errors='coerce').fillna(0)

        # KPIs
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Empenhado", f"R$ {df_desp[c_valor].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with m2:
            v_pago = df_desp[c_pago].sum() if c_pago else 0
            st.metric("Total Pago", f"R$ {v_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with m3:
            st.metric("Nº de Documentos", len(df_desp))

        # Gráficos
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            st.subheader("🏢 Top 10 Credores")
            df_top = df_desp.groupby(c_credor)[c_valor].sum().sort_values(ascending=True).tail(10).reset_index()
