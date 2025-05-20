import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitoramento de Estações", layout="wide")

# Função para carregar lista de estações do Google Sheets
@st.cache_data
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    return df["CÓDIGO FLU - ANA"].dropna().astype(str).tolist()
    
lista_estacoes = carregar_estacoes()

st.title("🔍 Monitoramento de Estações Hidrometeorológicas")

# Seletor de datas
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data inicial", value=datetime.now() - timedelta(days=7))
with col2:
    data_fim = st.date_input("Data final", value=datetime.now())

# Checkbox para selecionar todas
selecionar_todas = st.checkbox("Selecionar todas as estações", value=True)

# Multiselect com comportamento comprimido
if selecionar_todas:
    estacoes_selecionadas = lista_estacoes
    st.markdown("*Todas as estações selecionadas.*")
else:
    estacoes_selecionadas = st.multiselect(
        "Escolha as estações",
        options=lista_estacoes,
        default=[],
        placeholder="Selecione estações..."
    )

# Botão para iniciar consulta
if st.button("Consultar"):
    with st.spinner("Consultando dados..."):

        def verificar_atividade(codigo, data_inicio, data_fim):
            url = f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
            params = {
                "CodEstacao": codigo,
                "DataInicio": data_inicio.strftime("%d/%m/%Y"),
                "DataFim": data_fim.strftime("%d/%m/%Y")
            }
            try:
                response = requests.get(url, params=params, timeout=10)
                return "ativa" if "<DataHora>" in response.text else "inativa"
            except:
                return "erro"

        resultados = []
        for cod in estacoes_selecionadas:
            status = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estação": cod, "Status": status})

        df_resultado = pd.DataFrame(resultados)

        # Métricas
        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "ativa"]
        inativas = df_resultado[df_resultado["Status"] != "ativa"]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Ativas", f"{len(ativas)} de {total}", delta=f"{(len(ativas)/total)*100:.1f}%")
        with col2:
            st.metric("⚠️ Inativas ou erro", f"{len(inativas)} de {total}", delta=f"{(len(inativas)/total)*100:.1f}%")

        # Gráfico de pizza
        st.subheader("Distribuição de Atividade")
        st.plotly_chart(
            pd.DataFrame({
                "Status": ["Ativa", "Inativa/Erro"],
                "Quantidade": [len(ativas), len(inativas)]
            }).set_index("Status").plot.pie(y="Quantidade", autopct='%1.1f%%', ylabel="").figure,
            use_container_width=True
        )

        # Lista de inativas
        if not inativas.empty:
            st.subheader("📋 Estações Inativas ou com Erro")
            st.dataframe(inativas, hide_index=True, use_container_width=True)
        else:
            st.success("Todas as estações consultadas estão ativas.")
