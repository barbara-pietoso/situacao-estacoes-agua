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
lista_estacoes = (
    df_estacoes["CÓDIGO FLU - ANA"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

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

# Função de verificação
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
    except Exception:
        return "Erro de leitura"

# Botão de consulta
if st.button("Consultar"):
    with st.spinner("🔄 Consultando estações..."):
        resultados = []
        progresso = st.progress(0)
        total = len(estacoes_selecionadas)

        for i, cod in enumerate(estacoes_selecionadas):
            status = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estacao": str(cod).strip(), "Status": status})
            progresso.progress((i + 1) / total)

        df_resultado = pd.DataFrame(resultados)

        # Merge com informações das estações
        df_resultado = df_resultado.merge(
            df_estacoes,
            left_on="Estacao",
            right_on="CÓDIGO FLU - ANA",
            how="left"
        )

        # Conversão das coordenadas
        df_resultado["latitude"] = pd.to_numeric(
            df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce"
        )
        df_resultado["longitude"] = pd.to_numeric(
            df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce"
        )

        # Agrupamentos
        total = len(df_resultado)
        status_labels = {
            "Transmitindo - Dados Válidos": "verde",
            "Transmitindo - Sem Dados Válidos": "amarelo",
            "Sem transmissão": "vermelho",
            "Erro de leitura": "cinza"
        }

        ativas = df_resultado[df_resultado["Status"] == "Transmitindo - Dados Válidos"]
        sem_dados = df_resultado[df_resultado["Status"] == "Transmitindo - Sem Dados Válidos"]
        inativas = df_resultado[df_resultado["Status"] == "Sem transmissão"]
        erros = df_resultado[df_resultado["Status"] == "Erro de leitura"]

        col4, col5 = st.columns(2)
        with col4:
            st.metric("✅ Transmitindo com Dados Válidos", f"{len(ativas)} de {total}")
        with col5:
            st.metric(
                "⚠️ Sem Dados / Sem Transmissão / Erro",
                f"{len(sem_dados) + len(inativas) + len(erros)} de {total}"
            )

        # Gráfico de pizza
        col6, col7 = st.columns([1, 1])
        with col6:
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
                color="Status",
                color_discrete_map={
                    "Transmitindo - Dados Válidos": "#73AF48",
                    "Transmitindo - Sem Dados Válidos": "#FFA500",
                    "Sem transmissão": "#B82B2B",
                    "Erro de leitura": "#A9A9A9"
                },
                hole=0.4
            )
            fig.update_traces(textinfo='percent+label', pull=[0.05]*4)
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20), height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Mapa
        with col7:
            df_mapa = df_resultado.dropna(subset=["latitude", "longitude"]).copy()
            if not df_mapa.empty:
                st.subheader("🗺️ Mapa das Estações")
                color_map = {
                    "Transmitindo - Dados Válidos": [115, 175, 72],
                    "Transmitindo - Sem Dados Válidos": [255, 165, 0],
                    "Sem transmissão": [184, 43, 43],
                    "Erro de leitura": [169, 169, 169]
                }
                df_mapa["color"] = df_mapa["Status"].map(color_map)

                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_mapa,
                    get_position='[longitude, latitude]',
                    get_color="color",
                    get_radius=5000,
                    pickable=True
                )

                view_state = pdk.ViewState(
                    latitude=-30.0,
                    longitude=-53.5,
                    zoom=5.5,
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

        # Tabela de estações não ativas
        nao_ativas = df_resultado[df_resultado["Status"] != "Transmitindo - Dados Válidos"]
        if not nao_ativas.empty:
            st.subheader("📋 Estações Não Ativas")
            st.dataframe(
                nao_ativas[["Estacao", "Nome_Estacao", "Status"]],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("Todas as estações consultadas estão transmitindo com dados válidos.")

        # Botão de download
        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=df_resultado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

