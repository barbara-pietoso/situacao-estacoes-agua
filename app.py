import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="Painel de Estações ANA", layout="wide")
st.title("📡 Monitoramento de Estações Hidrometeorológicas - ANA")

# Lista completa de estações
lista_completa_estacoes = [
    "87241000", "87242020", "87450004", "87318000", "87010000", "87189000",
    "87376000", "87401750", "87333000", "87398750", "87111000", "87228450",
    "87309010", "84420000", "87510015", "88009000", "87510040", "88060210",
    "88060200", "88150900", "88690050", "87390070", "87242000", "87242010",
    "85101000", "87920500", "88365010", "88550010", "88575050", "88700010",
    "79200010", "79400400", "87550050", "87409000", "76220900", "85203000",
    "85623010", "86746900", "85438510", "85734900", "85800000", "85480010",
    "76500040", "76150050", "76660900", "76378900", "76111010", "76290000",
    "77490000", "75400010", "76431995", "75650900", "75650010", "75831000",
    "74270010", "74600900", "75205010", "73100300", "74360010", "74370010",
    "74431000", "87231100", "87350000", "87318510", "87313000", "88050010",
    "85820900", "74100010", "87380000", "86780000", "74329000", "85642005",
    "87317020", "72630900", "87420360", "87237000", "87540010", "88370150",
    "76380050", "75230010", "74761000", "85590900", "85470010", "87317020",
    "86160010", "76240000", "76741900"
]

# Seletor de estações (todas selecionadas por padrão)
estacoes_selecionadas = st.multiselect(
    "🔍 Selecione as estações para análise (todas selecionadas por padrão):",
    options=lista_completa_estacoes,
    default=lista_completa_estacoes
)

# Dias a verificar
dias_verificados = st.slider("📅 Verificar dados dos últimos quantos dias?", 1, 30, 7)

# Botão para atualizar
if st.button("🔄 Atualizar painel") and estacoes_selecionadas:
    data_fim = datetime.today()
    data_inicio = data_fim - timedelta(days=dias_verificados)

    data_inicio_str = data_inicio.strftime("%d/%m/%Y")
    data_fim_str = data_fim.strftime("%d/%m/%Y")

    estacoes_ativas = []
    estacoes_inativas = []

    with st.spinner("🔎 Consultando dados da ANA..."):
        for cod in estacoes_selecionadas:
            url = f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais?CodEstacao={cod}&DataInicio={data_inicio_str}&DataFim={data_fim_str}"
            r = requests.get(url)
            root = ET.fromstring(r.content)

            ns = {'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1'}
            dados = root.findall(".//diffgr:diffgram//DadosHidrometereologicos", ns)

            if dados:
                estacoes_ativas.append(cod)
            else:
                estacoes_inativas.append(cod)

    # Resultados
    total = len(estacoes_selecionadas)
    n_ativas = len(estacoes_ativas)
    n_inativas = len(estacoes_inativas)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Resumo")
        st.write(f"**Total selecionadas:** {total}")
        st.success(f"✅ Ativas: {n_ativas} ({n_ativas/total:.0%})")
        st.error(f"⚠️ Inativas: {n_inativas} ({n_inativas/total:.0%})")

    with col2:
        fig, ax = plt.subplots()
        ax.pie(
            [n_ativas, n_inativas],
            labels=["Ativas", "Inativas"],
            autopct='%1.1f%%',
            colors=["#4CAF50", "#F44336"]
        )
        ax.axis("equal")
        st.pyplot(fig)

    if estacoes_inativas:
        st.subheader("📍 Estações inativas")
        st.dataframe(pd.DataFrame(estacoes_inativas, columns=["Código da Estação"]))
    else:
        st.success("🎉 Todas as estações selecionadas estão ativas!")

else:
    st.info("👈 Selecione estações e clique em **Atualizar painel**.")


