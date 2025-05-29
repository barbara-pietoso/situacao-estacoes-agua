import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import pydeck as pdk
import xml.etree.ElementTree as ET

st.set_page_config(
    page_title="Monitoramento de Estações", 
    page_icon=":droplet:",
    layout="wide"
)

col1, col2, col3 = st.columns([1, 5, 1], vertical_alignment="center")

col3.image('https://raw.githubusercontent.com/barbara-pietoso/situacao-estacoes-agua/main/drhslogo.jpg', width=200)
col2.markdown("<h1 style='text-align: center;'>Monitoramento de Estações Hidrometeorológicas da SEMA - RS</h1>", unsafe_allow_html=True)
col1.image('https://raw.githubusercontent.com/barbara-pietoso/situacao-estacoes-agua/main/EmbeddedImage59bb01f.jpg', width=250)

@st.cache_data(show_spinner=True)
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    df["CÓDIGO FLU - ANA"] = df["CÓDIGO FLU - ANA"].astype(str).str.strip()
    return df

df_estacoes = carregar_estacoes()
lista_estacoes = df_estacoes["CÓDIGO FLU - ANA"].dropna().astype(str).str.strip().drop_duplicates().tolist()

dias = st.slider("Selecione o intervalo de dias até hoje", 1, 30, 7)
data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

selecionar_todas = st.checkbox("Selecionar todas as estações", value=True)
if selecionar_todas:
    estacoes_selecionadas = lista_estacoes
    st.markdown("*Todas as estações selecionadas.*")
else:
    estacoes_selecionadas = st.multiselect("Escolha as estações", options=lista_estacoes, default=[], placeholder="Selecione estações...")

def verificar_atividade(codigo, data_inicio, data_fim):
    url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
    params = {
        "CodEstacao": codigo,
        "DataInicio": data_inicio.strftime("%d/%m/%Y"),
        "DataFim": data_fim.strftime("%d/%m/%Y")
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            dados = root.findall(".//DadosHidrometereologicos")
            if not dados:
                return "Transmitindo - Sem Dados Válidos"
            for item in dados:
                for campo_base in ["NivelFinal", "VazaoFinal", "ChuvaFinal"]:
                    valor_elem = item.find(f"./{campo_base}")
                    cq_elem = item.find(f"./CQ_{campo_base}")
                    valor = valor_elem.text.strip() if valor_elem is not None and valor_elem.text else None
                    qualidade = cq_elem.text.strip().lower() if cq_elem is not None and cq_elem.text else ""
                    if valor and qualidade == "dado aprovado":
                        return "Transmitindo - Dados Válidos"
            return "Transmitindo - Sem Dados Válidos"
        else:
            return "Sem transmissão"
    except:
        return "Erro de leitura"

if st.button("Consultar"):
    with st.spinner("Consultando estações..."):
        resultados = []
        progresso = st.progress(0)
        for i, cod in enumerate(estacoes_selecionadas):
            status = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estacao": str(cod).strip(), "Status": status})
            progresso.progress((i + 1) / len(estacoes_selecionadas))

        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.merge(df_estacoes, left_on="Estacao", right_on="CÓDIGO FLU - ANA", how="left")
        df_resultado["latitude"] = pd.to_numeric(df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce")
        df_resultado["longitude"] = pd.to_numeric(df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce")

        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "Transmitindo - Dados Válidos"]
        sem_dados = df_resultado[df_resultado["Status"] == "Transmitindo - Sem Dados Válidos"]
        inativas = df_resultado[df_resultado["Status"] == "Sem transmissão"]
        erros = df_resultado[df_resultado["Status"] == "Erro de leitura"]

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("✅ Transmitindo - Dados Válidos", f"{len(ativas)} de {total}")
        with col5:
            st.metric("🟡 Transmitindo - Sem Dados Válidos", f"{len(sem_dados)} de {total}")
        with col6:
            st.metric("🔴 Sem Transmissão / Erro", f"{len(inativas) + len(erros)} de {total}")

        col7, col8 = st.columns([1, 1])
        with col7:
            st.subheader("📊 Distribuição de Atividade")
            status_data = pd.DataFrame({
                "Status": [
                    "Transmitindo - Dados Válidos",
                    "Transmitindo - Sem Dados Válidos",
                    "Sem transmissão",
                    "Erro de leitura"
                ],
                "Quantidade": [len(ativas), len(sem_dados), len(inativas), len(erros)]
            })
            fig = px.pie(
                status_data,
                names="Status",
                values="Quantidade",
                hole=0.4,
                color="Status",
                color_discrete_map={
                    "Transmitindo - Dados Válidos": "#73AF48",
                    "Transmitindo - Sem Dados Válidos": "#FFA500",
                    "Sem transmissão": "#B82B2B",
                    "Erro de leitura": "#808080"
                }
            )
            fig.update_traces(textinfo='percent+label', pull=[0.05]*4)
            st.plotly_chart(fig, use_container_width=True)

        with col8:
            df_mapa = df_resultado.dropna(subset=["latitude", "longitude"]).copy()
            if not df_mapa.empty:
                st.subheader("🗺️ Mapa das Estações")
                color_map = {
                    "Transmitindo - Dados Válidos": [115, 175, 72],
                    "Transmitindo - Sem Dados Válidos": [255, 165, 0],
                    "Sem transmissão": [184, 43, 43],
                    "Erro de leitura": [128, 128, 128]
                }
                df_mapa["color"] = df_mapa["Status"].map(color_map)
                layer = pdk.Layer("ScatterplotLayer", data=df_mapa, get_position='[longitude, latitude]', get_color="color", get_radius=5000, pickable=True)
                view_state = pdk.ViewState(latitude=-30.0, longitude=-53.5, zoom=5.5)
                st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{Nome_Estacao} - {Status}"}, map_style="mapbox://styles/mapbox/light-v9"))
            else:
                st.warning("Nenhuma estação com coordenadas válidas para exibir no mapa.")

        nao_ativas = df_resultado[df_resultado["Status"] != "Transmitindo - Dados Válidos"]
        if not nao_ativas.empty:
            st.subheader("📋 Estações Não Ativas (sem dados, inativas ou com erro)")
            st.dataframe(nao_ativas[["Estacao", "Nome_Estacao", "Status"]], hide_index=True, use_container_width=True)
        else:
            st.success("Todas as estações consultadas estão ativas.")

        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=df_resultado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        st.subheader("📈 Séries Temporais das Estações Ativas")
        tipo_dado = st.selectbox("Escolha o tipo de dado para visualizar", options=["NivelFinal", "VazaoFinal", "ChuvaFinal"], format_func=lambda x: {"NivelFinal": "Nível", "VazaoFinal": "Vazão", "ChuvaFinal": "Chuva"}[x])
        tipo_grafico = st.selectbox("Tipo de gráfico", ["Linha", "Área", "Dispersão"])

        estacoes_ativas = ativas["Estacao"].tolist()
        dados_series = []

        with st.spinner("Carregando séries temporais..."):
            for codigo in estacoes_ativas:
                url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
                params = {
                    "CodEstacao": codigo,
                    "DataInicio": data_inicio.strftime("%d/%m/%Y"),
                    "DataFim": data_fim.strftime("%d/%m/%Y")
                }
                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        dados = root.findall(".//DadosHidrometereologicos")
                        for item in dados:
                            datahora_elem = item.find("DataHora")
                            valor_elem = item.find(tipo_dado)
                            qualidade_elem = item.find(f"CQ_{tipo_dado}")
                            if datahora_elem is not None and datahora_elem.text and valor_elem is not None and valor_elem.text and qualidade_elem is not None and qualidade_elem.text.lower().strip() == "dado aprovado":
                                try:
                                    dados_series.append({
                                        "Estacao": codigo,
                                        "DataHora": pd.to_datetime(datahora_elem.text, dayfirst=True),
                                        "Valor": float(valor_elem.text.replace(",", "."))
                                    })
                                except:
                                    pass
                except:
                    continue

        df_series = pd.DataFrame(dados_series)
        if not df_series.empty:
            estacoes_opcoes = df_series["Estacao"].drop_duplicates().tolist()
            estacoes_filtradas = st.multiselect("Filtrar por estação", options=estacoes_opcoes, default=estacoes_opcoes)
            df_plot = df_series[df_series["Estacao"].isin(estacoes_filtradas)]

            if tipo_grafico == "Linha":
                fig = px.line(df_plot, x="DataHora", y="Valor", color="Estacao")
            elif tipo_grafico == "Área":
                fig = px.area(df_plot, x="DataHora", y="Valor", color="Estacao")
            else:
                fig = px.scatter(df_plot, x="DataHora", y="Valor", color="Estacao")

            fig.update_layout(
                title="Séries Temporais das Estações Ativas",
                xaxis_title="Data e Hora",
                yaxis_title=tipo_dado,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="📥 Baixar dados CSV das séries",
                data=df_plot.to_csv(index=False).encode("utf-8"),
                file_name="series_temporais_estacoes_ativas.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum dado disponível para as estações ativas no período selecionado.")

