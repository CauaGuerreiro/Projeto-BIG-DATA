import pandas as pd
import streamlit as st
import dateutil.parser
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px

# === Configurações do Streamlit ===
st.set_page_config(page_title="Traffic Pulse", layout="wide")
st.title("🚦 Traffic Pulse: Dashboard de Acidentes em Petrópolis")

# === 1. Carregar dados ===
@st.cache_data
def carregar_dados():
    # Lendo CSVs com encoding utf-8
    df1 = pd.read_csv("acidentes_petropolis.csv", encoding="utf-8")
    df2 = pd.read_csv("DETRAN PETROPOLIS 2025.csv", encoding="utf-8")
    df3 = pd.read_csv("DETRAN PETROPOLIS 2024.csv", encoding="utf-8")
    df4 = pd.read_csv(
    "DETRAN PETROPOLIS 2023.csv", 
    encoding="utf-8", 
    sep=None, 
    engine="python", 
    on_bad_lines='skip'  # ignora linhas com problemas
)
    df5 = pd.read_csv(
    "DETRAN PETROPOLIS 2022.csv", 
    encoding="utf-8", 
    sep=None, 
    engine="python", 
    on_bad_lines='skip'  # ignora linhas com problemas
)
    df6 = pd.read_csv(
    "DETRAN PETROPOLIS 2021.csv", 
    encoding="utf-8", 
    sep=None, 
    engine="python", 
    on_bad_lines='skip'  # ignora linhas com problemas
)
    df7 = pd.read_csv(
    "DETRAN PETROPOLIS 2020.csv", 
    encoding="utf-8", 
    sep=None, 
    engine="python", 
    on_bad_lines='skip'  # ignora linhas com problemas
)
    # Concatenando todos os dados
    dados = pd.concat([df1, df2, df3, df4, df5, df6, df7], ignore_index=True)

    # Normalizar colunas
    dados.columns = dados.columns.str.lower().str.strip()

    # Renomear colunas
    renomear = {
        "sexo": "genero",
        "sexo_condutor": "genero",
        "sexo_vitima": "genero",
        "veiculo": "tipo_veiculo",
        "tipo de veiculo": "tipo_veiculo"
    }
    dados = dados.rename(columns={k:v for k,v in renomear.items() if k in dados.columns})

    # Conversão de datas
    if "data_inversa" in dados.columns:
        def parse_data(x):
            try:
                return dateutil.parser.parse(str(x), dayfirst=True)
            except:
                return pd.NaT
        dados["data_inversa"] = dados["data_inversa"].apply(parse_data)
    else:
        dados["data_inversa"] = pd.NaT

    # Corrigir vírgulas em colunas numéricas
    for col in ["latitude", "longitude", "mortos", "feridos_leves", "feridos_graves", "pessoas", "veiculos", "km"]:
        if col in dados.columns:
            # Substitui vírgula por ponto e converte para numérico
            dados[col] = pd.to_numeric(dados[col].astype(str).str.replace(",", "."), errors="coerce")
    
    return dados

# Carregar dados
dados = carregar_dados()

# === 2. Filtros sidebar ===
st.sidebar.header("Filtros")
anos = ["Todos"] + sorted(dados["data_inversa"].dt.year.dropna().astype(int).unique().tolist())
ano = st.sidebar.selectbox("Ano", anos)

meses = ["Todos"] + list(range(1,13))
mes = st.sidebar.selectbox("Mês", meses)

bairros = ["Todos"] + sorted(dados["municipio"].dropna().unique())
bairro = st.sidebar.selectbox("Bairro/Local", bairros)

tipos = ["Todos"] + sorted(dados["tipo_acidente"].dropna().unique())
tipo_acidente = st.sidebar.selectbox("Tipo de Acidente", tipos)

# Gênero
if "genero" in dados.columns:
    generos = ["Todos"] + sorted(dados["genero"].dropna().unique())
    genero = st.sidebar.selectbox("Gênero", generos)
else:
    genero = "Todos"

# Tipo veículo
if "tipo_veiculo" in dados.columns:
    veiculos = ["Todos"] + sorted(dados["tipo_veiculo"].dropna().unique())
    tipo_veiculo = st.sidebar.selectbox("Tipo de Veículo", veiculos)
else:
    tipo_veiculo = "Todos"

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
if genero != "Todos" and "genero" in filtro.columns:
    filtro = filtro[filtro["genero"].str.contains(genero, case=False, na=False)]
if tipo_veiculo != "Todos" and "tipo_veiculo" in filtro.columns:
    filtro = filtro[filtro["tipo_veiculo"].str.contains(tipo_veiculo, case=False, na=False)]

if filtro.empty:
    st.warning("⚠ Nenhum dado encontrado com esses filtros.")
    st.stop()

# === 3. Métricas principais ===
total_acidentes = len(filtro)
total_mortos = filtro["mortos"].sum() if "mortos" in filtro.columns else 0
total_feridos_leves = filtro["feridos_leves"].sum() if "feridos_leves" in filtro.columns else 0
total_feridos_graves = filtro["feridos_graves"].sum() if "feridos_graves" in filtro.columns else 0
media_dia = filtro.groupby("data_inversa").size().mean()

st.subheader("📊 Métricas Principais")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Acidentes", total_acidentes)
col2.metric("Mortos", int(total_mortos))
col3.metric("Feridos Leves", int(total_feridos_leves))
col4.metric("Feridos Graves", int(total_feridos_graves))
col5.metric("Média/Dia", round(media_dia,2))

# === 4. Abas ===
tab1, tab2, tab3, tab4 = st.tabs(["📈 Gráficos", "🗺️ Mapa Interativo", "📅 Detalhes", "🚧 Prevenção e Análise"])

# --- Aba Gráficos ---
with tab1:
    st.subheader("📊 Gráficos Interativos")
    # Top 10 locais
    top_locais = filtro["municipio"].value_counts().nlargest(10)
    fig_locais = px.bar(
        top_locais[::-1],
        orientation='h',
        labels={'index':'Local','value':'Nº de Acidentes'},
        title="Top 10 Locais com Mais Acidentes",
        color=top_locais[::-1].values,
        color_continuous_scale='Reds'
    )
    fig_locais.update_layout(showlegend=False)
    st.plotly_chart(fig_locais, use_container_width=True)

    # Acidentes por dia
    acidentes_dia = filtro.groupby("data_inversa").size()
    fig_dia = px.line(
        x=acidentes_dia.index,
        y=acidentes_dia.values,
        markers=True,
        labels={'x':'Data','y':'Nº de Acidentes'},
        title="Acidentes por Dia"
    )
    st.plotly_chart(fig_dia, use_container_width=True)

    # Gráficos categóricos
    col1, col2, col3 = st.columns(3)
    with col1:
        if "tipo_acidente" in filtro.columns:
            tipo_counts = filtro["tipo_acidente"].value_counts().nlargest(10)
            fig_tipo = px.bar(tipo_counts[::-1], orientation='h',
                              labels={'index':'Tipo','value':'Nº de Acidentes'},
                              title="Tipos de Acidentes", color=tipo_counts[::-1].values,
                              color_continuous_scale='Oranges')
            fig_tipo.update_layout(showlegend=False)
            st.plotly_chart(fig_tipo, use_container_width=True)
    with col2:
        if "genero" in filtro.columns:
            genero_counts = filtro["genero"].value_counts()
            fig_genero = px.bar(genero_counts[::-1], orientation='h',
                                labels={'index':'Gênero','value':'Nº de Acidentes'},
                                title="Distribuição por Gênero", color=genero_counts[::-1].values,
                                color_continuous_scale='Purples')
            fig_genero.update_layout(showlegend=False)
            st.plotly_chart(fig_genero, use_container_width=True)
    with col3:
        if "tipo_veiculo" in filtro.columns:
            veic_counts = filtro["tipo_veiculo"].value_counts().nlargest(10)
            fig_veic = px.bar(veic_counts[::-1], orientation='h',
                              labels={'index':'Veículo','value':'Nº de Acidentes'},
                              title="Tipos de Veículo", color=veic_counts[::-1].values,
                              color_continuous_scale='Greens')
            fig_veic.update_layout(showlegend=False)
            st.plotly_chart(fig_veic, use_container_width=True)

# --- Aba Mapa Interativo com Folium ---
with tab2:
    st.subheader("🗺️ Mapa de Acidentes (Folium)")

    if "latitude" in filtro.columns and "longitude" in filtro.columns:
        filtro_map = filtro.dropna(subset=["latitude", "longitude"])
        if not filtro_map.empty:
            mapa = folium.Map(location=[-22.5056, -43.1779], zoom_start=12)
            marker_cluster = MarkerCluster().add_to(mapa)

            for _, row in filtro_map.iterrows():
                lat, lon = row["latitude"], row["longitude"]
                cor = "blue"
                if pd.notna(row.get("mortos")) and row.get("mortos") > 0:
                    cor = "red"
                elif pd.notna(row.get("feridos_graves")) and row.get("feridos_graves") > 0:
                    cor = "orange"

                mortos = int(row.get("mortos") if pd.notna(row.get("mortos")) else 0)
                feridos_graves = int(row.get("feridos_graves") if pd.notna(row.get("feridos_graves")) else 0)
                feridos_leves = int(row.get("feridos_leves") if pd.notna(row.get("feridos_leves")) else 0)

                # Popup bonito e organizado
                popup_text = f"""
                <div style="font-family: Arial; font-size: 13px; line-height: 1.4;">
                    <b style="color: #2F4F4F;">Local:</b> {row.get('municipio') if pd.notna(row.get('municipio')) else 'N/D'}<br>
                    <b style="color: #2F4F4F;">Data:</b> {row.get('data_inversa').strftime('%d/%m/%Y') if pd.notna(row.get('data_inversa')) else 'N/D'}<br>
                    <b style="color: #2F4F4F;">Tipo:</b> {row.get('tipo_acidente') if pd.notna(row.get('tipo_acidente')) else 'N/D'}<br>
                    <b style="color: red;">Mortos:</b> {mortos}<br>
                    <b style="color: orange;">Feridos Graves:</b> {feridos_graves}<br>
                    <b style="color: green;">Feridos Leves:</b> {feridos_leves}
                </div>
                """
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color=cor,
                    fill=True,
                    fill_opacity=0.7,
                    popup=popup_text
                ).add_to(marker_cluster)

            st_folium(mapa, width=900, height=550)
        else:
            st.info("⚠ Nenhum dado de latitude/longitude disponível.")
    else:
        st.info("⚠ Colunas de latitude/longitude ausentes nos dados.")

# --- Aba Tabela ---
with tab3:
    st.subheader("📋 Tabela de Detalhes")
    st.dataframe(filtro.reset_index(drop=True))
    
with tab4:

    # --- Estatísticas Básicas ---
    st.markdown("### 📌 Principais padrões observados no recorte filtrado")

    # 1. Locais críticos
    locais_criticos = filtro["municipio"].value_counts().head(3)

    # 2. Tipos de acidentes
    tipos_criticos = filtro["tipo_acidente"].value_counts().head(3) if "tipo_acidente" in filtro.columns else None

    # ----------------------------
    # 3. HORÁRIOS (CORRIGIDO)
    # ----------------------------
    if "horario" in filtro.columns:

        # Tenta converter vários possíveis formatos
        filtro["horario"] = pd.to_datetime(
            filtro["horario"].astype(str).str.replace(".", ":", regex=False),
            errors="coerce"
        )

        # Extrai apenas a HORA
        filtro["hora"] = filtro["horario"].dt.hour

        # Formata corretamente como 00:00
        filtro["hora_formatada"] = filtro["hora"].apply(lambda x: f"{int(x):02d}:00" if pd.notnull(x) else None)

        # Conta horas
        horarios_criticos = filtro["hora_formatada"].value_counts().head(3)

    else:
        horarios_criticos = None

    # 4. Veículos
    veiculos_criticos = filtro["tipo_veiculo"].value_counts().head(3) if "tipo_veiculo" in filtro.columns else None

    # 5. Gravidade
    total_ferimentos = (filtro["feridos_leves"].sum() if "feridos_leves" in filtro.columns else 0) + \
                       (filtro["feridos_graves"].sum() if "feridos_graves" in filtro.columns else 0)
    total_m = filtro["mortos"].sum() if "mortos" in filtro.columns else 0

    # --- Exibição ---
    if not filtro.empty:
        st.markdown("#### 🧭 Locais com maior incidência:")
        st.write(locais_criticos)

        if tipos_criticos is not None:
            st.markdown("#### 🛑 Tipos de acidentes mais comuns:")
            st.write(tipos_criticos)

        if horarios_criticos is not None:
            st.markdown("#### ⏰ Horários mais perigosos:")
            st.write(horarios_criticos)

        if veiculos_criticos is not None:
            st.markdown("#### 🚗 Veículos mais envolvidos:")
            st.write(veiculos_criticos)

        st.markdown("#### ⚠️ Gravidade geral:")
        st.write(f"- Feridos totais: {total_ferimentos}")
        st.write(f"- Mortes totais: {total_m}")

    # --- Recomendações Automáticas ---
    st.markdown("---")
    st.markdown("### 🛡 Recomendações de Prevenção Baseadas nos Dados")

    recomendacoes = []

    # 1. Locais críticos
    for local, qtd in locais_criticos.items():
        recomendacoes.append(
            f"• **Reforçar sinalização e fiscalização no local '{local}'**, pois apresenta {qtd} acidentes no período analisado."
        )

    # 2. Horários perigosos — agora usando HORA FORMATADA
    if horarios_criticos is not None:
        for hora_fmt, qtd_h in horarios_criticos.items():
            h_int = int(hora_fmt.split(":")[0])
            recomendacoes.append(
                f"• **Atenção redobrada entre {hora_fmt} e {h_int:02d}:59**, faixa com {qtd_h} registros de acidentes."
            )

 # 3. Tipo de acidente
if tipos_criticos is not None:
    for tipo, qtd in tipos_criticos.items():
        tipo_lower = tipo.lower()

        # =====================
        # MEDIDAS ESPECÍFICAS
        # =====================

        if "saída de leito" in tipo_lower or "carroçável" in tipo_lower:
            recomendacoes.append(
                "• Saída de leito carroçável → Instalar defensas metálicas, melhorar iluminação, reforçar sinalização de curvas e revisar pavimento."
            )

        elif "colisão com objeto" in tipo_lower:
            recomendacoes.append(
                "• Colisão com objeto → Remover obstáculos próximos à pista, instalar amortecedores de impacto e melhorar refletividade da sinalização."
            )

        elif "tombamento" in tipo_lower:
            recomendacoes.append(
                "• Tombamento → Reforçar limites de velocidade em curvas, instalar placas de advertência para veículos pesados e melhorar aderência da via."
            )

        elif "colisão" in tipo_lower:
            recomendacoes.append(
                "• Colisões → Revisar limites de velocidade, reforçar faixas de pedestres e ampliar fiscalização."
            )

        # Recomendação geral
        recomendacoes.append(
            f"• '{tipo}' aparece com frequência ({qtd}). Implementar ações específicas de engenharia, fiscalização e educação no trânsito."
        )

# Exibir recomendações
st.markdown("#### ✔ Ações Recomendadas:")
for r in recomendacoes:
    st.markdown(r)
