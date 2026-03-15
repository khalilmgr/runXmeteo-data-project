import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

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

# ── Chargement & parsing ───────────────────────────────────────────────────────
@st.cache_data
def load_data():
    csv_path = Path(__file__).parent.parent / "Seance1.csv"
    df = pd.read_csv(csv_path)

    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()

    # Extraction du nom du coureur depuis le titre (ex: "Adrien400m" → "Adrien")
    df["Coureur"] = df["Titre"].str.replace(r"400m$", "", regex=True)

    # Conversion durée (HH:MM:SS.s → secondes)
    def duration_to_seconds(s):
        s = str(s).strip()
        parts = s.replace(",", ".").split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except Exception:
            return None

    # Conversion allure (MM:SS/km → secondes/km)
    def pace_to_seconds(s):
        s = str(s).strip()
        parts = s.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return None

    # Conversion des Pas (format "1,116" → 1116)
    def clean_int(s):
        try:
            return int(str(s).replace(",", "").replace(" ", ""))
        except Exception:
            return None

    df["Durée_s"] = df["Durée"].apply(duration_to_seconds)
    df["Durée_min"] = df["Durée_s"] / 60

    df["Allure_s"] = df["Allure moyenne"].apply(pace_to_seconds)
    df["Meilleure_allure_s"] = df["Meilleure allure"].apply(pace_to_seconds)

    df["Distance"] = pd.to_numeric(df["Distance"], errors="coerce")
    df["Calories"] = pd.to_numeric(df["Calories"], errors="coerce")
    df["FC_moy"] = pd.to_numeric(df["Fréquence cardiaque moyenne"], errors="coerce")
    df["FC_max"] = pd.to_numeric(df["Fréquence cardiaque maximale"], errors="coerce")
    df["Cadence_moy"] = pd.to_numeric(df["Cadence de course moyenne"], errors="coerce")
    df["Foulée_moy"] = pd.to_numeric(df["Longueur moyenne des foulées"], errors="coerce")
    df["Puissance_moy"] = pd.to_numeric(df["Puissance moyenne"], errors="coerce")
    df["Puissance_max"] = pd.to_numeric(df["Puissance max."], errors="coerce")
    df["Pas"] = df["Pas"].apply(clean_int)
    df["TE"] = pd.to_numeric(df["TE aérobie"], errors="coerce")

    # Allure lisible (secondes → "MM:SS")
    def seconds_to_pace_str(s):
        if pd.isna(s):
            return "N/A"
        m = int(s) // 60
        sec = int(s) % 60
        return f"{m}:{sec:02d}/km"

    df["Allure_str"] = df["Allure_s"].apply(seconds_to_pace_str)
    df["Meilleure_allure_str"] = df["Meilleure_allure_s"].apply(seconds_to_pace_str)

    return df


df = load_data()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🏃 SAÉ Running — Dashboard Séance 1")
st.caption("Séance 1 · 12 mars 2026 · 3×400m · Parc de Champagne, Reims")
st.divider()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
st.subheader("Vue d'ensemble par coureur")

cols = st.columns(4)
for i, row in df.iterrows():
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

# ── Layout : 2 colonnes ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

# ── Graphique 1 : Allure moyenne ───────────────────────────────────────────────
with col1:
    st.subheader("Allure moyenne (s/km)")
    st.caption("Plus la valeur est basse, plus le coureur est rapide")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Coureur"],
        y=df["Allure_s"],
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
        text=df["Allure_str"],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Allure : %{text}<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title="Secondes/km",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
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
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
        opacity=0.7,
    ))
    fig2.add_trace(go.Bar(
        name="FC max",
        x=df["Coureur"],
        y=df["FC_max"],
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
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

# ── Layout : 2 colonnes ────────────────────────────────────────────────────────
col3, col4 = st.columns(2)

# ── Graphique 3 : Cadence & Foulée ────────────────────────────────────────────
with col3:
    st.subheader("Cadence & Longueur de foulée")
    st.caption("Cadence (pas/min) vs longueur de foulée (m)")

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Cadence moy (pas/min)",
        x=df["Coureur"],
        y=df["Cadence_moy"],
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
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
                color=COUREURS_COLORS[coureur],
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

# ── Graphique 5 : Puissance ────────────────────────────────────────────────────
st.divider()
col5, col6 = st.columns(2)

with col5:
    st.subheader("Puissance moyenne & maximale (W)")
    st.caption("Puissance développée pendant la course")

    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        name="Puissance moy",
        x=df["Coureur"],
        y=df["Puissance_moy"],
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
        opacity=0.7,
    ))
    fig5.add_trace(go.Bar(
        name="Puissance max",
        x=df["Coureur"],
        y=df["Puissance_max"],
        marker_color=[COUREURS_COLORS[c] for c in df["Coureur"]],
        opacity=1.0,
        marker_pattern_shape="/",
    ))
    fig5.update_layout(
        barmode="group",
        yaxis_title="Watts",
        height=320,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

# ── Graphique 6 : Tableau récap ───────────────────────────────────────────────
with col6:
    st.subheader("Tableau récapitulatif")

    recap = df[["Coureur", "Distance", "Durée_min", "Allure_str",
                "Meilleure_allure_str", "FC_moy", "FC_max",
                "Cadence_moy", "Foulée_moy", "Calories"]].copy()
    recap.columns = ["Coureur", "Dist. (km)", "Durée (min)", "Allure moy",
                     "Meilleure allure", "FC moy", "FC max",
                     "Cadence", "Foulée (m)", "Calories"]
    recap["Durée (min)"] = recap["Durée (min)"].round(2)

    st.dataframe(
        recap.set_index("Coureur"),
        use_container_width=True,
        height=320,
    )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("SAÉ Data Pipeline · BUT Informatique 2A · IUT Reims-Châlons-Charleville · 2025-2026")