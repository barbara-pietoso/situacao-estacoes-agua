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

# Função para carregar lista de estações do Google Sheets
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

# ✅ Função corrigida para verificar se estação está ativa com base no XML real
def verificar_atividade(codigo, data_inicio, data_fim, debug=False):
    url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
    params = {
        "CodEstacao": codigo,
        "DataInicio": data_inicio.strftime("%d/%m/%Y"),
        "DataFim": data_fim.strftime("%d/%m/%Y")
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            if debug:
                st.write(f"Estação: {codigo}")
                st.code(response.content.decode("utf-8"), language="xml")

            root = ET.fromstring(response.content)
            dados = root.findall(".//DadosHidrometereologicos")
            if not dados:
                return "sem dados válidos"

            for item in dados:
                for campo_base in ["NivelFinal", "VazaoFinal", "ChuvaFinal"]:
                    valor_elem = item.find(f"./{campo_base}")
                    cq_elem = item.find(f"./CQ_{campo_base}")

                    valor = valor_elem.text.strip() if valor_elem is not None and valor_elem.text else None
                    qualidade = cq_elem.text.strip().lower() if cq_elem is not None and cq_elem.text else ""

                    if valor and qualidade == "dado aprovado":
                        return "ativa"

            return "sem dados válidos"
        else:
            return "inativa"
    except Exception as e:
        if debug:
            st.error(f"Erro ao consultar estação {codigo}: {e}")
        return "erro"

# Botão para consulta
if st.button("Consultar"):
    with st.spinner("Consultando dados..."):

        resultados = []
        for cod in estacoes_selecionadas:
            status = verificar_atividade(cod, data_inicio, data_fim, debug=True)
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
        df_resultado["latitude"] = pd.to_numeric(
            df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce"
        )
        df_resultado["longitude"] = pd.to_numeric(
            df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce"
        )

        # Métricas
        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "ativa"]
        sem_dados = df_resultado[df_resultado["Status"] == "sem dados válidos"]
        inativas = df_resultado[df_resultado["Status"] == "inativa"]
        erros = df_resultado[df_resultado["Status"] == "erro"]

        col4, col5 = st.columns(2)
        with col4:
            st.metric("✅ Ativas", f"{len(ativas)} de {total}")
        with col5:
            st.metric(
                "⚠️ Inativas / Sem Dados / Erro",
                f"{len(inativas) + len(sem_dados) + len(erros)} de {total}"
            )

        # Gráfico de pizza
        col6, col7 = st.columns([1, 1])
        with col6:
            st.subheader("📊 Distribuição de Atividade")
            status_data = pd.DataFrame({
                "Status": ["Ativa", "Sem dados válidos", "Inativa", "Erro"],
                "Quantidade": [len(ativas), len(sem_dados), len(inativas), len(erros)]
            })

            fig = px.pie(
                status_data,
                names="Status",
                values="Quantidade",
                title="",
                color="Status",
                color_discrete_map={
                    "Ativa": "#73AF48",
                    "Sem dados válidos": "#FFA500",
                    "Inativa": "#B82B2B",
                    "Erro": "#DAA51B"
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
                    "ativa": [115, 175, 72],
                    "sem dados válidos": [255, 165, 0],
                    "inativa": [184, 43, 43],
                    "erro": [218, 165, 27]
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
        nao_ativas = df_resultado[df_resultado["Status"] != "ativa"]
        if not nao_ativas.empty:
            st.subheader("📋 Estações Não Ativas (sem dados, inativas ou com erro)")
            st.dataframe(
                nao_ativas[["Estacao", "Nome_Estacao", "Status"]],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("Todas as estações consultadas estão ativas.")

        # Botão de download
        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=df_resultado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )


