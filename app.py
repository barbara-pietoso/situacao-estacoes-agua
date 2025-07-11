import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta 
import pydeck as pdk
import xml.etree.ElementTree as ET
import plotly.express as px

st.set_page_config(
    page_title="Monitoramento de Estações", 
    page_icon=":droplet:",
    layout="wide"
)

st.markdown("""
    <style>
    .stMultiSelect [data-baseweb="select"] {
        max-height: 100px;
        overflow-y: auto;
    }
    .stMultiSelect .css-1wa3eu0-placeholder {
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 5, 1], vertical_alignment="center")
col3.image('https://raw.githubusercontent.com/barbara-pietoso/situacao-estacoes-agua/main/drhslogo.jpg', width=200)
col2.markdown("<h1 style='text-align: center;'>Monitoramento de Estações Hidrometeorológicas da SEMA - RS</h1>", unsafe_allow_html=True)
col1.image('https://raw.githubusercontent.com/barbara-pietoso/situacao-estacoes-agua/main/EmbeddedImage59bb01f.jpg', width=250)

@st.cache_data(show_spinner=True)
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url)
    df["CÓDIGO FLU - ANA"] = df["CÓDIGO FLU - ANA"].astype(str).str.strip()
    df["Bacia_Hidrografica"] = df["Bacia_Hidrografica"].fillna("Não informado")
    df["Municipio"] = df["Municipio"].fillna("Não informado")
    df["Curso_Hidrico"] = df["Curso_Hidrico"].fillna("Não informado")
    df["Rede_Prioritaria"] = df["Rede_Prioritaria"].fillna("Não informado")
    return df

df_estacoes = carregar_estacoes()

col_filtros = st.columns([1, 1, 1, 1, 1])

def filtro_multiselect_dropdown(col, label, opcoes, chave):
    selecionados = col.multiselect(
        label,
        opcoes,
        key=chave,
        placeholder=f"Todas as opções selecionadas"
    )
    if not selecionados or set(selecionados) == set(opcoes):
        texto = "Clique na caixa para alterar seleção"
    else:
        texto = f"{len(selecionados)} selecionado(s)"
    col.caption(texto)
    return selecionados if selecionados else opcoes

op_bacias = sorted(df_estacoes["Bacia_Hidrografica"].unique())
op_municipios = sorted(df_estacoes["Municipio"].unique())
op_cursos = sorted(df_estacoes["Curso_Hidrico"].unique())
op_prioritaria = sorted(df_estacoes["Rede_Prioritaria"].unique())

sel_bacias = filtro_multiselect_dropdown(col_filtros[0], "Bacia Hidrográfica", op_bacias, "filtro_bacia")
sel_municipios = filtro_multiselect_dropdown(col_filtros[1], "Município", op_municipios, "filtro_municipio")
sel_cursos = filtro_multiselect_dropdown(col_filtros[2], "Curso Hídrico", op_cursos, "filtro_curso")
sel_prioritaria = filtro_multiselect_dropdown(col_filtros[3], "Rede Prioritária", op_prioritaria, "filtro_prioritaria")

with col_filtros[4]:
    dias = st.slider("Selecione o intervalo de dias até hoje", 1, 30, 7)

df_filtrado = df_estacoes[
    (df_estacoes["Bacia_Hidrografica"].isin(sel_bacias)) &
    (df_estacoes["Municipio"].isin(sel_municipios)) &
    (df_estacoes["Curso_Hidrico"].isin(sel_cursos)) &
    (df_estacoes["Rede_Prioritaria"].isin(sel_prioritaria))
]

lista_estacoes = (
    df_filtrado["CÓDIGO FLU - ANA"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

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

#st.caption(f"{len(lista_estacoes)} estações disponíveis após aplicar filtros.")

data_fim = datetime.now()
data_inicio = data_fim - timedelta(days=dias)

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
                return {"Status": "inativa"}

            valores = {"Nivel": None, "Vazao": None, "Chuva": None, "UltimaAtualizacao": None}
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
                        valores[chave] = valor
                        if data:
                            datas_validas.append(data)

            if any([valores["Nivel"], valores["Vazao"], valores["Chuva"]]):
                if datas_validas:
                    valores["UltimaAtualizacao"] = max(datas_validas).strftime("%d/%m/%Y %H:%M")
                return {"Status": "ativa", **valores}
            else:
                return {"Status": "transmitindo_sem_dados"}
        else:
            return {"Status": "inativa"}
    except:
        return {"Status": "erro"}

if st.button("Consultar"):
    with st.spinner("Consultando estações..."):
        resultados = []
        barra = st.progress(0)
        for i, cod in enumerate(estacoes_selecionadas):
            resultado = verificar_atividade(cod, data_inicio, data_fim)
            resultado["Estacao"] = cod
            resultados.append(resultado)
            barra.progress((i + 1) / len(estacoes_selecionadas))

    df_resultado = pd.DataFrame(resultados)
    # Solução do erro de merge: renomear coluna antes do merge
    df_estacoes_renomeado = df_estacoes.rename(columns={"CÓDIGO FLU - ANA": "Estacao"})
    df_resultado = df_resultado.merge(df_estacoes_renomeado, on="Estacao", how="left")

    df_resultado["latitude"] = pd.to_numeric(df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce")
    df_resultado["longitude"] = pd.to_numeric(df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce")

    ativas = df_resultado[df_resultado["Status"] == "ativa"]
    sem_dados = df_resultado[df_resultado["Status"] == "transmitindo_sem_dados"]
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
        status_data = pd.DataFrame({
            "Status": ["Ativa", "Transmitindo Sem Dados", "Inativa", "Erro"],
            "Quantidade": [len(ativas), len(sem_dados), len(inativas), len(erros)]
        })
        fig = px.pie(
            status_data,
            names="Status",
            values="Quantidade",
            color="Status",
            color_discrete_map={
                "Ativa": "#73AF48",
                "Transmitindo Sem Dados": "#FFA500",
                "Inativa": "#B82B2B",
                "Erro": "#A9A9A9"
            },
            hole=0.4
        )
        fig.update_traces(textinfo='percent+label', pull=[0.05]*4)
        fig.update_layout(showlegend=True, margin=dict(t=20, b=20), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col7:
        df_mapa = df_resultado.dropna(subset=["latitude", "longitude"])
        if not df_mapa.empty:
            st.subheader("🗺️ Mapa das Estações")
            icon_urls = {
                "ativa": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
                "transmitindo_sem_dados": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png",
                "inativa": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
                "erro": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png",
            }
            df_mapa["icon_data"] = df_mapa["Status"].apply(lambda status: {
                "url": icon_urls.get(status, icon_urls["erro"]),
                "width": 25,
                "height": 41,
                "anchorY": 41
            })
            layer = pdk.Layer(
                type="IconLayer",
                data=df_mapa,
                get_icon="icon_data",
                get_position="[longitude, latitude]",
                get_size=4,
                size_scale=5,
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
                map_style="mapbox://styles/mapbox/satellite-streets-v12"
            ))
        else:
            st.warning("Nenhuma estação com coordenadas válidas para exibir no mapa.")

    if not ativas.empty:
        st.subheader("✅ Estações Ativas com Dados Válidos")
        st.dataframe(
            ativas[["Estacao", "Nome_Estacao", "Nivel", "Vazao", "Chuva", "UltimaAtualizacao"]],
            hide_index=True,
            use_container_width=True
        )

    nao_ativas = df_resultado[df_resultado["Status"] != "ativa"]
    if not nao_ativas.empty:
        st.subheader("📋 Estações Não Ativas")
        st.dataframe(
            nao_ativas[["Estacao", "Nome_Estacao", "Status"]],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("Todas as estações consultadas estão ativas.")

    st.download_button(
        label="📥 Baixar Relatório CSV",
        data=df_resultado.to_csv(index=False).encode("utf-8"),
        file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )
