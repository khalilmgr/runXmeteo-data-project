"""
app.py — SAÉ Running Dashboard
6 pages : Vue d'ensemble | Performance | Biomécanique | Météo | Tête-à-tête | Conditions
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import load_data

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAÉ Running",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "Adrien": "#E53935",
    "Nathan": "#2E7D32",
    "Arthur": "#E65100",
    "Khalil": "#1565C0",
}

# Styles d'axes réutilisables
_AXIS = dict(gridcolor="#2a2a2a", tickcolor="#555", linecolor="#555", zerolinecolor="#333")

def xax(**kwargs):
    return dict(**_AXIS, **kwargs)

def yax(**kwargs):
    return dict(**_AXIS, **kwargs)

# Template de layout Plotly (sans xaxis/yaxis pour éviter les conflits)
LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0", family="monospace", size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#333", borderwidth=1),
    margin=dict(t=50, b=40, l=50, r=30),
    hoverlabel=dict(bgcolor="#1a1a1a", font_color="white", bordercolor="#555"),
)

st.markdown("""
<style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111111; }
    h1, h2, h3 { color: #f0f0f0; font-family: monospace; }
    .stDivider { border-color: #2a2a2a; }
    .stDataFrame { background: #1a1a1a; }
    div[data-testid="stMetric"] { background: #1a1a1a; border: 1px solid #2a2a2a;
                                   border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def pace_str(s):
    if s is None or pd.isna(s):
        return "N/A"
    return f"{int(s)//60}:{int(s)%60:02d}/km"


def add_trendline(fig, x_series, y_series, color="#666", dash="dot"):
    """Ajoute une droite de régression linéaire OLS sur un scatter."""
    mask = pd.notna(x_series) & pd.notna(y_series)
    x_c, y_c = np.array(x_series[mask], dtype=float), np.array(y_series[mask], dtype=float)
    if len(x_c) < 3:
        return
    m, b = np.polyfit(x_c, y_c, 1)
    x_line = np.linspace(x_c.min(), x_c.max(), 100)
    fig.add_trace(go.Scatter(
        x=x_line, y=m * x_line + b,
        mode="lines",
        line=dict(color=color, dash=dash, width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))


def normalize(series, higher_is_better=True, ref_series=None):
    """Normalise une série entre 0 et 100."""
    s = ref_series if ref_series is not None else series
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    if higher_is_better:
        return (series - mn) / (mx - mn) * 100
    return (mx - series) / (mx - mn) * 100


def kpi_card(coureur, allure, meilleure, fc, distance, duree):
    color = COLORS.get(coureur, "#888")
    fc_val = f"{int(fc)} bpm" if not pd.isna(fc) else "N/A"
    return f"""
    <div style="border-left:4px solid {color}; padding:14px 18px; border-radius:8px;
                background:#1a1a1a; margin-bottom:8px;">
        <h3 style="margin:0 0 8px 0; color:{color}; font-family:monospace;">{coureur}</h3>
        <p style="margin:2px 0; color:#e0e0e0; font-size:1.1em;">⏱ <b>{allure}</b></p>
        <p style="margin:2px 0; color:#999;">🏅 Meilleure : {meilleure}</p>
        <p style="margin:2px 0; color:#999;">❤️ FC moy : {fc_val}</p>
        <p style="margin:2px 0; color:#999;">📏 {distance} km · {duree:.1f} min</p>
    </div>"""


# ── Chargement ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_data():
    return load_data()

df_all, source = get_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏃 SAÉ Running")
    st.caption(f"Source : **{source}**")
    st.divider()

    page = st.radio("Navigation", [
        "Vue d'ensemble",
        "Performance",
        "Biomécanique",
        "Météo & Corrélations",
        "Tête-à-tête",
        "Conditions & Contexte",
    ])

    st.divider()
    seances_dispo = sorted(df_all["Séance"].unique())
    seances_sel = st.multiselect("Séance(s)", seances_dispo, default=seances_dispo)

    coureurs_dispo = sorted(df_all["Coureur"].unique())
    coureurs_sel = st.multiselect("Coureur(s)", coureurs_dispo, default=coureurs_dispo)

df = df_all[
    df_all["Séance"].isin(seances_sel) &
    df_all["Coureur"].isin(coureurs_sel)
].copy()

if df.empty:
    st.warning("Aucune donnée pour la sélection en cours.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — VUE D'ENSEMBLE
# ══════════════════════════════════════════════════════════════════════════════
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    derniere_seance = df["Séance"].max()
    df_kpi = df[df["Séance"] == derniere_seance].sort_values("Allure_s")
    date_str = str(df_kpi["Date"].iloc[0]) if "Date" in df_kpi.columns else ""
    st.caption(f"Séance {derniere_seance} · {date_str}")

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    cols = st.columns(len(df_kpi))
    for i, (_, row) in enumerate(df_kpi.iterrows()):
        with cols[i]:
            st.markdown(kpi_card(
                row["Coureur"], row["Allure_str"], row["Meilleure_allure_str"],
                row["FC_moy"], row["Distance"], row["Durée_min"]
            ), unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    # ── Classement horizontal ──────────────────────────────────────────────────
    with col1:
        st.subheader("Classement")
        st.caption("Allure moyenne — plus à gauche = plus rapide")

        df_rank = df_kpi.sort_values("Allure_s", ascending=True)
        fig = go.Figure(go.Bar(
            x=df_rank["Allure_s"],
            y=df_rank["Coureur"],
            orientation="h",
            marker_color=[COLORS.get(c, "#888") for c in df_rank["Coureur"]],
            text=df_rank["Allure_str"],
            textposition="outside",
            textfont=dict(color="white"),
            hovertemplate="<b>%{y}</b><br>Allure : %{text}<extra></extra>",
        ))
        fig.update_layout(
            **LAYOUT, height=280,
            xaxis=dict(**_AXIS, autorange="reversed", title="s/km"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Records personnels ─────────────────────────────────────────────────────
    with col2:
        st.subheader("Records personnels")
        st.caption("Meilleures performances toutes séances confondues")

        records = []
        for coureur in sorted(coureurs_sel):
            dc = df_all[df_all["Coureur"] == coureur]
            if dc.empty:
                continue
            records.append({
                "Coureur": coureur,
                "Meilleure allure": pace_str(dc["Allure_s"].min()),
                "Sprint": pace_str(dc["Meilleure_allure_s"].min()),
                "FC min": f"{int(dc['FC_moy'].min())} bpm" if dc["FC_moy"].notna().any() else "N/A",
                "Foulée max": f"{dc['Foulée_moy'].max():.2f} m" if dc["Foulée_moy"].notna().any() else "N/A",
            })

        if records:
            st.dataframe(
                pd.DataFrame(records).set_index("Coureur"),
                use_container_width=True, height=260,
            )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Performance":
    st.title("Performance")

    col1, col2 = st.columns(2)

    # ── Allure par séance ──────────────────────────────────────────────────────
    with col1:
        st.subheader("Allure moyenne par séance")
        st.caption("Barres groupées par séance — plus bas = plus rapide")

        fig = go.Figure()
        for i, seance in enumerate(sorted(df["Séance"].unique())):
            d = df[df["Séance"] == seance]
            fig.add_trace(go.Bar(
                name=f"Séance {seance}",
                x=d["Coureur"],
                y=d["Allure_s"],
                text=d["Allure_str"],
                textposition="outside",
                textfont=dict(color="white", size=10),
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=0.55 + 0.25 * i,
                hovertemplate="<b>%{x}</b> · S" + str(seance) + "<br>%{text}<extra></extra>",
            ))
        fig.update_layout(
            **LAYOUT, barmode="group", height=380,
            yaxis=dict(**_AXIS, autorange="reversed", title="s/km"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── % Progression ─────────────────────────────────────────────────────────
    with col2:
        st.subheader("Progression vs Séance 1")
        st.caption("% d'amélioration depuis S1 · positif = plus rapide")

        seances_sorted = sorted(df["Séance"].unique())
        if len(seances_sorted) < 2:
            st.info("Nécessite au moins 2 séances.")
        else:
            s1 = df[df["Séance"] == seances_sorted[0]][["Coureur", "Allure_s"]].rename(columns={"Allure_s": "base"})
            prog = df[df["Séance"] > seances_sorted[0]].merge(s1, on="Coureur")
            prog["pct"] = (prog["base"] - prog["Allure_s"]) / prog["base"] * 100

            fig2 = go.Figure()
            for i, seance in enumerate(sorted(prog["Séance"].unique())):
                d = prog[prog["Séance"] == seance].sort_values("Coureur")
                fig2.add_trace(go.Bar(
                    name=f"Séance {seance}",
                    x=d["Coureur"],
                    y=d["pct"],
                    marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                    opacity=0.55 + 0.25 * i,
                    text=[f"{v:+.1f}%" for v in d["pct"]],
                    textposition="outside",
                    textfont=dict(color="white", size=10),
                    hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
                ))
            fig2.add_hline(y=0, line=dict(color="#555", width=1))
            fig2.update_layout(**LAYOUT, barmode="group", height=380, yaxis_title="%")
            st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    # ── Évolution dans le temps ────────────────────────────────────────────────
    with col3:
        st.subheader("Évolution de l'allure")
        st.caption("Progression au fil des séances · pointillés = meilleur résultat personnel")

        fig3 = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance")
            if dc.empty:
                continue
            best = dc["Allure_s"].min()
            color = COLORS.get(coureur, "#888")
            # Ligne de PR en pointillés
            fig3.add_hline(y=best, line=dict(color=color, dash="dot", width=0.8))
            fig3.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Allure_s"],
                name=coureur,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=10, color=color, line=dict(width=2, color="#0d0d0d")),
                text=dc["Allure_str"],
                hovertemplate="<b>%{fullData.name}</b> · S%{x}<br>%{text}<extra></extra>",
            ))
        fig3.update_layout(
            **LAYOUT, height=360,
            xaxis=dict(**_AXIS, title="Séance", dtick=1),
            yaxis=dict(**_AXIS, autorange="reversed", title="s/km"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Heatmap coureur × séance ───────────────────────────────────────────────
    with col4:
        st.subheader("Heatmap performances")
        st.caption("Allure par coureur par séance · vert = rapide · rouge = lent")

        pivot = df.pivot_table(index="Coureur", columns="Séance", values="Allure_s", aggfunc="mean")
        text_piv = df.pivot_table(index="Coureur", columns="Séance", values="Allure_str", aggfunc="first")

        fig4 = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"S{c}" for c in pivot.columns],
            y=pivot.index.tolist(),
            text=text_piv.reindex(index=pivot.index, columns=pivot.columns).values,
            texttemplate="%{text}",
            textfont=dict(color="white", size=13),
            colorscale=[[0, "#1B5E20"], [0.5, "#F9A825"], [1, "#B71C1C"]],
            showscale=True,
            hovertemplate="<b>%{y}</b> · %{x}<br>Allure : %{text}<extra></extra>",
        ))
        fig4.update_layout(**LAYOUT, height=360)
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — BIOMÉCANIQUE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Biomécanique":
    st.title("Biomécanique & Effort")

    # ── Radar normalisé ────────────────────────────────────────────────────────
    st.subheader("Profil athlétique")
    st.caption("Chaque axe normalisé 0–100 sur l'ensemble des données · score élevé = meilleure performance relative")

    RADAR = [
        ("Vitesse",   "Allure_s",      False),
        ("Endurance", "FC_moy",        False),
        ("Cadence",   "Cadence_moy",   True),
        ("Foulée",    "Foulée_moy",    True),
        ("Puissance", "Puissance_moy", True),
    ]
    radar_ok = [(lbl, col, hib) for lbl, col, hib in RADAR
                if col in df.columns and df[col].notna().any()]
    categories = [r[0] for r in radar_ok] + [radar_ok[0][0]]

    fig_r = go.Figure()
    for _, row in df.iterrows():
        coureur, seance = row["Coureur"], row["Séance"]
        vals = []
        for _, col_name, hib in radar_ok:
            v = row.get(col_name)
            if pd.isna(v):
                vals.append(50.0)
                continue
            ref = df_all[col_name].dropna()
            mn, mx = ref.min(), ref.max()
            if mx == mn:
                vals.append(50.0)
            elif hib:
                vals.append((v - mn) / (mx - mn) * 100)
            else:
                vals.append((mx - v) / (mx - mn) * 100)
        vals.append(vals[0])
        color = COLORS.get(coureur, "#888")
        n_seances = df["Séance"].nunique()
        opacity = min(0.12 + 0.12 * (seance - 1), 0.35)

        fig_r.add_trace(go.Scatterpolar(
            r=vals, theta=categories,
            name=f"{coureur} S{seance}",
            line=dict(color=color, width=2),
            fill="toself",
            fillcolor=color,
            opacity=opacity,
        ))
    fig_r.update_layout(
        **LAYOUT,
        polar=dict(
            bgcolor="#1a1a1a",
            radialaxis=dict(visible=True, range=[0, 100], tickcolor="#555",
                            gridcolor="#333", color="#888"),
            angularaxis=dict(tickcolor="#555", gridcolor="#333", color="#e0e0e0"),
        ),
        height=430,
    )
    st.plotly_chart(fig_r, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)

    # ── Scatter cadence vs allure ──────────────────────────────────────────────
    with col1:
        st.subheader("Cadence vs Allure")
        st.caption("Cadence élevée = plus rapide ? · droite = tendance globale")

        fig5 = go.Figure()
        df5 = df.dropna(subset=["Cadence_moy", "Allure_s"])
        for coureur in coureurs_sel:
            dc = df5[df5["Coureur"] == coureur]
            if dc.empty:
                continue
            fig5.add_trace(go.Scatter(
                x=dc["Cadence_moy"], y=dc["Allure_s"],
                name=coureur, mode="markers",
                marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                customdata=list(zip(dc["Allure_str"], dc["Séance"])),
                hovertemplate=f"<b>{coureur}</b> · S%{{customdata[1]}}<br>"
                              f"Cadence : %{{x}} pas/min<br>Allure : %{{customdata[0]}}<extra></extra>",
            ))
        add_trendline(fig5, df5["Cadence_moy"], df5["Allure_s"])
        fig5.update_layout(
            **LAYOUT, height=320,
            xaxis=dict(**_AXIS, title="Cadence (pas/min)"),
            yaxis=dict(**_AXIS, autorange="reversed", title="Allure (s/km)"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ── Scatter foulée vs allure ───────────────────────────────────────────────
    with col2:
        st.subheader("Foulée vs Allure")
        st.caption("Grande foulée = plus rapide ?")

        fig6 = go.Figure()
        df6 = df.dropna(subset=["Foulée_moy", "Allure_s"])
        for coureur in coureurs_sel:
            dc = df6[df6["Coureur"] == coureur]
            if dc.empty:
                continue
            fig6.add_trace(go.Scatter(
                x=dc["Foulée_moy"], y=dc["Allure_s"],
                name=coureur, mode="markers",
                marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                customdata=list(zip(dc["Allure_str"], dc["Séance"])),
                hovertemplate=f"<b>{coureur}</b> · S%{{customdata[1]}}<br>"
                              f"Foulée : %{{x}} m<br>Allure : %{{customdata[0]}}<extra></extra>",
            ))
        add_trendline(fig6, df6["Foulée_moy"], df6["Allure_s"])
        fig6.update_layout(
            **LAYOUT, height=320,
            xaxis=dict(**_AXIS, title="Longueur de foulée (m)"),
            yaxis=dict(**_AXIS, autorange="reversed", title="Allure (s/km)"),
        )
        st.plotly_chart(fig6, use_container_width=True)

    col3, col4 = st.columns(2)

    # ── Indice d'efficacité cardio ─────────────────────────────────────────────
    with col3:
        st.subheader("Efficacité cardiovasculaire")
        st.caption("Allure ÷ FC moy (s/km/bpm) · plus bas = plus efficace")

        df_eff = df.dropna(subset=["Allure_s", "FC_moy"]).copy()
        df_eff["eff"] = df_eff["Allure_s"] / df_eff["FC_moy"]

        fig7 = go.Figure()
        for i, seance in enumerate(sorted(df_eff["Séance"].unique())):
            d = df_eff[df_eff["Séance"] == seance]
            fig7.add_trace(go.Bar(
                name=f"Séance {seance}",
                x=d["Coureur"], y=d["eff"],
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=0.55 + 0.25 * i,
                text=[f"{v:.2f}" for v in d["eff"]],
                textposition="outside",
                textfont=dict(color="white", size=10),
                hovertemplate="<b>%{x}</b><br>Indice : %{text}<extra></extra>",
            ))
        fig7.update_layout(**LAYOUT, barmode="group", height=320, yaxis_title="s/km/bpm")
        st.plotly_chart(fig7, use_container_width=True)

    # ── TE Aérobie ─────────────────────────────────────────────────────────────
    with col4:
        st.subheader("Training Effect aérobie")
        st.caption("Qualité de l'effort Garmin · 0 = aucun effet · 5 = surcharge")

        df_te = df.dropna(subset=["TE"])
        fig8 = go.Figure()
        for i, seance in enumerate(sorted(df_te["Séance"].unique())):
            d = df_te[df_te["Séance"] == seance]
            fig8.add_trace(go.Bar(
                name=f"Séance {seance}",
                x=d["Coureur"], y=d["TE"],
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=0.55 + 0.25 * i,
                text=[f"{v:.1f}" for v in d["TE"]],
                textposition="outside",
                textfont=dict(color="white", size=10),
            ))
        fig8.add_hline(y=3, line=dict(color="#555", dash="dot", width=1),
                       annotation_text="seuil 3", annotation_font_color="#888")
        fig8.update_layout(
            **LAYOUT, barmode="group", height=320,
            yaxis=dict(**_AXIS, range=[0, 5.5], title="TE aérobie"),
        )
        st.plotly_chart(fig8, use_container_width=True)

    # ── Calories corrigées ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Économie de course — Calories/km (corrigées)")
    st.caption(
        "Les données Garmin sont calibrées sur le profil d'Arthur (70 kg). "
        "Les calories sont corrigées par le poids réel de chaque coureur. "
        "Plus bas = plus économe énergétiquement."
    )

    # Poids réels des coureurs
    POIDS = {"Arthur": 70, "Khalil": 80, "Adrien": 64, "Nathan": 76}
    POIDS_REF = 70  # poids du profil Garmin (Arthur)

    df_cal = df.dropna(subset=["Calories", "Distance"]).copy()
    df_cal = df_cal[df_cal["Distance"] > 0].copy()
    df_cal["facteur"] = df_cal["Coureur"].map(lambda c: POIDS.get(c, POIDS_REF) / POIDS_REF)
    df_cal["cal_km_brut"]    = df_cal["Calories"] / df_cal["Distance"]
    df_cal["cal_km_corrige"] = df_cal["cal_km_brut"] * df_cal["facteur"]

    col_cal1, col_cal2 = st.columns(2)

    with col_cal1:
        st.caption("Calories brutes/km (données Garmin telles quelles)")
        fig_cb = go.Figure()
        for i, seance in enumerate(sorted(df_cal["Séance"].unique())):
            d = df_cal[df_cal["Séance"] == seance]
            fig_cb.add_trace(go.Bar(
                name=f"Séance {seance}",
                x=d["Coureur"], y=d["cal_km_brut"],
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=0.55 + 0.25 * i,
                text=[f"{v:.0f}" for v in d["cal_km_brut"]],
                textposition="outside",
                textfont=dict(color="white", size=10),
                hovertemplate="<b>%{x}</b><br>%{text} kcal/km<extra></extra>",
            ))
        fig_cb.update_layout(**LAYOUT, barmode="group", height=320, yaxis_title="kcal/km")
        st.plotly_chart(fig_cb, use_container_width=True)

    with col_cal2:
        st.caption("Calories corrigées/km · facteur = poids réel ÷ 70 kg (profil Garmin)")
        fig_cc = go.Figure()
        for i, seance in enumerate(sorted(df_cal["Séance"].unique())):
            d = df_cal[df_cal["Séance"] == seance]
            fig_cc.add_trace(go.Bar(
                name=f"Séance {seance}",
                x=d["Coureur"], y=d["cal_km_corrige"],
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=0.55 + 0.25 * i,
                text=[f"{v:.0f}" for v in d["cal_km_corrige"]],
                textposition="outside",
                textfont=dict(color="white", size=10),
                hovertemplate="<b>%{x}</b><br>%{text} kcal/km (corrigé)<extra></extra>",
            ))
        fig_cc.update_layout(**LAYOUT, barmode="group", height=320, yaxis_title="kcal/km")
        st.plotly_chart(fig_cc, use_container_width=True)

    st.info(
        "**Facteurs de correction appliqués :** "
        "Adrien ×0.91 · Arthur ×1.00 · Khalil ×1.14 · Nathan ×1.09 · "
        "La puissance et le TE aérobie restent biaisés (profil fitness d'Arthur uniquement)."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 — MÉTÉO & CORRÉLATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Météo & Corrélations":
    st.title("Météo & Corrélations")

    has_meteo = "Météo_Temp" in df.columns and df["Météo_Temp"].notna().any()

    if not has_meteo:
        st.info("""
        **Données météo non disponibles en mode CSV.**

        Elles apparaîtront automatiquement une fois la base PostgreSQL alimentée
        via `ingest_meteo.py`.

        Les graphiques de cette page répondent directement à la problématique :
        *"Les conditions environnementales impactent-elles la performance ?"*
        """)
        st.stop()

    # ── Cards météo par séance ─────────────────────────────────────────────────
    st.subheader("Conditions météo par séance")
    df_mc = df.drop_duplicates("Séance").sort_values("Séance")

    mcols = st.columns(len(df_mc))
    for i, (_, row) in enumerate(df_mc.iterrows()):
        with mcols[i]:
            pluie = f"{row.get('Météo_Precipitation', 0) or 0:.1f} mm"
            st.markdown(f"""
            <div style="border:1px solid #333; border-radius:8px; padding:14px;
                        background:#1a1a1a; text-align:center;">
                <h4 style="color:#e0e0e0; margin:0 0 8px 0;">Séance {int(row['Séance'])}</h4>
                <p style="font-size:2em; margin:4px 0;">🌡️</p>
                <p style="margin:2px 0; color:#fff; font-size:1.3em;"><b>{row['Météo_Temp']:.1f}°C</b></p>
                <p style="margin:2px 0; color:#aaa;">Ressenti {row.get('Météo_TempRessentie', row['Météo_Temp']):.1f}°C</p>
                <p style="margin:4px 0; color:#aaa;">💧 {row.get('Météo_Humidite', 0):.0f}% humidité</p>
                <p style="margin:2px 0; color:#aaa;">💨 {row.get('Météo_Vent', 0):.1f} km/h</p>
                <p style="margin:2px 0; color:#aaa;">🌧 {pluie}</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    # ── Scatter température vs allure ──────────────────────────────────────────
    with col1:
        st.subheader("Température vs Allure")
        st.caption("Répond directement à la problématique · droite = tendance toutes données confondues")

        df9 = df.dropna(subset=["Météo_Temp", "Allure_s"])
        fig9 = go.Figure()
        for coureur in coureurs_sel:
            dc = df9[df9["Coureur"] == coureur]
            if dc.empty:
                continue
            fig9.add_trace(go.Scatter(
                x=dc["Météo_Temp"], y=dc["Allure_s"],
                name=coureur, mode="markers",
                marker=dict(size=16, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                customdata=list(zip(dc["Allure_str"], dc["Séance"])),
                hovertemplate=f"<b>{coureur}</b> · S%{{customdata[1]}}<br>"
                              f"Temp : %{{x}}°C<br>Allure : %{{customdata[0]}}<extra></extra>",
            ))
        add_trendline(fig9, df9["Météo_Temp"], df9["Allure_s"])
        fig9.update_layout(
            **LAYOUT, height=360,
            xaxis=dict(**_AXIS, title="Température (°C)"),
            yaxis=dict(**_AXIS, autorange="reversed", title="Allure (s/km)"),
        )
        st.plotly_chart(fig9, use_container_width=True)

    # ── Scatter humidité vs FC ─────────────────────────────────────────────────
    with col2:
        st.subheader("Humidité vs Fréquence Cardiaque")
        st.caption("Chaleur humide → FC plus élevée ?")

        df10 = df.dropna(subset=["Météo_Humidite", "FC_moy"])
        fig10 = go.Figure()
        for coureur in coureurs_sel:
            dc = df10[df10["Coureur"] == coureur]
            if dc.empty:
                continue
            fig10.add_trace(go.Scatter(
                x=dc["Météo_Humidite"], y=dc["FC_moy"],
                name=coureur, mode="markers",
                marker=dict(size=16, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                customdata=dc["Séance"],
                hovertemplate=f"<b>{coureur}</b> · S%{{customdata}}<br>"
                              f"Humidité : %{{x}}%<br>FC : %{{y}} bpm<extra></extra>",
            ))
        add_trendline(fig10, df10["Météo_Humidite"], df10["FC_moy"])
        fig10.update_layout(
            **LAYOUT, height=360,
            xaxis=dict(**_AXIS, title="Humidité (%)"),
            yaxis=dict(**_AXIS, title="FC moyenne (bpm)"),
        )
        st.plotly_chart(fig10, use_container_width=True)

    # ── Température & vent par séance ──────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Température par séance")
        st.caption("Réelle vs ressentie")

        df_tc = df.drop_duplicates("Séance").sort_values("Séance").dropna(subset=["Météo_Temp"])
        fig11 = go.Figure()
        fig11.add_trace(go.Bar(
            name="Temp. réelle",
            x=df_tc["Séance"].astype(str),
            y=df_tc["Météo_Temp"],
            marker_color="#5588FF",
            text=[f"{v:.1f}°C" for v in df_tc["Météo_Temp"]],
            textposition="outside", textfont=dict(color="white"),
        ))
        if "Météo_TempRessentie" in df_tc.columns:
            fig11.add_trace(go.Bar(
                name="Ressenti",
                x=df_tc["Séance"].astype(str),
                y=df_tc["Météo_TempRessentie"],
                marker_color="#FF8844",
                text=[f"{v:.1f}°C" for v in df_tc["Météo_TempRessentie"]],
                textposition="outside", textfont=dict(color="white"),
            ))
        fig11.update_layout(**LAYOUT, barmode="group", height=320, yaxis_title="°C")
        st.plotly_chart(fig11, use_container_width=True)

    with col4:
        st.subheader("Humidité & Vent")
        st.caption("Humidité (barres) · vent (ligne)")

        df_hw = df.drop_duplicates("Séance").sort_values("Séance").dropna(subset=["Météo_Humidite"])
        fig12 = go.Figure()
        fig12.add_trace(go.Bar(
            name="Humidité (%)",
            x=df_hw["Séance"].astype(str),
            y=df_hw["Météo_Humidite"],
            marker_color="#44CCAA",
            yaxis="y",
        ))
        if "Météo_Vent" in df_hw.columns:
            fig12.add_trace(go.Scatter(
                name="Vent (km/h)",
                x=df_hw["Séance"].astype(str),
                y=df_hw["Météo_Vent"],
                mode="markers+lines",
                marker=dict(size=10, color="white"),
                line=dict(color="#aaa", width=1.5),
                yaxis="y2",
            ))
        fig12.update_layout(
            **LAYOUT, height=320,
            yaxis=dict(title="Humidité (%)", gridcolor="#2a2a2a"),
            yaxis2=dict(title="Vent (km/h)", overlaying="y", side="right"),
        )
        st.plotly_chart(fig12, use_container_width=True)

    # ── Heatmap corrélations ───────────────────────────────────────────────────
    st.divider()
    st.subheader("Matrice de corrélations")
    st.caption("Pearson · rouge = corrélation positive · bleu = inverse · blanc = indépendant")

    corr_candidates = ["Allure_s", "FC_moy", "Cadence_moy", "Foulée_moy",
                       "Puissance_moy", "Météo_Temp", "Météo_Humidite", "Météo_Vent"]
    corr_cols = [c for c in corr_candidates if c in df.columns and df[c].notna().sum() >= 3]

    if len(corr_cols) >= 3 and len(df) >= 4:
        corr = df[corr_cols].corr()
        labels_map = {
            "Allure_s": "Allure", "FC_moy": "FC moy", "Cadence_moy": "Cadence",
            "Foulée_moy": "Foulée", "Puissance_moy": "Puissance",
            "Météo_Temp": "Température", "Météo_Humidite": "Humidité", "Météo_Vent": "Vent",
        }
        corr.index = [labels_map.get(c, c) for c in corr.index]
        corr.columns = [labels_map.get(c, c) for c in corr.columns]

        fig13 = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            text=[[f"{v:.2f}" for v in row] for row in corr.values],
            texttemplate="%{text}",
            textfont=dict(color="white", size=11),
            colorscale="RdBu", reversescale=True,
            zmin=-1, zmax=1, showscale=True,
            hovertemplate="%{y} × %{x}<br>r = %{text}<extra></extra>",
        ))
        fig13.update_layout(**LAYOUT, height=440)
        st.plotly_chart(fig13, use_container_width=True)
    else:
        st.info("Pas assez de données pour la matrice. Nécessite au moins 4 lignes avec données météo.")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 5 — TÊTE-À-TÊTE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Tête-à-tête":
    st.title("Tête-à-tête")
    st.caption("Comparez deux coureurs sur une séance donnée")

    if len(coureurs_sel) < 2:
        st.warning("Sélectionnez au moins 2 coureurs dans la sidebar.")
        st.stop()

    col_a, col_b, col_s = st.columns([2, 2, 1])
    with col_a:
        ca = st.selectbox("Coureur A", coureurs_sel, index=0)
    with col_b:
        cb = st.selectbox("Coureur B", [c for c in coureurs_sel if c != ca], index=0)
    with col_s:
        seance_tat = st.selectbox("Séance", sorted(df["Séance"].unique()))

    da = df[(df["Coureur"] == ca) & (df["Séance"] == seance_tat)]
    db_ = df[(df["Coureur"] == cb) & (df["Séance"] == seance_tat)]

    if da.empty or db_.empty:
        st.warning("Données manquantes pour un des coureurs sur cette séance.")
        st.stop()

    ra, rb = da.iloc[0], db_.iloc[0]
    st.divider()

    # ── Comparaison radar ──────────────────────────────────────────────────────
    RADAR2 = [
        ("Vitesse",   "Allure_s",      False),
        ("Endurance", "FC_moy",        False),
        ("Cadence",   "Cadence_moy",   True),
        ("Foulée",    "Foulée_moy",    True),
        ("Puissance", "Puissance_moy", True),
    ]
    radar2_ok = [(lbl, col, hib) for lbl, col, hib in RADAR2
                 if col in df.columns and df[col].notna().any()]
    cats2 = [r[0] for r in radar2_ok] + [radar2_ok[0][0]]

    fig_r2 = go.Figure()
    for runner, row in [(ca, ra), (cb, rb)]:
        vals = []
        for _, col_name, hib in radar2_ok:
            v = row.get(col_name)
            if pd.isna(v):
                vals.append(50.0)
                continue
            ref = df_all[col_name].dropna()
            mn, mx = ref.min(), ref.max()
            vals.append(50.0 if mx == mn else ((v - mn) / (mx - mn) * 100 if hib else (mx - v) / (mx - mn) * 100))
        vals.append(vals[0])
        color = COLORS.get(runner, "#888")
        fig_r2.add_trace(go.Scatterpolar(
            r=vals, theta=cats2, name=runner,
            line=dict(color=color, width=2),
            fill="toself", fillcolor=color, opacity=0.2,
        ))
    fig_r2.update_layout(
        **LAYOUT,
        polar=dict(
            bgcolor="#1a1a1a",
            radialaxis=dict(visible=True, range=[0, 100], tickcolor="#555",
                            gridcolor="#333", color="#888"),
            angularaxis=dict(tickcolor="#555", gridcolor="#333", color="#e0e0e0"),
        ),
        height=380,
    )
    st.plotly_chart(fig_r2, use_container_width=True)

    # ── Barres comparatives ────────────────────────────────────────────────────
    st.subheader("Comparaison métrique par métrique")

    METRIQUES = [
        ("Allure moy",   "Allure_s",      "s/km",    False, lambda v: pace_str(v)),
        ("Sprint",       "Meilleure_allure_s", "s/km", False, lambda v: pace_str(v)),
        ("FC moy",       "FC_moy",         "bpm",    False, lambda v: f"{int(v)} bpm"),
        ("FC max",       "FC_max",          "bpm",   False, lambda v: f"{int(v)} bpm"),
        ("Cadence",      "Cadence_moy",    "pas/min", True,  lambda v: f"{int(v)} pas/min"),
        ("Foulée",       "Foulée_moy",     "m",       True,  lambda v: f"{v:.2f} m"),
        ("Puissance",    "Puissance_moy",  "W",       True,  lambda v: f"{int(v)} W"),
        ("TE aérobie",   "TE",             "",        True,  lambda v: f"{v:.1f}"),
        ("Calories/km",  None,             "kcal/km", False, None),
    ]

    for label, col_name, unit, hib, fmt in METRIQUES:
        if col_name is None:
            # Calories normalisées
            if pd.notna(ra.get("Calories")) and ra.get("Distance", 0) > 0:
                va = ra["Calories"] / ra["Distance"]
                vb = rb["Calories"] / rb["Distance"]
                fmt_fn = lambda v: f"{v:.0f} kcal/km"
            else:
                continue
        else:
            va, vb = ra.get(col_name), rb.get(col_name)
            fmt_fn = fmt
            if pd.isna(va) or pd.isna(vb):
                continue

        winner = ca if (va < vb) != hib else cb
        color_a = COLORS.get(ca, "#888")
        color_b = COLORS.get(cb, "#888")

        c1, c2 = st.columns([1, 6])
        with c1:
            st.markdown(
                f"<p style='margin:0; color:#888; font-family:monospace; font-size:0.85em;'>{label}</p>"
                f"<p style='margin:0; color:{COLORS.get(winner,'#fff')}; font-size:0.75em;'>🏆 {winner}</p>",
                unsafe_allow_html=True
            )
        with c2:
            fig_tat = go.Figure()
            fig_tat.add_trace(go.Bar(
                x=[va], y=[ca], orientation="h",
                marker_color=color_a,
                text=[fmt_fn(va)], textposition="inside",
                textfont=dict(color="white", size=11),
                showlegend=False,
                hoverinfo="skip",
            ))
            fig_tat.add_trace(go.Bar(
                x=[vb], y=[cb], orientation="h",
                marker_color=color_b,
                text=[fmt_fn(vb)], textposition="inside",
                textfont=dict(color="white", size=11),
                showlegend=False,
                hoverinfo="skip",
            ))
            x_max = max(va, vb) * 1.25
            fig_tat.update_layout(
                **{k: v for k, v in LAYOUT.items() if k != "margin"},
                barmode="group", height=90,
                margin=dict(t=2, b=2, l=5, r=5),
                xaxis=dict(range=[0, x_max] if hib else [x_max, 0],
                           showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, tickfont=dict(color="white", size=11)),
            )
            st.plotly_chart(fig_tat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 6 — CONDITIONS & CONTEXTE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Conditions & Contexte":
    CONDITIONS_FILE = Path(__file__).parent.parent / "data" / "conditions.json"
    CONDITIONS_FILE.parent.mkdir(exist_ok=True)

    def load_conditions() -> list[dict]:
        if CONDITIONS_FILE.exists():
            return json.loads(CONDITIONS_FILE.read_text(encoding="utf-8"))
        return []

    def save_conditions(data: list[dict]):
        CONDITIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    st.title("Conditions & Contexte")
    st.caption(
        "Saisie manuelle des conditions physiologiques de chaque coureur avant chaque séance. "
        "Ces données permettent d'identifier les biais dans l'analyse des performances."
    )

    # ── Formulaire de saisie ───────────────────────────────────────────────────
    st.subheader("Saisir les conditions d'une séance")

    with st.form("form_conditions"):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            form_coureur = st.selectbox("Coureur", sorted(COLORS.keys()))
        with fc2:
            form_seance = st.selectbox("Séance", sorted(df_all["Séance"].unique()))
        with fc3:
            form_etat = st.slider("État général (1 = mauvais · 5 = excellent)", 1, 5, 3)

        fc4, fc5, fc6 = st.columns(3)
        with fc4:
            form_sommeil = st.number_input("Heures de sommeil", 0.0, 12.0, 7.0, step=0.5)
        with fc5:
            form_repas = st.number_input("Heures depuis dernier repas", 0.0, 24.0, 2.0, step=0.5)
        with fc6:
            form_jeun = st.checkbox("À jeun")

        form_courbatures = st.checkbox("Courbatures / douleurs")
        form_notes = st.text_area("Notes libres (stress, blessure, météo perçue...)", height=80)

        submitted = st.form_submit_button("Enregistrer")

    if submitted:
        conditions = load_conditions()
        # Mise à jour si existe déjà, sinon ajout
        existing = next((c for c in conditions
                         if c["coureur"] == form_coureur and c["seance"] == int(form_seance)), None)
        entry = {
            "coureur":        form_coureur,
            "seance":         int(form_seance),
            "a_jeun":         form_jeun,
            "heures_sommeil": form_sommeil,
            "etat_general":   form_etat,
            "courbatures":    form_courbatures,
            "dernier_repas_h": form_repas,
            "notes":          form_notes.strip(),
        }
        if existing:
            conditions = [e if not (e["coureur"] == form_coureur and e["seance"] == int(form_seance))
                          else entry for e in conditions]
            st.success(f"Conditions de {form_coureur} · Séance {form_seance} mises à jour.")
        else:
            conditions.append(entry)
            st.success(f"Conditions de {form_coureur} · Séance {form_seance} enregistrées.")
        save_conditions(conditions)

    # ── Tableau des conditions saisies ─────────────────────────────────────────
    st.divider()
    st.subheader("Conditions enregistrées")

    conditions = load_conditions()
    if not conditions:
        st.info("Aucune condition saisie pour l'instant. Utilisez le formulaire ci-dessus.")
    else:
        df_cond = pd.DataFrame(conditions).sort_values(["seance", "coureur"])

        # Mise en forme lisible
        df_display = df_cond.copy()
        df_display["a_jeun"] = df_display["a_jeun"].map({True: "✅ Oui", False: "❌ Non"})
        df_display["courbatures"] = df_display["courbatures"].map({True: "⚠️ Oui", False: "Non"})
        df_display["etat_general"] = df_display["etat_general"].apply(lambda v: "⭐" * int(v))
        df_display = df_display.rename(columns={
            "coureur": "Coureur", "seance": "Séance",
            "a_jeun": "À jeun", "heures_sommeil": "Sommeil (h)",
            "etat_general": "État", "courbatures": "Courbatures",
            "dernier_repas_h": "Dernier repas (h)", "notes": "Notes",
        })
        st.dataframe(df_display.set_index("Coureur"), use_container_width=True)

        # ── Suppression ───────────────────────────────────────────────────────
        st.caption("Supprimer une entrée :")
        del_col1, del_col2, del_col3 = st.columns([2, 2, 1])
        with del_col1:
            del_coureur = st.selectbox("Coureur", [c["coureur"] for c in conditions],
                                       key="del_coureur")
        with del_col2:
            del_seances = [c["seance"] for c in conditions if c["coureur"] == del_coureur]
            del_seance = st.selectbox("Séance", del_seances, key="del_seance")
        with del_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 Supprimer"):
                conditions = [c for c in conditions
                              if not (c["coureur"] == del_coureur and c["seance"] == del_seance)]
                save_conditions(conditions)
                st.success(f"Entrée supprimée : {del_coureur} · Séance {del_seance}")
                st.rerun()

    # ── Visualisation état général ─────────────────────────────────────────────
    if conditions and len(conditions) >= 2:
        st.divider()
        st.subheader("État général par coureur par séance")
        st.caption("Permet de contextualiser les performances — un coureur en mauvais état est-il moins performant ?")

        df_cv = pd.DataFrame(conditions)
        df_cv["etat_num"] = df_cv["etat_general"].astype(float)

        fig_cond = go.Figure()
        for coureur in sorted(df_cv["coureur"].unique()):
            dc = df_cv[df_cv["coureur"] == coureur].sort_values("seance")
            fig_cond.add_trace(go.Scatter(
                x=dc["seance"], y=dc["etat_num"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=12, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                hovertemplate="<b>%{fullData.name}</b> · S%{x}<br>État : %{y}/5<extra></extra>",
            ))
        fig_cond.add_hrect(y0=1, y1=2.5, fillcolor="#B71C1C", opacity=0.08, line_width=0)
        fig_cond.add_hrect(y0=3.5, y1=5, fillcolor="#1B5E20", opacity=0.08, line_width=0)
        fig_cond.update_layout(
            **LAYOUT, height=320,
            xaxis=dict(**_AXIS, title="Séance", dtick=1),
            yaxis=dict(**_AXIS, range=[0.5, 5.5], title="État général", dtick=1),
        )
        st.plotly_chart(fig_cond, use_container_width=True)

        # ── Scatter état vs allure ─────────────────────────────────────────────
        st.subheader("État général vs Allure")
        st.caption("Un mauvais état se traduit-il par une allure plus lente ?")

        df_merge = df_cv.merge(
            df_all[["Coureur", "Séance", "Allure_s", "Allure_str"]],
            left_on=["coureur", "seance"], right_on=["Coureur", "Séance"], how="inner"
        )
        if not df_merge.empty:
            fig_ea = go.Figure()
            for coureur in sorted(df_merge["coureur"].unique()):
                dc = df_merge[df_merge["coureur"] == coureur]
                fig_ea.add_trace(go.Scatter(
                    x=dc["etat_num"], y=dc["Allure_s"],
                    name=coureur, mode="markers",
                    marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                                line=dict(width=2, color="#0d0d0d")),
                    customdata=list(zip(dc["Allure_str"], dc["seance"])),
                    hovertemplate="<b>%{fullData.name}</b> · S%{customdata[1]}<br>"
                                  "État : %{x}/5<br>Allure : %{customdata[0]}<extra></extra>",
                ))
            add_trendline(fig_ea, df_merge["etat_num"], df_merge["Allure_s"])
            fig_ea.update_layout(
                **LAYOUT, height=320,
                xaxis=dict(**_AXIS, title="État général (1-5)", dtick=1),
                yaxis=dict(**_AXIS, autorange="reversed", title="Allure (s/km)"),
            )
            st.plotly_chart(fig_ea, use_container_width=True)

    # ── Note sur les biais ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Biais identifiés")
    st.markdown("""
| Biais | Impact | Correction appliquée |
|---|---|---|
| Profil Garmin unique (Arthur, 70 kg) | Calories, puissance, TE biaisés | ✅ Calories corrigées par poids réel |
| À jeun vs pas à jeun | FC plus élevée, énergie réduite | ✅ Variable collectée ici |
| Heures de sommeil | Récupération, performance | ✅ Variable collectée ici |
| GPS précision ~3-5m | Distance peut varier de 1-2% | ❌ Non corrigeable |
| Métriques moyennées 3 tours | Mélange effort modéré + maximal + récup | ❌ Splits non disponibles |
| Apprentissage du parcours | Amélioration S1→S2 non due à la condition physique | ⚠️ À mentionner en note critique |
| Niveaux physiques hétérogènes | Arthur (3:31) vs Khalil (6:13) difficilement comparables en absolu | ✅ % progression neutralise ça |
    """)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("SAÉ Data Pipeline · BUT Informatique 2A · IUT Reims-Châlons-Charleville · 2025-2026")