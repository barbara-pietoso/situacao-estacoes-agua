import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pydeck as pdk
import xml.etree.ElementTree as ET

st.set_page_config(
    page_title="Monitoramento de Estações",
    page_icon=":droplet:",
    layout="wide"
)

# Cabeçalho
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

# Filtros e intervalo de dias
with st.container():
    col_f1, col_f2, col_f3, col_f4, col_dias = st.columns([1, 1, 1, 1, 1])

    with col_f1:
        bacias = df_estacoes["Bacia_Hidrografica"].dropna().unique().tolist()
        bacia_filtrada = st.multiselect("Bacia Hidrográfica", bacias, default=bacias)

    with col_f2:
        municipios = df_estacoes["Municipio"].dropna().unique().tolist()
        municipio_filtrado = st.multiselect("Município", municipios, default=municipios)

    with col_f3:
        cursos = df_estacoes["Curso_Hidrico"].dropna().unique().tolist()
        curso_filtrado = st.multiselect("Curso Hídrico", cursos, default=cursos)

    with col_f4:
        prioridades = df_estacoes["Rede_Prioritaria"].dropna().unique().tolist()
        prioritaria_filtrada = st.multiselect("Rede Prioritária", prioridades, default=prioridades)

    with col_dias:
        dias = st.slider("Dias até hoje", 1, 30, 7)

# Aplicando filtros
df_estacoes_filtrado = df_estacoes[
    df_estacoes["Bacia_Hidrografica"].isin(bacia_filtrada) &
    df_estacoes["Municipio"].isin(municipio_filtrado) &
    df_estacoes["Curso_Hidrico"].isin(curso_filtrado) &
    df_estacoes["Rede_Prioritaria"].isin(prioritaria_filtrada)
]

lista_estacoes = df_estacoes_filtrado["CÓDIGO FLU - ANA"].dropna().astype(str).str.strip().drop_duplicates().tolist()

data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

selecionar_todas = st.checkbox("Selecionar todas as estações", value=True)

if selecionar_todas:
    estacoes_selecionadas = lista_estacoes
else:
    estacoes_selecionadas = st.multiselect("Escolha estações", options=lista_estacoes)

def verificar_atividade(codigo, data_inicio, data_fim):
    url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais"
    params = {
        "CodEstacao": codigo,
        "DataInicio": data_inicio.strftime("%d/%m/%Y"),
        "DataFim": data_fim.strftime("%d/%m/%Y")
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return {"Status": "inativa"}

        root = ET.fromstring(response.content)
        dados = root.findall(".//DadosHidrometereologicos")

        if not dados:
            return {"Status": "sem dados válidos"}

        resultado = {"Status": "sem dados válidos", "Nivel": None, "Vazao": None, "Chuva": None, "UltimaAtualizacao": None}
        datas_validas = []

        for item in dados:
            data_text = item.findtext("DataHora")
            try:
                data = datetime.strptime(data_text, "%Y-%m-%d %H:%M:%S")
            except:
                data = None

            for campo, key in [("NivelFinal", "Nivel"), ("VazaoFinal", "Vazao"), ("ChuvaFinal", "Chuva")]:
                valor = item.findtext(campo)
                qualidade = item.findtext(f"CQ_{campo}")
                if valor and qualidade and "aprovado" in qualidade.lower():
                    resultado[key] = valor
                    if data:
                        datas_validas.append(data)

        if any([resultado["Nivel"], resultado["Vazao"], resultado["Chuva"]]):
            resultado["Status"] = "ativa"
            if datas_validas:
                resultado["UltimaAtualizacao"] = max(datas_validas).strftime("%d/%m/%Y %H:%M")
        return resultado

    except:
        return {"Status": "erro"}

if st.button("Consultar"):
    with st.spinner("Consultando estações..."):
        resultados = []
        total = len(estacoes_selecionadas)
        barra = st.progress(0)

        for i, cod in enumerate(estacoes_selecionadas):
            res = verificar_atividade(cod, data_inicio, data_fim)
            res["Estacao"] = cod
            resultados.append(res)
            barra.progress((i + 1) / total)

    df_res = pd.DataFrame(resultados)
    df_res = df_res.merge(df_estacoes, left_on="Estacao", right_on="CÓDIGO FLU - ANA", how="left")

    df_res["latitude"] = pd.to_numeric(df_res["Lat"].astype(str).str.replace(",", "."), errors="coerce")
    df_res["longitude"] = pd.to_numeric(df_res["Long"].astype(str).str.replace(",", "."), errors="coerce")

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Ativas", str(len(df_res[df_res["Status"] == "ativa"])))
    col2.metric("🟡 Sem Dados Válidos", str(len(df_res[df_res["Status"] == "sem dados válidos"])))
    col3.metric("🔴 Inativas/Erro", str(len(df_res[df_res["Status"].isin(["inativa", "erro"])])))

    st.subheader("🗺️ Mapa das Estações")
    df_mapa = df_res.dropna(subset=["latitude", "longitude"]).copy()

    color_map = {
        "ativa": [115, 175, 72],
        "sem dados válidos": [255, 165, 0],
        "inativa": [184, 43, 43],
        "erro": [169, 169, 169]
    }

    df_mapa["color"] = df_mapa["Status"].map(color_map)

    icon_data = {
        "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
        "width": 128,
        "height": 128,
        "anchorY": 128
    }

    df_mapa["icon_data"] = df_mapa["color"].apply(lambda c: {**icon_data, "tintColor": c})

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/outdoors-v12",
        initial_view_state=pdk.ViewState(
            latitude=-29.5,
            longitude=-53,
            zoom=6.5,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                type="IconLayer",
                data=df_mapa,
                get_icon="icon_data",
                get_size=4,
                size_scale=10,
                get_position=["longitude", "latitude"],
                pickable=True,
            )
        ],
        tooltip={"text": "{Estacao}\nStatus: {Status}\nAtualizado: {UltimaAtualizacao}"}
    ))
