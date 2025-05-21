import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import pydeck as pdk

st.set_page_config(page_title="Monitoramento de Estacoes", layout="wide")

# Função para carregar lista de estações do Google Sheets
@st.cache_data
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    return df

df_estacoes = carregar_estacoes()
df_estacoes["CÓDIGO FLU - ANA"] = df_estacoes["CÓDIGO FLU - ANA"].astype(str)  # 👈 conversão aqui
lista_estacoes = df_estacoes["CÓDIGO FLU - ANA"].dropna().tolist()

st.title("🔍 Monitoramento de Estações Hidrometeorológicas")

# Seletor de datas por barra
dias = st.slider("Selecione o intervalo de dias até hoje", 1, 30, 7)
data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

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
            resultados.append({"Estacao": str(cod), "Status": status})  # 👈 conversão aqui também

        df_resultado = pd.DataFrame(resultados)

        # Merge com coordenadas e outras infos
        df_resultado = df_resultado.merge(
            df_estacoes,
            left_on="Estacao",
            right_on="CÓDIGO FLU - ANA",
            how="left"
        )

        # Conversão segura das coordenadas
        df_resultado["latitude"] = df_resultado["Lat"].astype(str).str.replace(",", ".", regex=False).str.strip()
        df_resultado["longitude"] = df_resultado["Long"].astype(str).str.replace(",", ".", regex=False).str.strip()
        df_resultado["latitude"] = pd.to_numeric(df_resultado["latitude"], errors="coerce")
        df_resultado["longitude"] = pd.to_numeric(df_resultado["longitude"], errors="coerce")

        # Métricas
        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "ativa"]
        inativas = df_resultado[df_resultado["Status"] != "ativa"]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Ativas", f"{len(ativas)} de {total}", delta=f"{(len(ativas)/total)*100:.1f}%")
        with col2:
            st.metric("⚠️ Inativas ou erro", f"{len(inativas)} de {total}", delta=f"{(len(inativas)/total)*100:.1f}%")

        # Gráfico de pizza com Plotly Express
        status_data = pd.DataFrame({
            "Status": ["Ativa", "Inativa/Erro"],
            "Quantidade": [len(ativas), len(inativas)]
        })

        fig = px.pie(
            status_data,
            names="Status",
            values="Quantidade",
            title="Distribuição de Atividade",
            color="Status",
            color_discrete_map={"Ativa": "green", "Inativa/Erro": "red"},
            hole=0.4
        )

        fig.update_traces(textinfo='percent+label', pull=[0.05, 0])
        fig.update_layout(showlegend=True, margin=dict(t=40, b=20), height=400)

        st.subheader("Distribuição de Atividade")
        st.plotly_chart(fig, use_container_width=True)

        # Mapa com Pydeck
        df_mapa = df_resultado.dropna(subset=["latitude", "longitude"])

        if not df_mapa.empty:
            st.subheader("🗌️ Mapa das Estações")
            color_map = {"ativa": [0, 200, 0], "inativa": [200, 0, 0], "erro": [128, 128, 128]}
            df_mapa["color"] = df_mapa["Status"].map(color_map)

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_mapa,
                get_position='[longitude, latitude]',
                get_color="color",
                get_radius=100,
                pickable=True
            )

            view_state = pdk.ViewState(
                latitude=df_mapa["latitude"].mean(),
                longitude=df_mapa["longitude"].mean(),
                zoom=8,
                pitch=0
            )

            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{Nome_Estacao} - {Status}"}))
        else:
            st.warning("Nenhuma estação com coordenadas válidas para exibir no mapa.")

        # Lista de inativas
        if not inativas.empty:
            st.subheader("📋 Estações Inativas ou com Erro")
            st.dataframe(inativas[["Estacao", "Nome_Estacao", "Status"]], hide_index=True, use_container_width=True)
        else:
            st.success("Todas as estações consultadas estão ativas.")

        # Botão de download
        st.download_button(
            label="🔧 Baixar Relatório CSV",
            data=df_resultado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
