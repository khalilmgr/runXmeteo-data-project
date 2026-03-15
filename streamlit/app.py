import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import load_data

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAÉ Running Dashboard",
    page_icon="🏃",
    layout="wide",
)

COUREURS_COLORS = {
    "Adrien": "#4C9BE8",
    "Nathan": "#E8734C",
    "Khalil": "#4CE87A",
    "Arthur": "#E84C9B",
}

# ── Chargement des données ─────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_data():
    return load_data()

df_all, source = get_data()

# ── Sidebar : filtres ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtres")

    seances_dispo = sorted(df_all["Séance"].unique())
    seance_sel = st.multiselect(
        "Séance(s)",
        options=seances_dispo,
        default=seances_dispo,
    )

    coureurs_dispo = sorted(df_all["Coureur"].unique())
    coureurs_sel = st.multiselect(
        "Coureur(s)",
        options=coureurs_dispo,
        default=coureurs_dispo,
    )

    st.divider()
    st.caption(f"Source : **{source}**")

df = df_all[
    df_all["Séance"].isin(seance_sel) &
    df_all["Coureur"].isin(coureurs_sel)
].copy()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🏃 SAÉ Running — Dashboard")
st.caption("BUT Informatique 2A · IUT Reims-Châlons-Charleville · Parc de Champagne, Reims")
st.divider()

if df.empty:
    st.warning("Aucune donnée pour la sélection en cours.")
    st.stop()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
st.subheader("Vue d'ensemble par coureur")

# On affiche les KPI sur la séance la plus récente sélectionnée
derniere_seance = df["Séance"].max()
df_kpi = df[df["Séance"] == derniere_seance]

cols = st.columns(len(df_kpi))
for i, (_, row) in enumerate(df_kpi.iterrows()):
    with cols[i]:
        coureur = row["Coureur"]
        color = COUREURS_COLORS.get(coureur, "#888")
        st.markdown(
            f"""
            <div style="border-left: 4px solid {color}; padding: 12px 16px; border-radius: 6px; background: #1e1e2e;">
                <h3 style="margin:0; color:{color}">{coureur}</h3>
                <p style="margin:4px 0; font-size:1.1em;">⏱ {row['Allure_str']}</p>
                <p style="margin:2px 0;">🏅 Meilleure : {row['Meilleure_allure_str']}</p>
                <p style="margin:2px 0;">❤️ FC moy : {int(row['FC_moy'])} bpm</p>
                <p style="margin:2px 0;">📏 {row['Distance']} km · {row['Durée_min']:.1f} min</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ── Graphique 1 : Allure moyenne ───────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Allure moyenne (s/km)")
    st.caption("Plus la valeur est basse, plus le coureur est rapide")

    fig = go.Figure()
    for seance in sorted(df["Séance"].unique()):
        d = df[df["Séance"] == seance]
        fig.add_trace(go.Bar(
            name=f"Séance {seance}",
            x=d["Coureur"],
            y=d["Allure_s"],
            text=d["Allure_str"],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Allure : %{text}<extra></extra>",
        ))
    fig.update_layout(
        barmode="group",
        yaxis_title="Secondes/km",
        yaxis=dict(autorange="reversed"),
        showlegend=len(seances_dispo) > 1,
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Graphique 2 : Fréquence cardiaque ─────────────────────────────────────────
with col2:
    st.subheader("Fréquence cardiaque (bpm)")
    st.caption("FC moyenne et maximale par coureur")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="FC moyenne",
        x=df["Coureur"],
        y=df["FC_moy"],
        marker_color=[COUREURS_COLORS.get(c, "#888") for c in df["Coureur"]],
        opacity=0.7,
    ))
    fig2.add_trace(go.Bar(
        name="FC max",
        x=df["Coureur"],
        y=df["FC_max"],
        marker_color=[COUREURS_COLORS.get(c, "#888") for c in df["Coureur"]],
        opacity=1.0,
        marker_pattern_shape="x",
    ))
    fig2.update_layout(
        barmode="group",
        yaxis_title="bpm",
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Graphique 3 : Cadence & Foulée ────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Cadence & Longueur de foulée")
    st.caption("Cadence (pas/min) vs longueur de foulée (m)")

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Cadence moy (pas/min)",
        x=df["Coureur"],
        y=df["Cadence_moy"],
        marker_color=[COUREURS_COLORS.get(c, "#888") for c in df["Coureur"]],
        yaxis="y",
        opacity=0.85,
    ))
    fig3.add_trace(go.Scatter(
        name="Foulée moy (m)",
        x=df["Coureur"],
        y=df["Foulée_moy"],
        mode="markers+lines",
        marker=dict(size=12, color="white", line=dict(width=2, color="gray")),
        yaxis="y2",
    ))
    fig3.update_layout(
        yaxis=dict(title="Cadence (pas/min)"),
        yaxis2=dict(title="Foulée (m)", overlaying="y", side="right"),
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Graphique 4 : Scatter Allure vs FC ────────────────────────────────────────
with col4:
    st.subheader("Allure vs Fréquence cardiaque")
    st.caption("Efficacité cardiovasculaire — idéal : rapide + FC basse")

    fig4 = go.Figure()
    for _, row in df.iterrows():
        coureur = row["Coureur"]
        fig4.add_trace(go.Scatter(
            x=[row["Allure_s"]],
            y=[row["FC_moy"]],
            mode="markers+text",
            name=coureur,
            text=[coureur],
            textposition="top center",
            marker=dict(
                size=18,
                color=COUREURS_COLORS.get(coureur, "#888"),
                line=dict(width=2, color="white"),
            ),
            hovertemplate=(
                f"<b>{coureur}</b><br>"
                f"Allure : {row['Allure_str']}<br>"
                f"FC moy : {int(row['FC_moy'])} bpm<extra></extra>"
            ),
        ))
    fig4.update_layout(
        xaxis_title="Allure (s/km) — plus bas = plus rapide",
        yaxis_title="FC moyenne (bpm)",
        showlegend=False,
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Graphique 5 : Météo (visible seulement si données dispo) ──────────────────
if df["Météo_Temp"].notna().any():
    st.divider()
    st.subheader("Conditions météo pendant les séances")

    col5, col6 = st.columns(2)

    with col5:
        st.caption("Température ressentie (°C)")
        df_meteo = df.drop_duplicates("Séance")[["Séance", "Météo_Temp", "Météo_TempRessentie", "Météo_Humidite", "Météo_Vent"]]
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            name="Temp. réelle",
            x=df_meteo["Séance"].astype(str),
            y=df_meteo["Météo_Temp"],
            marker_color="#5599FF",
        ))
        fig5.add_trace(go.Bar(
            name="Temp. ressentie",
            x=df_meteo["Séance"].astype(str),
            y=df_meteo["Météo_TempRessentie"],
            marker_color="#FF9955",
        ))
        fig5.update_layout(
            barmode="group", yaxis_title="°C", height=300,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col6:
        st.caption("Humidité (%) et vent (km/h)")
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            name="Humidité (%)",
            x=df_meteo["Séance"].astype(str),
            y=df_meteo["Météo_Humidite"],
            marker_color="#44CCAA",
            yaxis="y",
        ))
        fig6.add_trace(go.Scatter(
            name="Vent (km/h)",
            x=df_meteo["Séance"].astype(str),
            y=df_meteo["Météo_Vent"],
            mode="markers+lines",
            marker=dict(size=10, color="white"),
            yaxis="y2",
        ))
        fig6.update_layout(
            yaxis=dict(title="Humidité (%)"),
            yaxis2=dict(title="Vent (km/h)", overlaying="y", side="right"),
            height=300,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig6, use_container_width=True)

# ── Tableau récap ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Tableau récapitulatif")

recap = df[["Coureur", "Séance", "Distance", "Durée_min", "Allure_str",
            "Meilleure_allure_str", "FC_moy", "FC_max",
            "Cadence_moy", "Foulée_moy", "Calories"]].copy()
recap.columns = ["Coureur", "Séance", "Dist. (km)", "Durée (min)", "Allure moy",
                 "Meilleure allure", "FC moy", "FC max",
                 "Cadence", "Foulée (m)", "Calories"]
recap["Durée (min)"] = recap["Durée (min)"].round(2)

st.dataframe(recap.set_index("Coureur"), use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("SAÉ Data Pipeline · BUT Informatique 2A · IUT Reims-Châlons-Charleville · 2025-2026")