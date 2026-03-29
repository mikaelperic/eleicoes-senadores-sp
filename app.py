import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json

st.set_page_config(
    page_title="Senadores SP — 1994 a 2022",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dados ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_geo():
    gdf = gpd.read_file("dados/senadores_sp_por_zona_ano.gpkg")
    gdf["id"] = gdf["zona"].astype(str) + "_" + gdf["id_municipio"].astype(str)
    return gdf

@st.cache_data
def load_votos():
    return pd.read_parquet("dados/senadores_sp_por_zona_1994_2022_enriquecido.parquet")

gdf_all = load_geo()
df_votos = load_votos()

ANOS = sorted(gdf_all["ano"].unique().tolist())

# Cor por espectro para o card de eleitos
COR_ESPECTRO = {
    "Esquerda":        "#e63946",
    "Centro-esquerda": "#f4a261",
    "Centro":          "#8ecae6",
    "Centro-direita":  "#457b9d",
    "Direita":         "#1d3557",
}

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("Eleições para Senador em São Paulo")
st.caption("Votos por zona eleitoral · 1994 a 2022 · Fonte: Base dos Dados / TSE · Geometrias: CEM/USP")

# ── Seleção de ano (pills) ─────────────────────────────────────────────────────

ano = st.pills(
    "Ano eleitoral",
    options=ANOS,
    default=2022,
    selection_mode="single",
)
if ano is None:
    ano = 2022

# ── Tipo de mapa ───────────────────────────────────────────────────────────────

tipo_mapa = st.radio(
    "Visualizar no mapa:",
    ["Espectro ideológico por zona", "Candidato mais votado por zona"],
    horizontal=True,
)

st.divider()

# ── Dados do ano selecionado ───────────────────────────────────────────────────

gdf = gdf_all[(gdf_all["ano"] == ano) & gdf_all["geometry"].notna()].copy()
df_ano = df_votos[df_votos["ano"] == ano]

# GeoJSON para o Plotly
geojson = json.loads(gdf.to_json())
for i, feature in enumerate(geojson["features"]):
    feature["id"] = gdf.iloc[i]["id"]

centro_sp = {"lat": -22.5, "lon": -48.5}

# ── Layout: mapa | painel de estatísticas ──────────────────────────────────────

col_mapa, col_stats = st.columns([3, 1])

# ── MAPA ───────────────────────────────────────────────────────────────────────

with col_mapa:

    if tipo_mapa == "Espectro ideológico por zona":
        fig_mapa = px.choropleth_map(
            gdf,
            geojson=geojson,
            locations="id",
            color="espectro_medio",
            color_continuous_scale="RdBu",   # vermelho = esquerda, azul = direita
            range_color=[1, 7],
            map_style="open-street-map",
            zoom=5.8,
            center=centro_sp,
            opacity=0.75,
            hover_data={
                "id": False,
                "ZE_NOME": True,
                "MUN_NOME": True,
                "espectro_medio": ":.2f",
                "votos_total": ":,",
            },
            labels={
                "espectro_medio": "Espectro",
                "ZE_NOME": "Zona",
                "MUN_NOME": "Município",
                "votos_total": "Total de votos",
            },
        )
        fig_mapa.update_coloraxes(
            colorbar_title="Espectro",
            colorbar_tickvals=[1, 2, 3, 4, 5, 6, 7],
            colorbar_ticktext=[
                "1 · Extrema esq.",
                "2 · Esquerda",
                "3 · Centro-esq.",
                "4 · Centro",
                "5 · Centro-dir.",
                "6 · Direita",
                "7 · Extrema dir.",
            ],
        )

    else:
        candidatos = sorted(gdf["candidato_mais_votado"].dropna().unique())
        cores = px.colors.qualitative.Set1[:len(candidatos)]
        mapa_cores = dict(zip(candidatos, cores))

        fig_mapa = px.choropleth_map(
            gdf,
            geojson=geojson,
            locations="id",
            color="candidato_mais_votado",
            color_discrete_map=mapa_cores,
            map_style="open-street-map",
            zoom=5.8,
            center=centro_sp,
            opacity=0.75,
            hover_data={
                "id": False,
                "ZE_NOME": True,
                "MUN_NOME": True,
                "candidato_mais_votado": True,
                "partido_mais_votado": True,
                "votos_total": ":,",
            },
            labels={
                "candidato_mais_votado": "Candidato",
                "partido_mais_votado": "Partido",
                "ZE_NOME": "Zona",
                "MUN_NOME": "Município",
                "votos_total": "Total de votos",
            },
        )
        fig_mapa.update_layout(legend_title_text="Candidato mais votado")

    fig_mapa.update_layout(
        height=620,
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_mapa, use_container_width=True)

# ── PAINEL DE ESTATÍSTICAS ─────────────────────────────────────────────────────

with col_stats:

    # ── Senadores eleitos ──────────────────────────────────────────────────────
    eleitos = (
        df_ano[df_ano["resultado"] == "eleito"]
        [["nome_urna", "sigla_partido", "espectro"]]
        .drop_duplicates("nome_urna")
        .reset_index(drop=True)
    )

    n_eleitos = len(eleitos)
    st.subheader(f"{'Senador eleito' if n_eleitos == 1 else 'Senadores eleitos'} — {ano}")

    for _, s in eleitos.iterrows():
        cor = COR_ESPECTRO.get(s["espectro"], "#888888")
        st.markdown(
            f"""
            <div style="
                border-left: 5px solid {cor};
                padding: 8px 12px;
                margin-bottom: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            ">
                <strong style="font-size:15px">{s['nome_urna']}</strong><br>
                <span style="color:#555; font-size:13px">{s['sigla_partido']} · {s['espectro']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Votos por partido ──────────────────────────────────────────────────────
    st.subheader("Votos por partido")

    total_votos = df_ano["votos"].sum()
    por_partido = (
        df_ano.groupby("sigla_partido")["votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    por_partido["pct"] = (por_partido["votos"] / total_votos * 100).round(1)

    fig_bar = px.bar(
        por_partido,
        x="pct",
        y="sigla_partido",
        orientation="h",
        text="pct",
        color="pct",
        color_continuous_scale="Blues",
        labels={"pct": "% dos votos", "sigla_partido": ""},
    )
    fig_bar.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )
    fig_bar.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
        coloraxis_showscale=False,
        height=520,
        margin={"t": 10, "b": 0, "l": 0, "r": 60},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    n_candidatos = df_ano["nome"].nunique()
    n_partidos = df_ano["sigla_partido"].nunique()
    st.caption(
        f"Total de votos válidos: **{total_votos:,}**  \n"
        f"Candidatos: {n_candidatos} · Partidos: {n_partidos}"
    )
