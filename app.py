import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import pydeck as pdk

st.set_page_config(page_title="Monitoramento de Estações", layout="wide")

# Função para carregar lista de estações do Google Sheets
@st.cache_data
def carregar_estacoes():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsisgVgYF0i9ZyKyoeQR8hckZ2uSw8lPzJ4k_IfqKQu0GyKuBhb1h7-yeR8eiQJRIWiTNkwCs8a7f3/pub?output=csv"
    df = pd.read_csv(url, dtype={"CÓDIGO FLU - ANA": str})
    return df

df_estacoes = carregar_estacoes()
lista_estacoes = df_estacoes["CÓDIGO FLU - ANA"].dropna().astype(str).tolist()

st.title("🔍 Monitoramento de Estações Hidrometeorológicas")

# Slider de seleção de intervalo
dias = st.slider("Quantos dias antes de hoje deseja consultar?", 1, 30, 7)
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

        resultados = []
        for cod in estacoes_selecionadas:
            status = verificar_atividade(cod, data_inicio, data_fim)
            resultados.append({"Estação": str(cod), "Status": status})

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

        # Gráfico de pizza
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

        # Mapa
        df_estacoes["CÓDIGO FLU - ANA"] = df_estacoes["CÓDIGO FLU - ANA"].astype(str)
        df_resultado["Estação"] = df_resultado["Estação"].astype(str)

        df_mapa = df_resultado.merge(
            df_estacoes[["CÓDIGO FLU - ANA", "Lat", "Long"]],
            left_on="Estação", right_on="CÓDIGO FLU - ANA", how="left"
        ).copy()

        # Conversão para float
        df_mapa["latitude"] = df_mapa["Lat"].str.replace(",", ".", regex=False).astype(float)
        df_mapa["longitude"] = df_mapa["Long"].str.replace(",", ".", regex=False).astype(float)

        if not df_mapa.empty and df_mapa["latitude"].notnull().all() and df_mapa["longitude"].notnull().all():
            df_mapa["color"] = df_mapa["Status"].apply(lambda x: [0, 200, 0] if x == "ativa" else [200, 0, 0])

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_mapa,
                get_position='[longitude, latitude]',
                get_fill_color="color",
                get_radius=3000,
                pickable=True
            )

            view_state = pdk.ViewState(
                latitude=df_mapa["latitude"].mean(),
                longitude=df_mapa["longitude"].mean(),
                zoom=5,
                pitch=0
            )

            st.subheader("🗺️ Mapa das Estações")
            st.pydeck_chart(pdk.Deck(
                map_style="light",
                initial_view_state=view_state,
                layers=[layer],
                tooltip={"text": "Estação: {Estação}\nStatus: {Status}"}
            ))
        else:
            st.warning("Nenhuma estação com coordenadas válidas para exibir no mapa.")

        # Lista de inativas
        if not inativas.empty:
            st.subheader("📋 Estações Inativas ou com Erro")
            st.dataframe(inativas, hide_index=True, use_container_width=True)
        else:
            st.success("Todas as estações consultadas estão ativas.")

        # Botão para baixar relatório
        csv = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar relatório em CSV",
            data=csv,
            file_name="relatorio_estacoes.csv",
            mime="text/csv"
        )


