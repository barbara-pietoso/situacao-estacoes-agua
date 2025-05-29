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
    estacoes_selecionadas = st.multiselect(
        "Escolha as estações",
        options=lista_estacoes,
        default=[],
        placeholder="Selecione estações..."
    )

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
                return "Transmitindo - Sem Dados Válidos", []

            registros = []
            for item in dados:
                dt = item.find("DataHora")
                dt = pd.to_datetime(dt.text.strip()) if dt is not None and dt.text else None

                dados_dict = {"Data": dt}
                dado_valido = False

                for campo in ["NivelFinal", "VazaoFinal", "ChuvaFinal"]:
                    valor_elem = item.find(campo)
                    cq_elem = item.find(f"CQ_{campo}")

                    valor = float(valor_elem.text.strip().replace(",", ".")) if valor_elem is not None and valor_elem.text else None
                    qualidade = cq_elem.text.strip().lower() if cq_elem is not None and cq_elem.text else ""

                    if qualidade == "dado aprovado" and valor is not None:
                        dado_valido = True

                    dados_dict[campo] = valor

                registros.append(dados_dict)

            status = "Transmitindo - Dados Válidos" if dado_valido else "Transmitindo - Sem Dados Válidos"
            return status, registros
        else:
            return "Sem transmissão", []
    except:
        return "Erro de leitura", []

if st.button("Consultar"):
    with st.spinner("Consultando estações..."):
        resultados, registros_ativos = [], []
        progresso = st.progress(0)

        for i, cod in enumerate(estacoes_selecionadas):
            status, registros = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estacao": cod, "Status": status})
            if status == "Transmitindo - Dados Válidos" and registros:
                df = pd.DataFrame(registros)
                df["Estacao"] = cod
                registros_ativos.append(df)
            progresso.progress((i + 1) / len(estacoes_selecionadas))

        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.merge(df_estacoes, left_on="Estacao", right_on="CÓDIGO FLU - ANA", how="left")
        df_resultado["latitude"] = pd.to_numeric(df_resultado["Lat"].astype(str).str.replace(",", "."), errors="coerce")
        df_resultado["longitude"] = pd.to_numeric(df_resultado["Long"].astype(str).str.replace(",", "."), errors="coerce")

        total = len(df_resultado)
        ativas = df_resultado[df_resultado["Status"] == "Transmitindo - Dados Válidos"]
        sem_transmissao = df_resultado[df_resultado["Status"] == "Sem transmissão"]
        demais = df_resultado[df_resultado["Status"].isin(["Transmitindo - Sem Dados Válidos", "Erro de leitura"])]

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("📡 Transmitindo - Dados Válidos", len(ativas))
        with col5:
            st.metric("📴 Sem transmissão", len(sem_transmissao))
        with col6:
            st.metric("⚠️ Sem dados válidos / Erro", len(demais))

        st.subheader("📈 Séries Temporais das Estações Ativas")
        if registros_ativos:
            df_series = pd.concat(registros_ativos, ignore_index=True)
            tipo_dado = st.selectbox("Selecione o tipo de dado", ["NivelFinal", "VazaoFinal", "ChuvaFinal"])
            estacoes_visiveis = st.multiselect("Filtrar estações", options=df_series["Estacao"].unique().tolist(), default=df_series["Estacao"].unique().tolist())

            dados_filtrados = df_series[df_series["Estacao"].isin(estacoes_visiveis)]
            fig = px.line(
                dados_filtrados,
                x="Data",
                y=tipo_dado,
                color="Estacao",
                markers=True,
                title=f"{tipo_dado.replace('Final','')} ao longo do tempo",
                labels={"Data": "Data", tipo_dado: tipo_dado.replace("Final", "")}
            )
            fig.update_layout(
                legend_title_text="Estação",
                height=500,
                margin=dict(t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="📥 Baixar dados do gráfico",
                data=dados_filtrados.to_csv(index=False).encode("utf-8"),
                file_name="dados_grafico_estacoes.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhuma estação com dados válidos para exibir.")

        nao_ativas = df_resultado[df_resultado["Status"] != "Transmitindo - Dados Válidos"]
        if not nao_ativas.empty:
            st.subheader("📋 Estações Não Ativas")
            st.dataframe(
                nao_ativas[["Estacao", "Nome_Estacao", "Status"]],
                hide_index=True,
                use_container_width=True
            )

        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=df_resultado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_estacoes_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

