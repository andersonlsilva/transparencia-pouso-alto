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
            fig_bar = px.bar(df_top, x=c_valor, y=c_credor, orientation='h', color=c_valor, color_continuous_scale='Blues')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_g2:
            st.subheader("🔍 Detalhes")
            sel_credor = st.selectbox("Filtrar Credor:", ["Selecione..."] + sorted(df_desp[c_credor].unique()))
            if sel_credor != "Selecione...":
                row = df_desp[df_desp[c_credor] == sel_credor].iloc[0]
                st.success(f"**{sel_credor}**")
                c_data = next((c for c in ['dt_doc_despesa', 'data', 'dt_documento'] if c in cols), cols[0])
                st.write(f"📅 **Data:** {row[c_data]}")
                st.write(f"💰 **Valor:** R$ {row[c_valor]:,.2f}")
                if 'historico' in cols: st.caption(f"📝 **Histórico:** {row['historico']}")
    else:
        st.error(f"Colunas vitais não encontradas. Disponíveis: {cols}")

# --- SEÇÃO 2: DISPENSAS E INEXIGIBILIDADES ---
st.markdown("---")
st.header("⚖️ Dispensas e Inexigibilidades")

params_disp = {
    'data_inicial': '',
    'dta_final': '',
    'ano': '2026-03-21',
    'id_entidade': '2',
    'situacao_processo_compra': '0'
}

data_disp_raw = get_data("https://pmpousoalto.geosiap.net.br:8443/portal-transparencia/api/default/licitacoes/dispensas/dispensas", params_disp)

if data_disp_raw:
    if isinstance(data_disp_raw, dict) and 'dispensas' in data_disp_raw:
        df_disp = pd.DataFrame(data_disp_raw['dispensas'])
    else:
        df_disp = pd.DataFrame(data_disp_raw)

    df_disp.columns = [c.lower() for c in df_disp.columns]
    cols_d = df_disp.columns.tolist()

    c_mod = next((c for c in ['ds_modalidade', 'modalidade', 'tipo_licitacao'] if c in cols_d), None)
    
    if c_mod:
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            fig_pie = px.pie(df_disp, names=c_mod, title="Tipos de Contratação", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_p2:
            st.write("#### Lista de Processos")
            col_view = [c for c in ['dt_processo', 'ds_objeto', c_mod] if c in cols_d]
            st.dataframe(df_disp[col_view], use_container_width=True, hide_index=True)
else:
    st.warning("Nenhum dado de dispensa disponível para o período selecionado.")

st.markdown("---")
st.caption("Fonte: API Geosiap | Dados processados para controle social.")
