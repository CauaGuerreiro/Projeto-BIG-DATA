import pandas as pd
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from streamlit_folium import st_folium
import dateutil.parser

# === Configurações do Streamlit ===
st.set_page_config(page_title="Traffic Pulse", layout="wide")
st.title("🚦 Traffic Pulse: Dashboard de Acidentes em Petrópolis")

# === 1. Carregar os dados ===
@st.cache_data
def carregar_dados():
    df1 = pd.read_csv("acidentes_petropolis.csv")
    df2 = pd.read_csv("DETRAN PETROPOLIS 2025.csv")
    df3 = pd.read_csv("DETRAN PETROPOLIS 2024.csv")
    dados = pd.concat([df1, df2, df3], ignore_index=True)
    
    # Normalizar colunas
    dados.columns = dados.columns.str.lower().str.strip()
    
    # Conversão de tipos
    if "data_inversa" in dados.columns:
        def parse_data(x):
            try:
                return dateutil.parser.parse(str(x), dayfirst=True)
            except:
                return pd.NaT
        dados["data_inversa"] = dados["data_inversa"].apply(parse_data)
    
    for col in ["latitude", "longitude", "mortos", "feridos_leves", "feridos_graves"]:
        if col in dados.columns:
            dados[col] = pd.to_numeric(dados[col], errors="coerce")
    
    return dados

dados = carregar_dados()

# === 2. Filtros na sidebar ===
st.sidebar.header("Filtros")

anos = ["Todos"] + sorted(dados["data_inversa"].dt.year.dropna().astype(int).unique().tolist())
ano = st.sidebar.selectbox("Ano", anos)

meses = ["Todos"] + list(range(1, 13))
mes = st.sidebar.selectbox("Mês", meses)

bairros = ["Todos"] + sorted(dados["municipio"].dropna().unique())
bairro = st.sidebar.selectbox("Bairro/Local", bairros)

tipos = ["Todos"] + sorted(dados["tipo_acidente"].dropna().unique())
tipo_acidente = st.sidebar.selectbox("Tipo de Acidente", tipos)

condicoes = ["Todos"] + sorted(dados["condicao_metereologica"].dropna().unique())
condicao = st.sidebar.selectbox("Condição Meteorológica", condicoes)

# Aplicar filtros
filtro = dados.copy()
if ano != "Todos":
    filtro = filtro[filtro["data_inversa"].dt.year == int(ano)]
if mes != "Todos":
    filtro = filtro[filtro["data_inversa"].dt.month == int(mes)]
if bairro != "Todos":
    filtro = filtro[filtro["municipio"].str.contains(bairro, case=False, na=False)]
if tipo_acidente != "Todos":
    filtro = filtro[filtro["tipo_acidente"].str.contains(tipo_acidente, case=False, na=False)]
if condicao != "Todos":
    filtro = filtro[filtro["condicao_metereologica"].str.contains(condicao, case=False, na=False)]

if filtro.empty:
    st.warning("⚠ Nenhum dado encontrado com esses filtros.")
    st.stop()

# === 3. Métricas principais ===
total_acidentes = len(filtro)
total_mortos = filtro["mortos"].sum()
total_feridos_leves = filtro["feridos_leves"].sum()
total_feridos_graves = filtro["feridos_graves"].sum()
media_dia = filtro.groupby("data_inversa").size().mean()

st.subheader("📊 Métricas Principais")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Acidentes", total_acidentes)
col2.metric("Mortos", total_mortos)
col3.metric("Feridos Leves", total_feridos_leves)
col4.metric("Feridos Graves", total_feridos_graves)
col5.metric("Média/Dia", round(media_dia, 2))

# === 4. Abas para gráficos e mapa ===
tab1, tab2, tab3 = st.tabs(["📈 Gráficos", "🗺️ Mapa Interativo", "📅 Detalhes"])

# --- Gráficos ---
with tab1:
    st.subheader("Gráficos Analíticos")
    col1, col2 = st.columns(2)

    # Top 10 locais
    acidentes_por_local = filtro["municipio"].value_counts()
    with col1:
        if not acidentes_por_local.empty:
            fig, ax = plt.subplots(figsize=(8,4))
            sns.barplot(x=acidentes_por_local.index[:10], y=acidentes_por_local.values[:10], palette="Reds_r", ax=ax)
            ax.set_xlabel("Local")
            ax.set_ylabel("Nº de Acidentes")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
            st.pyplot(fig)
        else:
            st.info("Sem dados para gráfico de locais.")

    # Acidentes por dia
    with col2:
        if not filtro.empty:
            acidentes_por_data = filtro["data_inversa"].value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(8,4))
            acidentes_por_data.plot(ax=ax)
            ax.set_xlabel("Data")
            ax.set_ylabel("Quantidade")
            st.pyplot(fig)

    # Tipo de acidente
    if "tipo_acidente" in filtro.columns:
        st.subheader("Distribuição por Tipo de Acidente")
        tipo_counts = filtro["tipo_acidente"].value_counts()
        fig, ax = plt.subplots(figsize=(8,4))
        sns.barplot(x=tipo_counts.index[:10], y=tipo_counts.values[:10], palette="Oranges_r", ax=ax)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
        st.pyplot(fig)

# --- Mapa interativo ---
with tab2:
    st.subheader("Mapa de Acidentes")
    if "latitude" in filtro.columns and "longitude" in filtro.columns:
        filtro_map = filtro.dropna(subset=["latitude", "longitude"])
        if not filtro_map.empty:
            mapa = folium.Map(location=[-22.5056, -43.1779], zoom_start=13)

            # Heatmap
            heat_data = [[row["latitude"], row["longitude"]] for _, row in filtro_map.iterrows()]
            if heat_data:
                HeatMap(heat_data, radius=15).add_to(mapa)

            # Marcadores coloridos
            for _, row in filtro_map.iterrows():
                lat, lon = row["latitude"], row["longitude"]
                cor = "blue"
                if row.get("mortos", 0) > 0:
                    cor = "red"
                elif row.get("feridos_graves", 0) > 0:
                    cor = "orange"

                popup_text = f"""
                <b>Local:</b> {row.get('municipio', 'N/D')}<br>
                <b>Data:</b> {row.get('data_inversa', 'N/D')}<br>
                <b>Tipo:</b> {row.get('tipo_acidente', 'N/D')}<br>
                <b>Mortos:</b> {row.get('mortos', 0)}<br>
                <b>Feridos Graves:</b> {row.get('feridos_graves', 0)}<br>
                <b>Feridos Leves:</b> {row.get('feridos_leves', 0)}
                """
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color=cor,
                    fill=True,
                    fill_opacity=0.7,
                    popup=popup_text
                ).add_to(mapa)

            st_folium(mapa, width=700, height=500)
        else:
            st.info("⚠ Nenhum dado de latitude/longitude disponível.")
    else:
        st.info("⚠ Colunas de latitude/longitude ausentes nos dados.")

# --- Tabela de detalhes ---
with tab3:
    st.subheader("Tabela de Detalhes")
    st.dataframe(filtro.reset_index(drop=True))
