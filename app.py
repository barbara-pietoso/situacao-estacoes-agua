import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="Monitoramento de Estações", layout="wide")

# Função para carregar lista de estações do Google Sheets
@st.cache_data
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    return df

df_estacoes = carregar_estacoes()
lista_estacoes = df_estacoes["CÓDIGO FLU - ANA"].dropna().astype(str).tolist()

st.title("🔍 Monitoramento de Estações Hidrometeorológicas")

# Seletor com barra deslizante de dias anteriores
dias = st.slider("Selecione o intervalo de dias até hoje", min_value=1, max_value=30, value=7)
data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)
st.markdown(f"📅 Intervalo selecionado: **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**")

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

        # Gráfico
        status_data = pd.DataFrame({
            "Status": ["Ativa", "Inativa/Erro"],
            "Quantidade": [len(ativas), len(inativas)]
        })

        fig = px.pie(
            status_data,
            names="Status",
            values="Quantidade",
            title="Distribuição de Atividade",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4
        )

        fig.update_traces(textinfo='percent+label', pull=[0.05, 0])
        fig.update_layout(
            showlegend=True,
            margin=dict(t=40, b=20),
            height=400
        )

        st.subheader("Distribuição de Atividade")
        st.plotly_chart(fig, use_container_width=True)

        # Junta com coordenadas geográficas
        df_estacoes["CÓDIGO FLU - ANA"] = df_estacoes["CÓDIGO FLU - ANA"].astype(str)
        df_resultado = df_resultado.merge(df_estacoes[["CÓDIGO FLU - ANA", "Lat", "Long"]],
                                          left_on="Estação", right_on="CÓDIGO FLU - ANA", how="left")

        df_mapa = df_resultado.dropna(subset=["Lat", "long"])

        # Mapa interativo
        st.subheader("🗺️ Mapa das Estações Consultadas")
        st.map(df_mapa.rename(columns={"Lat": "latitude", "long": "longitude"}))

        # Tabela de estações inativas
        if not inativas.empty:
            st.subheader("📋 Estações Inativas ou com Erro")
            st.dataframe(inativas, hide_index=True, use_container_width=True)
        else:
            st.success("Todas as estações consultadas estão ativas.")

        # Botão para download de CSV
        csv = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar relatório (.csv)",
            data=csv,
            file_name=f"relatorio_estacoes_{data_inicio.strftime('%Y%m%d')}_a_{data_fim.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
