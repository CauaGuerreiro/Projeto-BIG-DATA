import pandas as pd
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import seaborn as sns
import webbrowser
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox

def processar_acidentes():
    arquivos = glob.glob("*.csv")
    if not arquivos:
        messagebox.showerror("Erro", "Nenhum arquivo CSV encontrado na pasta.")
        return

    # Carregar os dados
    try:
        df1 = pd.read_csv("acidentes_petropolis.csv")
        df2 = pd.read_csv("PRF PETROPOLIS 2025.csv")
        df3 = pd.read_csv("PRF PETROPOLIS 2024.csv")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao ler os arquivos CSV: {e}")
        return

    dados = pd.concat([df1, df2, df3], ignore_index=True)
    dados["data"] = pd.to_datetime(dados["data_inversa"], errors="coerce")

    # Pegar filtros da interface
    ano = entry_ano.get().strip()
    mes = entry_mes.get().strip()
    bairro = entry_bairro.get().strip()

    filtro = dados.copy()
    if ano:
        if not ano.isdigit():
            messagebox.showerror("Erro", "Ano inválido")
            return
        filtro = filtro[filtro["data"].dt.year == int(ano)]

    if mes:
        if not mes.isdigit() or not (1 <= int(mes) <= 12):
            messagebox.showerror("Erro", "Mês inválido")
            return
        filtro = filtro[filtro["data"].dt.month == int(mes)]

    if bairro:
        if "local" not in filtro.columns:
            messagebox.showerror("Erro", "Coluna 'local' não encontrada no arquivo.")
            return
        filtro = filtro[filtro["municipio"].str.contains(bairro, case=False, na=False)]

    if filtro.empty:
        messagebox.showinfo("Resultado", "Nenhum dado encontrado com esses filtros.")
        return

    # Criar pastas para saída
    os.makedirs("graficos", exist_ok=True)
    os.makedirs("mapas", exist_ok=True)

    # Análise estatística
    acidentes_por_local = filtro["local"].value_counts()
    media_dia = filtro.groupby("data").size().mean()

    # Gráfico Top 10 locais
    plt.figure(figsize=(10, 5))
    sns.barplot(x=acidentes_por_local.index[:10], y=acidentes_por_local.values[:10], palette="Reds_r")
    plt.title("Top 10 Locais com Mais Acidentes")
    plt.xlabel("Local")
    plt.ylabel("Nº de Acidentes")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("graficos/grafico_top10_locais.png")
    plt.close()

    # Gráfico por data
    acidentes_por_data = filtro["data"].value_counts().sort_index()
    plt.figure(figsize=(12, 4))
    acidentes_por_data.plot()
    plt.title("Acidentes por Dia")
    plt.xlabel("Data")
    plt.ylabel("Quantidade")
    plt.tight_layout()
    plt.savefig("graficos/grafico_por_data.png")
    plt.close()

    # Criar mapa
    if "latitude" not in filtro.columns or "longitude" not in filtro.columns:
        messagebox.showerror("Erro", "Dados de latitude/longitude ausentes.")
        return

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

    folium.Marker(
        location=[-22.5056, -43.1779],
        popup=f"Média de {media_dia:.2f} acidentes por dia",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(mapa)

    saida_mapa = "mapas/mapa_acidentes.html"
    mapa.save(saida_mapa)

    url_local = 'file://' + os.path.abspath(saida_mapa)
    webbrowser.open(url_local)

    messagebox.showinfo("Sucesso", f"Mapa gerado em: {saida_mapa}")

# Criando interface
root = tk.Tk()
root.title("Análise de Acidentes Petrópolis")
root.geometry("400x250")

tk.Label(root, text="Ano (2024 ou 2025)").pack(pady=5)
entry_ano = tk.Entry(root)
entry_ano.pack()

tk.Label(root, text="Mês (1-12)").pack(pady=5)
entry_mes = tk.Entry(root)
entry_mes.pack()

tk.Label(root, text="Bairro/Local").pack(pady=5)
entry_bairro = tk.Entry(root)
entry_bairro.pack()

btn_rodar = tk.Button(root, text="Gerar Análise e Mapa", command=processar_acidentes)
btn_rodar.pack(pady=20)

root.mainloop()
