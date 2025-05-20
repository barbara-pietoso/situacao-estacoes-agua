import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.title("Monitoramento de Estações Hidrometeorológicas - ANA")

# Número de dias a verificar
dias_verificados = st.slider("Verificar dados dos últimos quantos dias?", 1, 30, 7)

# Entrada dos códigos das estações
codigos_raw = st.text_area("Cole a lista de códigos das estações (um por linha):", height=200)
codigos = [c.strip() for c in codigos_raw.splitlines() if c.strip().isdigit()]

# Botão para atualizar
if st.button("Atualizar painel"):

    data_fim = datetime.today()
    data_inicio = data_fim - timedelta(days=dias_verificados)

    data_inicio_str = data_inicio.strftime("%d/%m/%Y")
    data_fim_str = data_fim.strftime("%d/%m/%Y")

    estacoes_ativas = []
    estacoes_inativas = []

    with st.spinner("Consultando dados da ANA..."):
        for cod in codigos:
            url = f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais?CodEstacao={cod}&DataInicio={data_inicio_str}&DataFim={data_fim_str}"
            r = requests.get(url)
            root = ET.fromstring(r.content)

            # Verifica se há algum dado
            ns = {'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1'}
            dados = root.findall(".//diffgr:diffgram//DadosHidrometereologicos", ns)
            if dados:
                estacoes_ativas.append(cod)
            else:
                estacoes_inativas.append(cod)

    # Exibe contagem
    total = len(codigos)
    n_ativas = len(estacoes_ativas)
    n_inativas = len(estacoes_inativas)

    st.subheader("Resumo geral:")
    st.write(f"Total de estações: **{total}**")
    st.write(f"✅ Ativas: **{n_ativas}** ({n_ativas/total:.0%})")
    st.write(f"⚠️ Inativas: **{n_inativas}** ({n_inativas/total:.0%})")

    # Gráfico de pizza
    fig, ax = plt.subplots()
    ax.pie([n_ativas, n_inativas], labels=["Ativas", "Inativas"], autopct='%1.1f%%', colors=["#4CAF50", "#F44336"])
    st.pyplot(fig)

    # Lista das inativas
    st.subheader("Estações inativas:")
    if estacoes_inativas:
        st.dataframe(pd.DataFrame(estacoes_inativas, columns=["Código da Estação"]))
    else:
        st.success("Todas as estações estão ativas no período informado!")

