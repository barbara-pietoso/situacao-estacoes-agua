import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import pydeck as pdk

st.set_page_config(page_title="Monitoramento de Estações", 
                   page_icon=":droplet:",
                   layout="wide")

col1, col2, col3 = st.columns([1,5,1], vertical_alignment="center")

col3.image('https://github.com/barbara-pietoso/situacao-estacoes-agua/blob/main/drhslogo.jpg', width=100)
col2.markdown("<h1 style='text-align: center;'>🔍Monitoramento de Estações Hidrometeorológicas da SEMA - RS</h1>", unsafe_allow_html=True)
col1.image('https://github.com/barbara-pietoso/situacao-estacoes-agua/blob/main/EmbeddedImage59bb01f.jpg', width=150)

# Função para carregar lista de estações do Google Sheets
@st.cache_data
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    df["CÓDIGO FLU - ANA"] = df["CÓDIGO FLU - ANA"].astype(str).str.strip()
    return df

df_estacoes = carregar_estacoes()
lista_estacoes = df_estacoes["CÓDIGO FLU - ANA"].dropna().tolist()

# Seletor de datas
dias = st.slider("Selecione o intervalo de dias até hoje", 1, 30, 7)
data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

# Seletor de estações
selecionar_todas = st.checkbox("Selecionar todas as estações", value=True)

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

# Botão para consulta
if st.button("Consultar"):
    with st.spinner("Consultando dados..."):

        def verificar_atividade(codigo, data_inicio, data_fim):
            url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
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

        # Consulta os dados de cada estação
        resultados = []
        for cod in estacoes_selecionadas:
            status = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estacao": str(cod).strip(), "Status": status})

        df_resultado = pd.DataFrame(resultados)

        # Merge com informações das estações
        df_resultado = df_resultado.merge(
            df_estacoes,
            left_on="Estacao",
            right_on="CÓDIGO FLU - ANA",
            how="left"
        )

        # Conversão segura das coordenadas
        df_resultado["latitude"] = pd.to_numeric(df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce")
        df_resultado["longitude"] = pd.to_numeric(df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce")

        # Métricas
        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "ativa"]
        inativas = df_resultado[df_resultado["Status"] != "ativa"]

        col4, col5 = st.columns(2)
        with col4:
            st.metric("✅ Ativas", f"{len(ativas)} de {total}", delta=f"{(len(ativas)/total)*100:.1f}%")
        with col5:
            st.metric("⚠️ Inativas ou erro", f"{len(inativas)} de {total}", delta=f"{(len(inativas)/total)*100:.1f}%")

        # Layout em duas colunas para gráfico + mapa
        col6, col7 = st.columns([1, 1])

        with col6:
            st.subheader("📊 Distribuição de Atividade")
            status_data = pd.DataFrame({
                "Status": ["Ativa", "Inativa/Erro"],
                "Quantidade": [len(ativas), len(inativas)]
            })

            fig = px.pie(
                status_data,
                names="Status",
                values="Quantidade",
                title="",
                color="Status",
                color_discrete_map={
                    "Ativa": "#73AF48",
                    "Inativa/Erro": "#B82B2B"
                },
                hole=0.4
            )
            fig.update_traces(textinfo='percent+label', pull=[0.05, 0])
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col7:
            df_mapa = df_resultado.dropna(subset=["latitude", "longitude"]).copy()
            if not df_mapa.empty:
                st.subheader("🗺️ Mapa das Estações")
                color_map = {"ativa": [115, 175, 72], "inativa": [184, 43, 43], "erro": [218, 165, 27]}
                df_mapa["color"] = df_mapa["Status"].map(color_map)

                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_mapa,
                    get_position='[longitude, latitude]',
                    get_color="color",
                    get_radius=3000,
                    pickable=True
                )

                view_state = pdk.ViewState(
                    latitude=-30.0,
                    longitude=-53.5,
                    zoom=6,
                    pitch=0
                )

                st.pydeck_chart(pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={"text": "{Nome_Estacao} - {Status}"},
                    map_style="mapbox://styles/mapbox/light-v9"
                ))
            else:
                st.warning("Nenhuma estação com coordenadas válidas para exibir no mapa.")

        # Lista de estações inativas
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
