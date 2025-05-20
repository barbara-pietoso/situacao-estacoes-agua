import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Função para consultar a estação na API da ANA
def consultar_dados(cod_estacao, data_inicio, data_fim):
    url = f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais?CodEstacao={cod_estacao}&DataInicio={data_inicio}&DataFim={data_fim}"
    resposta = requests.get(url)
    if resposta.status_code != 200:
        return None
    try:
        root = ET.fromstring(resposta.content)
        dados = root.findall(".//DadosHidrometereologicos")
        return len(dados) > 0
    except:
        return None

# ---------------- Interface Streamlit ----------------
st.set_page_config(page_title="Painel ANA - Estações Ativas", layout="wide")
st.title("🚰 Painel de Monitoramento de Estações da ANA")

st.markdown("Este painel verifica quais estações estão **ativas** nos últimos X dias, consultando a API da ANA em tempo real.")

dias = st.slider("Verificar atividade nos últimos quantos dias?", min_value=1, max_value=30, value=7)
data_fim = datetime.today()
data_inicio = data_fim - timedelta(days=dias)

lista_estacoes = st.text_area(
    "Insira os códigos das estações (um por linha):",
    "87450004\n87410001\n87510000"
)

codigos = [linha.strip() for linha in lista_estacoes.splitlines() if linha.strip()]

status_estacoes = []

with st.spinner("Consultando estações na API da ANA..."):
    for cod in codigos:
        ativo = consultar_dados(cod, data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"))
        status_estacoes.append({
            "Código": cod,
            "Status": "Ativa" if ativo else "Inativa ou sem dados"
        })

df_status = pd.DataFrame(status_estacoes)

st.success(f"Consulta concluída para {len(codigos)} estações.")
st.dataframe(df_status, use_container_width=True)

# Opção de baixar como CSV
csv = df_status.to_csv(index=False).encode("utf-8")
st.download_button("📥 Baixar resultados como CSV", csv, "estacoes_status.csv", "text/csv")

