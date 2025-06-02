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

# Controles de filtros e intervalo de dias
with st.container():
    col_filtros1, col_filtros2, col_filtros3, col_filtros4, col_dias = st.columns([1, 1, 1, 1, 1])

    with col_filtros1:
        bacias = df_estacoes["Bacia_Hidrografica"].dropna().unique().tolist()
        bacia_filtrada = st.multiselect("Bacia Hidrográfica", bacias, default=bacias)

    with col_filtros2:
        municipios = df_estacoes["Municipio"].dropna().unique().tolist()
        municipio_filtrado = st.multiselect("Município", municipios, default=municipios)

    with col_filtros3:
        cursos = df_estacoes["Curso_Hidrico"].dropna().unique().tolist()
        curso_filtrado = st.multiselect("Curso Hídrico", cursos, default=cursos)

    with col_filtros4:
        opcoes_prioritaria = df_estacoes["Rede_Prioritaria"].dropna().unique().tolist()
        prioritaria_filtrada = st.multiselect("Rede Prioritária", opcoes_prioritaria, default=opcoes_prioritaria)

    with col_dias:
        dias = st.slider("Intervalo de dias até hoje", 1, 30, 7)

# Aplicando filtros ao dataframe base
df_estacoes_filtrado = df_estacoes[
    df_estacoes["Bacia_Hidrografica"].isin(bacia_filtrada) &
    df_estacoes["Municipio"].isin(municipio_filtrado) &
    df_estacoes["Curso_Hidrico"].isin(curso_filtrado) &
    df_estacoes["Rede_Prioritaria"].isin(prioritaria_filtrada)
]

lista_estacoes = (
    df_estacoes_filtrado["CÓDIGO FLU - ANA"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

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

# Função para verificar atividade das estações
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
                return {"Status": "sem dados válidos"}

            valores_aprovados = {
                "Nivel": None,
                "Vazao": None,
                "Chuva": None,
                "UltimaAtualizacao": None
            }

            datas_validas = []

            for item in dados:
                data_text = item.findtext("DataHora")
                try:
                    data = datetime.strptime(data_text, "%Y-%m-%d %H:%M:%S") if data_text else None
                except:
                    data = None

                for campo, chave in [("NivelFinal", "Nivel"), ("VazaoFinal", "Vazao"), ("ChuvaFinal", "Chuva")]:
                    valor = item.findtext(campo)
                    qualidade = item.findtext(f"CQ_{campo}")
                    if valor and qualidade and "aprovado" in qualidade.lower():
                        valores_aprovados[chave] = valor
                        if data:
                            datas_validas.append(data)

            if any([valores_aprovados["Nivel"], valores_aprovados["Vazao"], valores_aprovados["Chuva"]]):
                if datas_validas:
                    ultima_data = max(datas_validas)
                    valores_aprovados["UltimaAtualizacao"] = ultima_data.strftime("%d/%m/%Y %H:%M")
                else:
                    valores_aprovados["UltimaAtualizacao"] = ""
                return {"Status": "ativa", **valores_aprovados}
            else:
                return {"Status": "sem dados válidos"}
        else:
            return {"Status": "inativa"}
    except:
        return {"Status": "erro"}

if st.button("Consultar"):
    with st.spinner("Consultando estações..."):
        resultados = []
        total_estacoes = len(estacoes_selecionadas)
        barra = st.progress(0, text="Consultando estações...")

        for i, cod in enumerate(estacoes_selecionadas):
            resultado = verificar_atividade(cod, data_inicio, data_fim)
            resultado["Estacao"] = str(cod).strip()
            resultados.append(resultado)
            barra.progress((i + 1) / total_estacoes, text="Consultando estações...")

    df_resultado = pd.DataFrame(resultados)

    df_resultado = df_resultado.merge(
        df_estacoes,
        left_on="Estacao",
        right_on="CÓDIGO FLU - ANA",
        how="left"
    )

    df_resultado["latitude"] = pd.to_numeric(
        df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce"
    )
    df_resultado["longitude"] = pd.to_numeric(
        df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce"
    )

    ativas = df_resultado[df_resultado["Status"] == "ativa"]
    sem_dados = df_resultado[df_resultado["Status"] == "sem dados válidos"]
    inativas = df_resultado[df_resultado["Status"] == "inativa"]
    erros = df_resultado[df_resultado["Status"] == "erro"]
    total = len(df_resultado)

    col4, col5, col6 = st.columns(3)
    col4.metric("✅ Transmitindo - Dados Válidos", f"{len(ativas)} de {total}")
    col5.metric("🟡 Transmitindo - Sem Dados Válidos", f"{len(sem_dados)} de {total}")
    col6.metric("🔴 Sem Transmissão / Erro", f"{len(inativas) + len(erros)} de {total}")

    col8, col7 = st.columns([1, 1])
    with col8:
        st.subheader("📊 Distribuição de Atividade")
        import plotly.express as px
        status_data = pd.DataFrame({
            "Status": ["Ativa", "Sem dados válidos", "Inativa", "Erro"],
            "Quantidade": [len(ativas), len(sem_dados), len(inativas), len(erros)]
        })
        fig = px.pie(
            status_data,
            names="Status",
            values="Quantidade",
            color="Status",
            color_discrete_map={
                "Ativa": "#73AF48",
                "Sem dados válidos": "#FFA500",
                "Inativa": "#B82B2B",
                "Erro": "#A9A9A9"
            },
            hole=0.4
        )
        fig.update_traces(textinfo='percent+label', pull=[0.05]*4)
        fig.update_layout(showlegend=True, margin=dict(t=20, b=20), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col7:
        df_mapa = df_resultado.dropna(subset=["latitude", "longitude"]).copy()
        if not df_mapa.empty:
            st.subheader("🗺️ Mapa das Estações")
            color_map = {
                "ativa": [115, 175, 72],
                "sem dados válidos": [255, 165, 0],
                "inativa": [184, 43, 43],
                "erro": [169, 169, 169]
            }
            df_mapa["
::contentReference[oaicite:0]{index=0}
 

