import pandas as pd
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from streamlit_folium import st_folium

# === Configurações do Streamlit ===
st.set_page_config(page_title="Acidentes em Petrópolis", layout="wide")
st.title("🚦 Dashboard Completo de Acidentes em Petrópolis")

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
    if "data" in dados.columns:
        dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    for col in ["latitude", "longitude", "mortos", "feridos_leves", "feridos_graves"]:
        if col in dados.columns:
            dados[col] = pd.to_numeric(dados[col], errors="coerce")
    return dados

dados = carregar_dados()
st.success("✅ Dados carregados com sucesso!")

# === 2. Mostrar primeiras linhas e colunas ===
st.write("Colunas disponíveis:", list(dados.columns))
st.write("Visualização inicial dos dados:", dados.head())

# === 3. Filtros avançados ===
st.sidebar.header("Filtros")

# Ano
anos = ["Todos"] + sorted(dados["data"].dt.year.dropna().astype(int).unique().tolist())
ano = st.sidebar.selectbox("Ano", anos)

# Mês
meses = ["Todos"] + list(range(1, 13))
mes = st.sidebar.selectbox("Mês", meses)

# Bairro/Local
bairros = ["Todos"] + sorted(dados["local"].dropna().unique())
bairro = st.sidebar.selectbox("Bairro/Local", bairros)

# Tipo de acidente
tipos = ["Todos"] + sorted(dados["tipo_acidente"].dropna().unique())
tipo_acidente = st.sidebar.selectbox("Tipo de Acidente", tipos)

# Condição meteorológica
condicoes = ["Todos"] + sorted(dados["condicao_metereologica"].dropna().unique())
condicao = st.sidebar.selectbox("Condição Meteorológica", condicoes)

# Aplicar filtros
filtro = dados.copy()
if ano != "Todos":
    filtro = filtro[filtro["data"].dt.year == int(ano)]
if mes != "Todos":
    filtro = filtro[filtro["data"].dt.month == int(mes)]
if bairro != "Todos":
    filtro = filtro[filtro["local"].str.contains(bairro, case=False, na=False)]
if tipo_acidente != "Todos":
    filtro = filtro[filtro["tipo_acidente"].str.contains(tipo_acidente, case=False, na=False)]
if condicao != "Todos":
    filtro = filtro[filtro["condicao_metereologica"].str.contains(condicao, case=False, na=False)]

if filtro.empty:
    st.warning("⚠ Nenhum dado encontrado com esses filtros.")
    st.stop()

# === 4. Resumo Estatístico ===
st.subheader("📊 Resumo Estatístico")
total_acidentes = len(filtro)
total_mortos = filtro["mortos"].sum() if "mortos" in filtro.columns else 0
total_feridos_leves = filtro["feridos_leves"].sum() if "feridos_leves" in filtro.columns else 0
total_feridos_graves = filtro["feridos_graves"].sum() if "feridos_graves" in filtro.columns else 0
media_dia = filtro.groupby("data").size().mean() if "data" in filtro.columns else 0

st.metric("Total de Acidentes", total_acidentes)
st.metric("Total de Mortos", total_mortos)
st.metric("Feridos Leves", total_feridos_leves)
st.metric("Feridos Graves", total_feridos_graves)
st.metric("Média de Acidentes por Dia", round(media_dia, 2))

# === 5. Gráficos ===
st.subheader("📈 Gráficos Analíticos")
col1, col2 = st.columns(2)

# Top 10 locais
acidentes_por_local = filtro["local"].value_counts()
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
    if "data" in filtro.columns and not filtro.empty:
        acidentes_por_data = filtro["data"].value_counts().sort_index()
        fig, ax = plt.subplots(figsize=(8,4))
        acidentes_por_data.plot(ax=ax)
        ax.set_xlabel("Data")
        ax.set_ylabel("Quantidade")
        st.pyplot(fig)
    else:
        st.info("Sem dados para gráfico de datas.")

# Dia da semana heatmap
if "dia_semana" in filtro.columns:
    st.subheader("Acidentes por Dia da Semana")
    dia_semana_counts = filtro["dia_semana"].value_counts().reindex(
        ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]
    ).fillna(0)
    fig, ax = plt.subplots(figsize=(8,3))
    sns.heatmap(dia_semana_counts.to_frame().T, annot=True, fmt="g", cmap="Reds", cbar=False, ax=ax)
    st.pyplot(fig)

# Tipo de acidente
if "tipo_acidente" in filtro.columns:
    st.subheader("Distribuição por Tipo de Acidente")
    tipo_counts = filtro["tipo_acidente"].value_counts()
    fig, ax = plt.subplots(figsize=(8,4))
    sns.barplot(x=tipo_counts.index[:10], y=tipo_counts.values[:10], palette="Oranges_r", ax=ax)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    st.pyplot(fig)

# === 6. Mapa interativo ===
st.subheader("🗺️ Mapa Interativo de Acidentes")
if "latitude" in filtro.columns and "longitude" in filtro.columns:
    filtro_map = filtro.dropna(subset=["latitude", "longitude"])
    if not filtro_map.empty:
        mapa = folium.Map(location=[-22.5056, -43.1779], zoom_start=13)

        # Heatmap
        heat_data = [[row["latitude"], row["longitude"]] for _, row in filtro_map.iterrows()]
        HeatMap(heat_data, radius=15).add_to(mapa)

        # Marcadores coloridos por gravidade
        for _, row in filtro_map.iterrows():
            cor = "blue"
            if row.get("mortos", 0) > 0:
                cor = "red"
            elif row.get("feridos_graves", 0) > 0:
                cor = "orange"
            
            popup_text = f"""
            Local: {row.get('local', 'N/D')}<br>
            Data: {row.get('data', 'N/D')}<br>
            Tipo: {row.get('tipo_acidente', 'N/D')}<br>
            Mortos: {row.get('mortos', 0)}<br>
            Feridos Graves: {row.get('feridos_graves', 0)}<br>
            Feridos Leves: {row.get('feridos_leves', 0)}
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=5,
                color=cor,
                fill=True,
                fill_opacity=0.7,
                popup=popup_text
            ).add_to(mapa)

        st_folium(mapa, width=800, height=500)
    else:
        st.info("Sem dados de latitude/longitude para exibir no mapa.")
else:
    st.info("Colunas de latitude/longitude ausentes nos dados.")
