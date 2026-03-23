import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Configuração de Layout
st.set_page_config(page_title="Portal Transparência Pouso Alto",
                   layout="wide", page_icon="🏦")

# Estilização Customizada via CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div.stButton > button:first-child { background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS (CACHE PARA VELOCIDADE) ---


@st.cache_data
def fetch_data(url, params):
    try:
        response = requests.get(url, params=params, verify=False, timeout=10)
        return response.json()
    except Exception as e:
        return None


# --- SIDEBAR / FILTROS ---
st.sidebar.header("📍 Localização & Período")
st.sidebar.info(
    "Município: Pouso Alto - MG\n\nEntidade: Prefeitura Municipal\n\nData: 21/03/2026")

# --- CORPO PRINCIPAL ---
st.title("🏦 Painel de Transparência Cidadã")
st.subheader("Entenda como o dinheiro público está sendo utilizado")

# Carregamento dos Dados
despesas_raw = fetch_data(
    "https://pmpousoalto.geosiap.net.br:8443/portal-transparencia/api/default/execucao/despesas_detalhadas/despesas_detalhadas",
    {'cp_ano': '2026', 'pec': '1', 'ano': '2026-03-21', 'id_entidade': '2'}
)

dispensas_raw = fetch_data(
    "https://pmpousoalto.geosiap.net.br:8443/portal-transparencia/api/default/licitacoes/dispensas/dispensas",
    {'data_inicial': '', 'dta_final': '', 'ano': '2026-03-21',
        'id_entidade': '2', 'situacao_processo_compra': '0'}
)

# --- SEÇÃO 1: RESUMO DE DESPESAS
if despesas_raw:
    # 1. ACESSANDO A "CAIXA" CORRETA (Ajuste baseado no erro que você recebeu)
    if isinstance(despesas_raw, dict) and 'despesas_detalhadas' in despesas_raw:
        df_desp = pd.DataFrame(despesas_raw['despesas_detalhadas'])
    elif isinstance(despesas_raw, list):
        df_desp = pd.DataFrame(despesas_raw)
    else:
        # Se os dados estiverem em outra chave ou direto no dict
        df_desp = pd.DataFrame(despesas_raw)

    # 2. Identificação Automática de Colunas
    colunas = df_desp.columns.tolist()

    # Nomes que costumam vir dentro da chave 'despesas_detalhadas'
    c_valor = next(
        (c for c in ['vl_empenhado', 'vlr_empenhado', 'valor'] if c in colunas), None)
    c_credor = next(
        (c for c in ['nm_credor', 'nome_credor', 'credor'] if c in colunas), None)

    # Se ainda não achou, pega por tentativa (comum em APIs Geosiap)
    if not c_valor:
        c_valor = 'vl_empenhado' if 'vl_empenhado' in colunas else colunas[-1]
    if not c_credor:
        c_credor = 'nm_credor' if 'nm_credor' in colunas else colunas[0]

    # 3. Validação e Gráficos
    if c_valor in colunas and c_credor in colunas:
        # Garante que o valor seja numérico
        df_desp[c_valor] = pd.to_numeric(
            df_desp[c_valor], errors='coerce').fillna(0)

    # 3. Validação Final antes de processar
    if c_valor and c_credor:
        # Garante que o valor seja numérico (crucial para o sum)
        df_desp[c_valor] = pd.to_numeric(
            df_desp[c_valor], errors='coerce').fillna(0)

        # KPIs (Cartões de Resumo)
        total_empenhado = df_desp[c_valor].sum()
        maior_gasto = df_desp[c_valor].max()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Empenhado", f"R$ {total_empenhado:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Nº de Despesas", len(df_desp))
        col3.metric("Maior Lançamento", f"R$ {maior_gasto:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")

        col_graph, col_detalhe = st.columns([2, 1])

        with col_graph:
            st.markdown("### 📊 Quem mais recebe recursos?")
            # Agrupamento usando as colunas detectadas
            df_top = df_desp.groupby(c_credor)[c_valor].sum().sort_values(
                ascending=True).tail(10).reset_index()

            fig = px.bar(df_top, x=c_valor, y=c_credor, orientation='h',
                         labels={c_valor: 'Valor (R$)', c_credor: 'Credor'},
                         color=c_valor, color_continuous_scale='Blues', text_auto='.2s')
            st.plotly_chart(fig, use_container_width=True)

        with col_detalhe:
            st.markdown("### 🔍 Detalhes do Credor")
            credor_sel = st.selectbox(
                "Selecione para detalhar:", sorted(df_desp[c_credor].unique()))

            # Filtra os dados do credor selecionado
            detalhes = df_desp[df_desp[c_credor] == credor_sel].iloc[0]

            # Busca data e histórico de forma segura
            c_data = next(
                (c for c in ['dt_documento', 'data', 'dt_emissao'] if c in colunas), colunas[0])
            c_hist = next(
                (c for c in ['ds_historico', 'historico', 'observacao'] if c in colunas), None)

            st.info(f"**Credor:** {detalhes[c_credor]}")
            st.write(f"📅 **Data:** {detalhes[c_data]}")
            st.write(f"💰 **Valor:** R$ {detalhes[c_valor]:,.2f}")
            if c_hist:
                st.write(f"📝 **Histórico:**")
                st.caption(detalhes[c_hist])
    else:
        # Se mesmo assim falhar, mostra as colunas para sabermos o que corrigir
        st.error(
            f"Erro: Não identificamos as colunas de dados. Colunas disponíveis: {colunas}")

# --- SEÇÃO 2: DISPENSAS E INEXIGIBILIDADES ---
st.markdown("---")
st.header("⚖️ Contratações Diretas")
st.write("Processos realizados sem a necessidade de licitação tradicional.")

if dispensas_raw:
    # 1. Tratamento da estrutura (Ajuste para o erro 'dispensas')
    if isinstance(dispensas_raw, dict) and 'dispensas' in dispensas_raw:
        df_disp = pd.DataFrame(dispensas_raw['dispensas'])
    elif isinstance(dispensas_raw, dict) and 'data' in dispensas_raw:
        df_disp = pd.DataFrame(dispensas_raw['data'])
    else:
        df_disp = pd.DataFrame(dispensas_raw)

    # 2. Identificação Dinâmica de Colunas para Dispensas
    cols_disp = df_disp.columns.tolist()
    c_modalidade = next(
        (c for c in ['ds_modalidade', 'modalidade', 'tipo'] if c in cols_disp), None)
    c_objeto = next(
        (c for c in ['ds_objeto', 'objeto', 'descricao'] if c in cols_disp), None)
    c_data_disp = next(
        (c for c in ['dt_processo', 'data', 'dt_abertura'] if c in cols_disp), None)

    if c_modalidade:
        c1, c2 = st.columns([1, 2])

        with c1:
            # Gráfico de Pizza usando a coluna detectada
            fig_pizza = px.pie(
                df_disp,
                names=c_modalidade,
                title="Distribuição de Processos",
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_pizza, use_container_width=True)

        with c2:
            st.markdown("#### Últimos Processos de Dispensa")
            # Criando uma tabela amigável com o que estiver disponível
            colunas_mostrar = [c for c in [c_data_disp,
                                           c_objeto, c_modalidade] if c is not None]
            df_disp_clean = df_disp[colunas_mostrar].copy()

            # Renomear para o cidadão entender
            nomes_amigaveis = {
                c_data_disp: 'Data', c_objeto: 'Objeto/Finalidade', c_modalidade: 'Modalidade'}
            df_disp_clean.rename(columns=nomes_amigaveis, inplace=True)

            st.dataframe(df_disp_clean, use_container_width=True,
                         hide_index=True)
    else:
        st.warning(
            f"Dados de dispensas recebidos, mas o formato é inesperado. Colunas: {cols_disp}")
else:
    st.info("Nenhuma dispensa ou inexigibilidade encontrada para o período.")

st.markdown("---")
st.caption("Fonte: API Geosiap - Portal da Transparência. Dados processados para fins de controle social.")
