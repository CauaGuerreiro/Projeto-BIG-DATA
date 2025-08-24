import pandas as pd
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import seaborn as sns
import webbrowser
import os
import glob

arquivos = glob.glob("*.csv")
print(arquivos)



# === 0. Configurações de saída ===
os.makedirs("graficos", exist_ok=True)
os.makedirs("mapas", exist_ok=True)

# === 1. Carregar os dados ===
df1 = pd.read_csv("acidentes_petropolis.csv")
df2 = pd.read_csv("DETRAN PETROPOLIS 2025.csv")
df3 = pd.read_csv("DETRAN PETROPOLIS 2024.csv")  # Corrigir se o nome for diferente

# Juntando os dados
dados = pd.concat([df1, df2, df3], ignore_index=True)

# Convertendo coluna 'data' para datetime
dados["data"] = pd.to_datetime(dados["data"])

# === 2. Filtros interativos ===
print("\n===== FILTROS DE PESQUISA =====")
ano = input("Digite o ano desejado (ou pressione Enter para todos): ")
mes = input("Digite o mês (1 a 12, ou Enter para todos): ")
bairro = input("Digite um bairro/local (ou Enter para todos): ")

filtro = dados.copy()
if ano:
    if not ano.isdigit():
        print("⚠ Ano inválido.")
        exit()
    filtro = filtro[filtro["data"].dt.year == int(ano)]

if mes:
    if not mes.isdigit() or not (1 <= int(mes) <= 12):
        print("⚠ Mês inválido.")
        exit()
    filtro = filtro[filtro["data"].dt.month == int(mes)]

if bairro:
    filtro = filtro[filtro["local"].str.contains(bairro, case=False, na=False)]

# Verifica se há dados
if filtro.empty:
    print("\n⚠ Nenhum dado encontrado com esses filtros.")
    exit()

# === 3. Análise estatística ===
acidentes_por_local = filtro["local"].value_counts()
media_dia = filtro.groupby("data").size().mean()

print("\nResumo dos acidentes por local:")
print(acidentes_por_local.head())

# === 4. Gráficos ===
plt.figure(figsize=(10, 5))
sns.barplot(x=acidentes_por_local.index[:10], y=acidentes_por_local.values[:10], palette="Reds_r")
plt.title("Top 10 Locais com Mais Acidentes")
plt.xlabel("Local")
plt.ylabel("Nº de Acidentes")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/grafico_top10_locais.png")
plt.close()

acidentes_por_data = filtro["data"].value_counts().sort_index()
plt.figure(figsize=(12, 4))
acidentes_por_data.plot()
plt.title("Acidentes por Dia")
plt.xlabel("Data")
plt.ylabel("Quantidade")
plt.tight_layout()
plt.savefig("graficos/grafico_por_data.png")
plt.close()

# === 5. Criar mapa ===
# Verifica se há colunas latitude e longitude
if "latitude" not in filtro.columns or "longitude" not in filtro.columns:
    print("⚠ Dados de latitude/longitude ausentes.")
    exit()

mapa = folium.Map(location=[-22.5056, -43.1779], zoom_start=13)

heat_data = [[row["latitude"], row["longitude"]] for _, row in filtro.iterrows()]
HeatMap(heat_data, radius=15).add_to(mapa)

for _, row in filtro.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=5,
        color="blue",
        fill=True,
        fill_opacity=0.6,
        popup=f"{row['local']} - {row['data'].date()}"
    ).add_to(mapa)

# Média de acidentes por dia
folium.Marker(
    location=[-22.5056, -43.1779],
    popup=f"Média de {media_dia:.2f} acidentes por dia",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(mapa)

# === 6. Exportar mapa ===
saida_mapa = "mapas/mapa_acidentes.html"
mapa.save(saida_mapa)
print(f"\n✅ Mapa gerado: {saida_mapa}")
webbrowser.open(saida_mapa)
