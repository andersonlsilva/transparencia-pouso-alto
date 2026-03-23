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

# --- PROCESSAMENTO DE DESPESAS ---
# ... (mantenha a parte do get_data igual) ...

if data_raw and 'despesas_detalhadas' in data_raw:
    df = pd.DataFrame(data_raw['despesas_detalhadas'])
    
    # FORÇA TODAS AS COLUNAS PARA MINÚSCULO (Evita erro de Valor_Empenhado vs valor_empenhado)
    df.columns = [c.lower() for c in df.columns]
    colunas_reais = df.columns.tolist()

    # IDENTIFICAÇÃO FLEXÍVEL (Busca o nome que existir na lista)
    c_valor = next((c for c in ['valor_empenhado', 'vl_empenhado', 'vlr_empenhado', 'valor'] if c in colunas_reais), None)
    c_credor = next((c for c in ['credor', 'nm_credor', 'nome_credor'] if c in colunas_reais), None)
    c_pago = next((c for c in ['vl_pago', 'valor_pago', 'vlr_pago'] if c in colunas_reais), None)
    c_funcao = next((c for c in ['funcao', 'ds_funcao'] if c in colunas_reais), None)

    if c_valor and c_credor:
        # Conversão segura para números
        df[c_valor] = pd.to_numeric(df[c_valor], errors='coerce').fillna(0)
        if c_pago:
            df[c_pago] = pd.to_numeric(df[c_pago], errors='coerce').fillna(0)

        # --- MÉTRICAS TOPO ---
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Empenhado", f"R$ {df[c_valor].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with m2:
            valor_pago_total = df[c_pago].sum() if c_pago else 0
            st.metric("Total Pago", f"R$ {valor_pago_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with m3:
            st.metric("Qtd. de Documentos", len(df))

        st.markdown("---")

        # --- GRÁFICOS (Usando as variáveis detectadas) ---
        col_esq, col_dir = st.columns([2, 1])

        with col_esq:
            st.subheader("🏢 Maiores Recebedores (Credores)")
            df_credor = df.groupby(c_credor)[c_valor].sum().sort_values(ascending=True).tail(10).reset_index()
            fig_cred = px.bar(df_credor, x=c_valor, y=c_credor, orientation='h',
                              color=c_valor, color_continuous_scale='Blues')
            st.plotly_chart(fig_cred, use_container_width=True)

            if c_funcao:
                st.subheader("📂 Gastos por Função (Área)")
                df_funcao = df.groupby(c_funcao)[c_valor].sum().reset_index()
                fig_fun = px.pie(df_funcao, values=c_valor, names=c_funcao, hole=.4)
                st.plotly_chart(fig_fun, use_container_width=True)

        with col_dir:
            st.subheader("🔍 Detalhes por Credor")
            credor_lista = sorted(df[c_credor].unique())
            selecionado = st.selectbox("Selecione um Credor:", ["Escolha..."] + credor_lista)

            if selecionado != "Escolha...":
                detalhe = df[df[c_credor] == selecionado].iloc[0]
                st.success(f"**{selecionado}**")
                # Busca campos adicionais de forma segura
                c_data = next((c for c in ['dt_doc_despesa', 'data', 'dt_documento'] if c in colunas_reais), colunas_reais[0])
                c_hist = next((c for c in ['historico', 'ds_historico'] if c in colunas_reais), None)
                
                st.write(f"📅 **Data:** {detalhe[c_data]}")
                st.write(f"💰 **Valor:** R$ {detalhe[c_valor]:,.2f}")
                if c_hist:
                    st.write(f"📝 **Histórico:**")
                    st.caption(detalhe[c_hist])
    else:
        st.error(f"Não conseguimos mapear as colunas. Disponíveis: {colunas_reais}")
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
