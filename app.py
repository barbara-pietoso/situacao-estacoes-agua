import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitoramento de Estações", layout="wide")
st.title("🔎 Monitoramento de Estações Hidrometeorológicas")

# Lista completa de estações
lista_estacoes = [
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
    "76380050", "75230010", "74761000", "87376000", "85590900", "85470010",
    "87317020", "86160010", "76240000", "76741900"
]

# Expander com seleção de estações
with st.expander("🎛️ Estações monitoradas (clique para selecionar)", expanded=False):
    selecionar_todas = st.checkbox("Selecionar todas as estações", value=True)
    if selecionar_todas:
        selecionadas = lista_estacoes
    else:
        selecionadas = st.multiselect(
            "Escolha as estações que deseja visualizar:",
            options=lista_estacoes,
            default=[],
            key="estacoes_selector"
        )

# Seletor de intervalo de tempo
dias = st.slider("Selecione o intervalo de dias para verificar as estações:", 1, 15, 3)
hoje = datetime.today()
data_inicio = hoje - timedelta(days=dias)
data_fim = hoje

st.write(f"🔄 Consultando dados de **{data_inicio.date()}** até **{data_fim.date()}**...")

# Função para verificar se uma estação está ativa
def verificar_estacao(codigo_estacao, data_inicio, data_fim):
    url = f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais?CodEstacao={codigo_estacao}&DataInicio={data_inicio.strftime('%d/%m/%Y')}&DataFim={data_fim.strftime('%d/%m/%Y')}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return False
        root = ET.fromstring(response.content)
        dados = root.findall(".//DadosHidrometereologicos")
        return len(dados) > 0
    except:
        return False

# Verificação
estacoes_ativas = []
estacoes_inativas = []

with st.spinner("🔍 Verificando status das estações..."):
    for codigo in selecionadas:
        if verificar_estacao(codigo, data_inicio, data_fim):
            estacoes_ativas.append(codigo)
        else:
            estacoes_inativas.append(codigo)

# Gráfico com porcentagem
total = len(selecionadas)
ativas = len(estacoes_ativas)
inativas = len(estacoes_inativas)

st.subheader("📊 Status das estações")

col1, col2 = st.columns(2)
with col1:
    st.metric("Ativas", f"{ativas} / {total}", delta=f"{ativas/total*100:.1f}%")
with col2:
    st.metric("Inativas", f"{inativas} / {total}", delta=f"{inativas/total*100:.1f}%", delta_color="inverse")

# Lista das estações inativas
st.subheader("📍 Estações inativas")
if inativas > 0:
    st.dataframe(pd.DataFrame(estacoes_inativas, columns=["Código da Estação"]))
else:
    st.success("✅ Todas as estações selecionadas estão ativas!")

