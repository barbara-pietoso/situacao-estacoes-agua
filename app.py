import streamlit as st
import requests
import xmltodict
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel de Estações Hidrometeorológicas", layout="wide")

# Lista de todas as estações (exemplo reduzido – substitua pela sua lista completa)
lista_estacoes = [
    "87241000", "87242020", "87450004", "87318000", "87010000", "87189000",
    "87376000", "87401750", "87333000", "87398750", "87111000", "87228450",
    "87309010", "84420000", "87510015", "88009000", "87510040", "88060210",
    "88060200", "88150900", "88690050", "87390070", "87242000", "87242010",
    "85101000", "87920500", "88365010", "88550010", "88575050", "88700010",
    "79200010", "79400400", "87550050", "87409000", "76220900", "85203000",
    "85623010", "86746900", "85438510", "85734900", "85800000", "85480010",
    "76500040", "76150050", "76660900", "76378900", "76111010", "76290000",
    "77490000", "75400010", "76431995", "75650900", "75650010", "75831000",
    "74270010", "74600900", "75205010", "73100300", "74360010", "74370010",
    "74431000", "87231100", "87350000", "87318510", "87313000", "88050010",
    "85820900", "74100010", "87380000", "86780000", "74329000", "85642005",
    "87317020", "72630900", "87420360", "87237000", "87540010", "88370150",
    "76380050", "75230010", "74761000", "85590900", "85470010", "87317020",
    "86160010", "76240000", "76741900"
]

# Datas para verificar atividade
data_fim = datetime.today()
data_inicio = data_fim - timedelta(days=7)
data_inicio_str = data_inicio.strftime("%d/%m/%Y")
data_fim_str = data_fim.strftime("%d/%m/%Y")

st.title("📡 Painel de Monitoramento de Estações Hidrometeorológicas")

# Multiselect compacto
selecionadas = st.multiselect(
    "Selecione as estações (clique para editar):",
    options=lista_estacoes,
    default=lista_estacoes,
    label_visibility="collapsed"  # Esconde o rótulo
)

# Texto informativo
if set(selecionadas) == set(lista_estacoes):
    st.markdown("✅ **Todas as estações selecionadas.**")
else:
    st.markdown(f"🔎 **{len(selecionadas)} estações selecionadas.**")

# Consulta função
@st.cache_data(ttl=3600)
def verificar_atividade(estacoes, inicio, fim):
    status = {}
    for cod in estacoes:
        url = (
            f"https://telemetriaws1.ana.gov.br/ServiceANA.asmx/"
            f"DadosHidrometeorologicosGerais?CodEstacao={cod}"
            f"&DataInicio={inicio}&DataFim={fim}"
        )
        try:
            resp = requests.get(url, timeout=10)
            data_dict = xmltodict.parse(resp.content)
            dados = data_dict['DataTable']['diffgr:diffgram']
            ativo = 'DocumentElement' in dados and 'DadosHidrometereologicos' in dados['DocumentElement']
            status[cod] = ativo
        except Exception:
            status[cod] = False
    return status

# Rodando verificação
with st.spinner("🔄 Consultando estações..."):
    status_estacoes = verificar_atividade(selecionadas, data_inicio_str, data_fim_str)

# Análise
ativas = [k for k, v in status_estacoes.items() if v]
inativas = [k for k, v in status_estacoes.items() if not v]
total = len(selecionadas)
perc_ativas = len(ativas) / total * 100 if total else 0
perc_inativas = 100 - perc_ativas

# Gráficos e dados
col1, col2 = st.columns(2)
with col1:
    st.subheader("✅ Estações Ativas")
    st.metric("Quantidade", len(ativas))
    st.progress(perc_ativas / 100)
with col2:
    st.subheader("❌ Estações Inativas")
    st.metric("Quantidade", len(inativas))
    st.progress(perc_inativas / 100)

# Tabela de inativas
st.markdown("### 📄 Lista de Estações Inativas")
if inativas:
    st.dataframe(pd.DataFrame({"Código da Estação": inativas}))
else:
    st.success("Nenhuma estação inativa nos últimos 7 dias!")

# Rodapé
st.caption("Atualizado em " + datetime.now().strftime("%d/%m/%Y %H:%M"))


