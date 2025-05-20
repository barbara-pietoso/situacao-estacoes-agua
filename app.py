import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.title("Monitoramento de Estações Hidrometeorológicas - ANA")

# Lista completa de estações (coloque aqui todos os códigos)
lista_completa_estacoes = [
    "87450004", "87410000", "87370000",  # <-- adicione todas as estações aqui
]

# Número de dias a verificar
dias_verificados = st.slider("Verificar dados dos últimos quantos dias?", 1, 30, 7)

# Seletor de estações
estacoes_selecionadas = st.multiselect(
    "Selecione as estações que deseja verificar:",
    options=lista_completa_estacoes,
    default=lista_completa_estacoes
)

# Botão de atualização
if st.button("Atualizar painel") and estacoes_selecionadas:

    data_fim = datetime.today()
    data_inicio = data_fim - timedelta(days=dias_verificados)

    data_inicio_str = data_inicio.strftime("%d/%m/%Y")
    data_fim_str = data_fim.strftime("%d/%m/%Y")

    estacoes_ativas = []
    estacoes_inativas = []

    with st.spinner("Consultando dados da ANA..."):
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

    st.subheader("Resumo:")
    st.write(f"Total selecionadas: **{total}**")
    st.write(f"✅ Ativas: **{n_ativas}** ({n_ativas/total:.0%})")
    st.write(f"⚠️ Inativas: **{n_inativas}** ({n_inativas/total:.0%})")

    # Gráfico
    fig, ax = plt.subplots()
    ax.pie([n_ativas, n_inativas], labels=["Ativas", "Inativas"], autopct='%1.1f%%', colors=["#4CAF50", "#F44336"])
    st.pyplot(fig)

    # Lista de inativas
    if estacoes_inativas:
        st.subheader("Estações inativas:")
        st.dataframe(pd.DataFrame(estacoes_inativas, columns=["Código da Estação"]))
    else:
        st.success("Todas as estações selecionadas estão ativas!")

else:
    st.info("Selecione pelo menos uma estação para iniciar.")


