"""
app.py :SAÉ Running Dashboard (refonte Tour 2)
───────────────────────────────────────────────
Toutes les métriques sont calculées sur le Tour 2 (400m effort maximal).
17 sections.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import load_data, load_fit_segment, load_all_tours, COUREURS_CONNUS, POIDS

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAÉ Running :Tour 2",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "Adrien": "#E53935",
    "Nathan": "#2E7D32",
    "Arthur": "#FFCF39",
    "Khalil": "#1565C0",
}

_AXIS = dict(gridcolor="#2a2a2a", tickcolor="#555", linecolor="#555", zerolinecolor="#333")

LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0", family="monospace", size=12),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", 
        bordercolor="#333", 
        borderwidth=1,
        orientation="h",
        yanchor="top",
        y=-0.35,
        xanchor="center",
        x=0.5
    ),
    margin=dict(t=50, b=80, l=50, r=50),
    hoverlabel=dict(bgcolor="#1a1a1a", font_color="white", bordercolor="#555"),
)

st.markdown("""
<style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111111; }
    h1,h2,h3 { color: #f0f0f0; font-family: monospace; }
    div[data-testid="stMetric"] { background:#1a1a1a; border:1px solid #2a2a2a;
                                   border-radius:8px; padding:10px; }
</style>
""", unsafe_allow_html=True)


# ── i18n ──────────────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "Section": "Section",
    "Séance(s)": "Session(s)",
    "Coureur(s)": "Runner(s)",
    "Aucune donnée pour la sélection.": "No data for current selection.",
    "Source : **postgresql** · données **Tour 2** uniquement": "Source: **postgresql** · **Lap 2** data only",
    "Source : **csv** · données **Tour 2** uniquement": "Source: **csv** · **Lap 2** data only",
    "KPI :Meilleurs résultats Tour 2": "KPI :Best Lap 2 Results",
    "Temps au 400m & Conditions météo": "400m Time & Weather Conditions",
    "Puissance & Effort :Tour 2": "Power & Effort :Lap 2",
    "Face-à-tête :Comparaison 2 coureurs": "Head-to-Head :2 Runner Comparison",
    "Profil de vitesse instantanée :Tour 2": "Instant Speed Profile :Lap 2",
    "Analyse des accélérations :Tour 2": "Acceleration Analysis :Lap 2",
    "Récupération cardiaque post-Tour 2": "Post-Lap 2 Heart Rate Recovery",
    "Heatmap Météo × Performance": "Weather × Performance Heatmap",
    "Courbes de progression :Tour 2": "Progress Curves :Lap 2",
    "Carte GPS :Simulation Tour 2": "GPS Map :Lap 2 Simulation",
    "Comparaison Tour 1 / Tour 2 / Tour 3": "Lap 1 / Lap 2 / Lap 3 Comparison",
    "Splits 100m :Tour 2": "100m Splits :Lap 2",
    "Distribution des vitesses :Tour 2": "Speed Distribution :Lap 2",
    "Allure instantanée :Tour 2": "Instant Pace :Lap 2",
    "Puissance relative :W/kg": "Relative Power :W/kg",
    "FC vs Distance :Tour 2": "HR vs Distance :Lap 2",
    "Vent & Conditions météo détaillées": "Wind & Detailed Weather Conditions",
    "Données météo non disponibles.": "Weather data unavailable.",
    "Données FIT non disponibles.": "FIT data unavailable.",
    "Données GPS non disponibles.": "GPS data unavailable.",
    "Séance": "Session",
    "Métrique": "Metric",
    "Coureur": "Runner",
    "Coureur A": "Runner A",
    "Coureur B": "Runner B",
    "Records personnels sur l'ensemble des séances disponibles": "Personal records across all available sessions",
    "Classement :Temps au 400m": "Ranking :400m Time",
    "FC max atteinte": "Max HR reached",
    "Conditions par séance": "Conditions by session",
    "Temps 400m & Température": "400m Time & Temperature",
    "Temps 400m & Humidité / Vent": "400m Time & Humidity / Wind",
    "Scatter : Température vs Temps au 400m": "Scatter: Temperature vs 400m Time",
    "Puissance moyenne par séance": "Average power by session",
    "Puissance max par séance": "Max power by session",
    "FC moyenne Tour 2": "Lap 2 average HR",
    "Efficacité cardiovasculaire": "Cardiovascular efficiency",
    "Temps 400m séance par séance": "400m time session by session",
    "Métriques clés :tableau comparatif": "Key metrics :comparison table",
    "Radar :profil global (toutes séances)": "Radar :overall profile (all sessions)",
    "Vitesse max instantanée :comparaison": "Instant max speed :comparison",
    "Analyse des accélérations :Tour 2": "Acceleration analysis :Lap 2",
    "Récupération cardiaque post-Tour 2": "Post-Lap 2 heart-rate recovery",
    "Tableau de récupération": "Recovery table",
    "Heatmap Température × Coureur": "Temperature × Runner heatmap",
    "Scatter Température × Métrique": "Temperature × Metric scatter",
    "Humidité × Temps 400m": "Humidity × 400m Time",
    "Évolution absolue": "Absolute evolution",
    "Progression vs Séance 1 (%)": "Progress vs Session 1 (%)",
    "Tableau de synthèse :Temps 400m toutes séances": "Summary table :400m Time all sessions",
    "Direction du vent par séance": "Wind direction by session",
    "Tableau météo complet par séance": "Full weather table by session",
    "Corrélation vent × performance": "Wind × performance correlation",
    "Vitesse max GPS par coureur": "GPS max speed by runner",
    "Profil au fil du temps": "Profile over time",
    "Moyenne par tour :tous coureurs": "Average per lap :all runners",
    "Tableau récapitulatif :moyennes par tour": "Summary table :lap averages",
    "Temps par 100m (secondes)": "Time per 100m (seconds)",
    "Allure par 100m (min/km)": "Pace per 100m (min/km)",
    "Analyse : qui gère le mieux son effort ?": "Analysis: who manages effort best?",
    "Histogramme de vitesse (km/h)": "Speed histogram (km/h)",
    "Violin plot :dispersion des vitesses": "Violin plot :speed dispersion",
    "Zones de vitesse (% du temps par zone)": "Speed zones (% of time per zone)",
    "Comparaison toutes séances :allure min atteinte": "All sessions comparison :minimum pace reached",
    "W/kg par séance": "W/kg by session",
    "Comparaison Watts bruts vs W/kg": "Raw watts vs W/kg comparison",
    "FC vs Distance parcourue": "HR vs distance covered",
    "FC vs Vitesse (scatter)": "HR vs speed (scatter)",
    "Indice de confort :Température ressentie vs Temps 400m": "Comfort index :felt temperature vs 400m Time",
    "X Axis": "X Axis",
    "Time (s)": "Time (s)",
    "Distance (m)": "Distance (m)",
    "Mode": "Mode",
    "Interactive slider": "Interactive slider",
    "Plotly animation": "Plotly animation",
}

PAGE_KEYS = [
    "kpi", "meteo", "power", "face", "speed", "accel", "recovery", "heatmap",
    "progress", "gps", "laps", "splits", "dist", "pace", "wkg", "hrdist", "wind",
]
PAGE_LABELS = {
    "fr": [
        "1 · KPI & Classement",
        "2 · Temps 400m & Météo",
        "3 · Puissance & Effort",
        "4 · Face-à-tête",
        "5 · Profil de vitesse",
        "6 · Accélérations",
        "7 · Récupération cardiaque",
        "8 · Heatmap Météo",
        "9 · Progression",
        "10 · Carte GPS animée",
        "11 · Tour 1 / 2 / 3",
        "12 · Splits 100m",
        "13 · Distribution vitesses",
        "14 · Allure instantanée",
        "15 · Puissance W/kg",
        "16 · FC vs Distance",
        "17 · Vent & Direction",
    ],
    "en": [
        "1 · KPI & Ranking",
        "2 · 400m Time & Weather",
        "3 · Power & Effort",
        "4 · Head-to-Head",
        "5 · Speed Profile",
        "6 · Accelerations",
        "7 · Heart Rate Recovery",
        "8 · Weather Heatmap",
        "9 · Progress",
        "10 · Animated GPS Map",
        "11 · Lap 1 / 2 / 3",
        "12 · 100m Splits",
        "13 · Speed Distribution",
        "14 · Instant Pace",
        "15 · Power W/kg",
        "16 · HR vs Distance",
        "17 · Wind & Direction",
    ],
}


def T(text):
    if not isinstance(text, str):
        return text
    if st.session_state.get("lang", "fr") == "fr":
        return text
    out = text
    for fr, en in TRANSLATIONS.items():
        out = out.replace(fr, en)
    return out


# ── Helpers ────────────────────────────────────────────────────────────────────

def add_trendline(fig, x, y, color="#666"):
    mask = pd.notna(x) & pd.notna(y)
    xc, yc = np.array(x[mask], float), np.array(y[mask], float)
    if len(xc) < 3:
        return
    m, b = np.polyfit(xc, yc, 1)
    xl = np.linspace(xc.min(), xc.max(), 100)
    fig.add_trace(go.Scatter(x=xl, y=m*xl+b, mode="lines",
                             line=dict(color=color, dash="dot", width=1.5),
                             showlegend=False, hoverinfo="skip"))


def fmt_time(s):
    if s is None or pd.isna(s):
        return "N/A"
    return f"{int(s)//60}:{int(s)%60:02d}"


# ── Chargement ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_data():
    return load_data()

@st.cache_data(ttl=300)
def get_fit(coureur, seance, window):
    return load_fit_segment(coureur, seance, window)


df_all, source = get_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    default_lang = st.session_state.get("lang", "fr")
    lang = st.selectbox("Language", ["Français", "English"], index=1 if default_lang == "en" else 0)
    st.session_state["lang"] = "en" if lang == "English" else "fr"

    st.markdown("## 🏃 SAÉ Running")
    st.caption(T(f"Source : **{source}** · données **Tour 2** uniquement"))
    st.divider()

    page_options = PAGE_LABELS[st.session_state["lang"]]
    page = st.radio(T("Section"), page_options)
    page_key = PAGE_KEYS[page_options.index(page)]

    st.divider()
    seances_dispo = sorted(df_all["Séance"].unique())
    seances_sel = st.multiselect(T("Séance(s)"), seances_dispo, default=seances_dispo)
    coureurs_sel = st.multiselect(T("Coureur(s)"), sorted(df_all["Coureur"].unique()),
                                  default=sorted(df_all["Coureur"].unique()))

df = df_all[df_all["Séance"].isin(seances_sel) & df_all["Coureur"].isin(coureurs_sel)].copy()

if df.empty:
    st.warning(T("Aucune donnée pour la sélection."))
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  1 :KPI & CLASSEMENT
# ══════════════════════════════════════════════════════════════════════════════
if page_key == "kpi":
    st.title(T("KPI :Meilleurs résultats Tour 2"))
    st.caption(T("Records personnels sur l'ensemble des séances disponibles"))

    # Agrégation des records par coureur
    records = []
    for coureur in sorted(coureurs_sel):
        dc = df_all[df_all["Coureur"] == coureur]
        if dc.empty:
            continue
        best_t400 = dc["Temps400m_s"].min()
        best_allure = dc["Allure_s"].min()
        fc_max = dc["FC_max"].max() if dc["FC_max"].notna().any() else None
        cad_max = dc["Cadence_spm"].max() if dc["Cadence_spm"].notna().any() else None
        pwr_max = dc["Puissance_w"].max() if dc["Puissance_w"].notna().any() else None
        records.append({
            "coureur": coureur,
            "best_t400": best_t400,
            "best_allure": best_allure,
            "fc_max": fc_max,
            "cad_max": cad_max,
            "pwr_max": pwr_max,
        })

    cols = st.columns(len(records))
    for i, r in enumerate(records):
        color = COLORS.get(r["coureur"], "#888")
        with cols[i]:
            t400 = fmt_time(r["best_t400"])
            fc   = f"{int(r['fc_max'])} bpm" if r["fc_max"] and not pd.isna(r["fc_max"]) else "N/A"
            cad  = f"{int(r['cad_max'])} spm" if r["cad_max"] and not pd.isna(r["cad_max"]) else "N/A"
            pwr  = f"{int(r['pwr_max'])} W"   if r["pwr_max"] and not pd.isna(r["pwr_max"]) else "N/A"
            st.markdown(f"""
            <div style="border-left:4px solid {color}; padding:16px 18px; border-radius:8px;
                        background:#1a1a1a; margin-bottom:8px;">
                <h3 style="margin:0 0 10px 0; color:{color}; font-family:monospace;">{r['coureur']}</h3>
                <p style="margin:4px 0; font-size:1.4em; color:#fff;">⏱ <b>{t400}</b> <span style="font-size:0.7em;color:#999">/ 400m</span></p>
                <p style="margin:4px 0; color:#aaa;"> FC max : <b style="color:#fff">{fc}</b></p>
                <p style="margin:4px 0; color:#aaa;"> Cadence max : <b style="color:#fff">{cad}</b></p>
                <p style="margin:4px 0; color:#aaa;"> Puissance max : <b style="color:#fff">{pwr}</b></p>
            </div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Classement :Temps au 400m"))
        st.caption(T("Meilleur temps normalisé à 400m exact · Tour 2 uniquement"))
        df_r = pd.DataFrame(records).sort_values("best_t400")
        df_r["label"] = df_r["best_t400"].apply(fmt_time)
        fig = go.Figure(go.Bar(
            x=df_r["best_t400"], y=df_r["coureur"], orientation="h",
            marker_color=[COLORS.get(c, "#888") for c in df_r["coureur"]],
            text=df_r["label"], textposition="outside",
            textfont=dict(color="white"),
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        ))
        fig.update_layout(**LAYOUT, height=280,
                          xaxis=dict(**_AXIS, title="secondes"),
                          yaxis=dict(**_AXIS))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("FC max atteinte"))
        st.caption(T("Fréquence cardiaque maximale :Tour 2"))
        df_r2 = pd.DataFrame(records).dropna(subset=["fc_max"]).sort_values("fc_max", ascending=False)
        fig2 = go.Figure(go.Bar(
            x=df_r2["coureur"], y=df_r2["fc_max"],
            marker_color=[COLORS.get(c, "#888") for c in df_r2["coureur"]],
            text=[f"{int(v)} bpm" for v in df_r2["fc_max"]],
            textposition="outside", textfont=dict(color="white"),
        ))
        fig2.update_layout(**LAYOUT, height=280,
                           yaxis=dict(**_AXIS, title="bpm"))
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  2 :TEMPS 400M & MÉTÉO
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "meteo":
    st.title(T("Temps au 400m & Conditions météo"))

    has_meteo = "temperature_c" in df.columns and df["temperature_c"].notna().any()

    if not has_meteo:
        st.warning(T("Données météo non disponibles. Vérifiez `data/meteo.json`."))
        st.stop()

    # Météo par séance (1 ligne par séance)
    df_meteo = df.drop_duplicates("Séance").sort_values("Séance")

    st.subheader(T("Conditions par séance"))
    mcols = st.columns(len(df_meteo))
    for i, (_, row) in enumerate(df_meteo.iterrows()):
        with mcols[i]:
            st.markdown(f"""
            <div style="border:1px solid #333; border-radius:8px; padding:14px;
                        background:#1a1a1a; text-align:center;">
                <h4 style="color:#e0e0e0; margin:0 0 6px 0;">Séance {int(row['Séance'])}</h4>
                <p style="color:#aaa; margin:2px 0; font-size:0.85em;">{row.get('Date','')}</p>
                <p style="font-size:1.8em; margin:6px 0;">🌡️</p>
                <p style="color:#fff; margin:2px 0;"><b>{row['temperature_c']:.1f}°C</b>
                   <span style="color:#888; font-size:0.85em"> (ressenti {row.get('temperature_ressentie_c', row['temperature_c']):.1f}°C)</span></p>
                <p style="color:#aaa; margin:2px 0; font-size:0.9em;">💧 {int(row['humidite_pct'])}% · 💨 {row['vent_kmh']:.1f} km/h</p>
                <p style="color:#aaa; margin:2px 0; font-size:0.9em;">🌧️ {row['precipitation_mm']:.1f} mm</p>
            </div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Temps 400m & Température"))
        st.caption(T("Double axe : barres = temps au 400m · ligne = température"))

        seances = sorted(df["Séance"].unique())
        fig = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance")
            if dc.empty:
                continue
            fig.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Temps400m_s"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=10),
                text=dc["Temps400m_str"],
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
                yaxis="y1",
            ))
        # Température
        temps_meteo = [df_meteo[df_meteo["Séance"] == s]["temperature_c"].values[0]
                       if s in df_meteo["Séance"].values else None for s in seances]
        fig.add_trace(go.Scatter(
            x=seances, y=temps_meteo, name="Température",
            mode="lines+markers", yaxis="y2",
            line=dict(color="#FF8F00", dash="dot", width=2),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="S%{x}<br>%{y:.1f}°C<extra></extra>",
        ))
        fig.update_layout(
            **LAYOUT, height=380,
            xaxis=dict(**_AXIS, title="Séance", dtick=1),
            yaxis=dict(**_AXIS, title="Temps 400m (s)", autorange="reversed"),
            yaxis2=dict(**_AXIS, title="Température (°C)", overlaying="y",
                        side="right", showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Temps 400m & Humidité / Vent"))

        fig3 = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance")
            if dc.empty:
                continue
            fig3.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Temps400m_s"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=10),
                text=dc["Temps400m_str"],
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
                yaxis="y1",
            ))
        vent = [df_meteo[df_meteo["Séance"] == s]["vent_kmh"].values[0]
                if s in df_meteo["Séance"].values else None for s in seances]
        fig3.add_trace(go.Bar(
            x=seances, y=vent, name="Vent (km/h)",
            marker_color="rgba(100,149,237,0.4)", yaxis="y2",
            hovertemplate="S%{x}<br>%{y:.1f} km/h<extra></extra>",
        ))
        fig3.update_layout(
            **LAYOUT, height=380,
            xaxis=dict(**_AXIS, title="Séance", dtick=1),
            yaxis=dict(**_AXIS, title="Temps 400m (s)", autorange="reversed"),
            yaxis2=dict(**_AXIS, title="Vent (km/h)", overlaying="y",
                        side="right", showgrid=False),
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()
    st.subheader(T("Scatter : Température vs Temps au 400m"))
    st.caption(T("Chaque point = 1 coureur × 1 séance · droite = tendance globale"))

    df_s = df.dropna(subset=["temperature_c", "Temps400m_s"])
    fig4 = go.Figure()
    for coureur in coureurs_sel:
        dc = df_s[df_s["Coureur"] == coureur]
        if dc.empty:
            continue
        fig4.add_trace(go.Scatter(
            x=dc["temperature_c"], y=dc["Temps400m_s"],
            name=coureur, mode="markers",
            marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                        line=dict(width=2, color="#0d0d0d")),
            customdata=list(zip(dc["Temps400m_str"], dc["Séance"])),
            hovertemplate=f"<b>{coureur}</b> · S%{{customdata[1]}}<br>"
                          f"Temp : %{{x:.1f}}°C · %{{customdata[0]}}<extra></extra>",
        ))
    add_trendline(fig4, df_s["temperature_c"], df_s["Temps400m_s"])
    fig4.update_layout(
        **LAYOUT, height=360,
        xaxis=dict(**_AXIS, title="Température (°C)"),
        yaxis=dict(**_AXIS, autorange="reversed", title="Temps 400m (s)"),
    )
    st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  3 :PUISSANCE & EFFORT
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "power":
    st.title(T("Puissance & Effort :Tour 2"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Puissance moyenne par séance"))
        st.caption(T("Watts moyens sur le Tour 2 · profil Arthur 70 kg (non corrigé)"))

        fig = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance")
            if dc.empty or dc["Puissance_w"].isna().all():
                continue
            fig.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Puissance_w"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=10),
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{y:.0f}} W<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, height=350,
                          xaxis=dict(**_AXIS, title="Séance", dtick=1),
                          yaxis=dict(**_AXIS, title="Watts"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Puissance max par séance"))

        fig2 = go.Figure()
        for i, seance in enumerate(sorted(df["Séance"].unique())):
            d = df[df["Séance"] == seance].dropna(subset=["Puissance_w"])
            if d.empty:
                continue
            fig2.add_trace(go.Bar(
                name=f"S{seance}",
                x=d["Coureur"], y=d["Puissance_w"],
                marker_color=[COLORS.get(c, "#888") for c in d["Coureur"]],
                opacity=min(0.5 + 0.17 * i, 1.0),
                text=[f"{int(v)}W" for v in d["Puissance_w"]],
                textposition="outside", textfont=dict(color="white", size=10),
            ))
        fig2.update_layout(**LAYOUT, barmode="group", height=350,
                           yaxis=dict(**_AXIS, title="Watts"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader(T("FC moyenne Tour 2"))
        st.caption(T("Effort cardiovasculaire sur le lap rapide"))

        fig3 = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance")
            if dc.empty or dc["FC_moy"].isna().all():
                continue
            fig3.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["FC_moy"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=10),
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{y:.0f}} bpm<extra></extra>",
            ))
        fig3.update_layout(**LAYOUT, height=320,
                           xaxis=dict(**_AXIS, title="Séance", dtick=1),
                           yaxis=dict(**_AXIS, title="bpm"))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader(T("Efficacité cardiovasculaire"))
        st.caption(T("Temps 400m / FC moy · plus bas = plus efficace à effort cardiaque égal"))

        df_eff = df.dropna(subset=["Temps400m_s", "FC_moy"]).copy()
        df_eff["eff"] = df_eff["Temps400m_s"] / df_eff["FC_moy"]

        fig4 = go.Figure()
        for coureur in coureurs_sel:
            dc = df_eff[df_eff["Coureur"] == coureur].sort_values("Séance")
            if dc.empty:
                continue
            fig4.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["eff"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2),
                marker=dict(size=10),
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{y:.3f}}<extra></extra>",
            ))
        fig4.update_layout(**LAYOUT, height=320,
                           xaxis=dict(**_AXIS, title="Séance", dtick=1),
                           yaxis=dict(**_AXIS, title="s/bpm"))
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  4 :FACE-À-TÊTE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "face":
    st.title(T("Face-à-tête :Comparaison 2 coureurs"))

    if len(coureurs_sel) < 2:
        st.warning(T("Sélectionnez au moins 2 coureurs dans la sidebar."))
        st.stop()

    col_a, col_b = st.columns(2)
    with col_a:
        ca = st.selectbox(T("Coureur A"), coureurs_sel, index=0)
    with col_b:
        cb = st.selectbox(T("Coureur B"), [c for c in coureurs_sel if c != ca], index=0)

    dca = df[df["Coureur"] == ca].sort_values("Séance")
    dcb = df[df["Coureur"] == cb].sort_values("Séance")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Temps 400m séance par séance"))
        fig = go.Figure()
        for coureur, dc in [(ca, dca), (cb, dcb)]:
            fig.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Temps400m_s"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=3),
                marker=dict(size=12),
                text=dc["Temps400m_str"],
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, height=360,
                          xaxis=dict(**_AXIS, title="Séance", dtick=1),
                          yaxis=dict(**_AXIS, autorange="reversed", title="secondes"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Métriques clés :tableau comparatif"))

        metrics = ["Temps400m_str", "FC_moy", "FC_max", "Cadence_spm", "Puissance_w"]
        labels  = ["Temps 400m", "FC moy (bpm)", "FC max (bpm)", "Cadence (spm)", "Puissance (W)"]

        rows = []
        for s in sorted(df["Séance"].unique()):
            ra = dca[dca["Séance"] == s].iloc[0] if not dca[dca["Séance"] == s].empty else None
            rb = dcb[dcb["Séance"] == s].iloc[0] if not dcb[dcb["Séance"] == s].empty else None
            for lbl, col_name in zip(labels, metrics):
                va = ra[col_name] if ra is not None else None
                vb = rb[col_name] if rb is not None else None
                def fmt(v):
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        return "N/A"
                    if isinstance(v, float):
                        return f"{v:.0f}"
                    return str(v)
                rows.append({"Séance": f"S{s}", "Métrique": lbl, ca: fmt(va), cb: fmt(vb)})

        st.dataframe(pd.DataFrame(rows).set_index(["Séance", "Métrique"]),
                     use_container_width=True, height=420)

    st.divider()
    st.subheader(T("Radar :profil global (toutes séances)"))

    RADAR_COLS = [
        ("Vitesse",   "Temps400m_s",  False),
        ("FC effort", "FC_moy",       False),
        ("Puissance", "Puissance_w",  True),
        ("Cadence",   "Cadence_spm",  True),
        ("Régularité","Allure_s",     False),
    ]
    cats = [r[0] for r in RADAR_COLS] + [RADAR_COLS[0][0]]

    fig_r = go.Figure()
    for coureur, dc in [(ca, dca), (cb, dcb)]:
        vals = []
        for _, col_name, hib in RADAR_COLS:
            v = dc[col_name].mean()
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
        fig_r.add_trace(go.Scatterpolar(
            r=vals, theta=cats, name=coureur,
            line=dict(color=color, width=2),
            fill="toself", fillcolor=color, opacity=0.3,
        ))
    fig_r.update_layout(
        **LAYOUT, height=420,
        polar=dict(
            bgcolor="#1a1a1a",
            radialaxis=dict(visible=True, range=[0, 100],
                            tickcolor="#555", gridcolor="#333", color="#888"),
            angularaxis=dict(tickcolor="#555", gridcolor="#333", color="#e0e0e0"),
        ),
    )
    st.plotly_chart(fig_r, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  5 :PROFIL DE VITESSE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "speed":
    st.title(T("Profil de vitesse instantanée :Tour 2"))
    st.caption(T("Courbe m/s second-par-second sur le lap d'effort maximal"))

    col_s, col_x = st.columns([2, 3])
    with col_s:
        seance_v = st.selectbox(T("Séance"), sorted(df["Séance"].unique()))
    with col_x:
        axe = st.radio(T("X Axis"), [T("Time (s)"), T("Distance (m)")], horizontal=True)

    coureurs_v = [c for c in coureurs_sel if
                  (df[(df["Coureur"] == c) & (df["Séance"] == seance_v)].shape[0] > 0)]

    fig = go.Figure()
    for coureur in coureurs_v:
        seg = get_fit(coureur, seance_v, "tour2")
        if seg is None or seg.empty or "enhanced_speed" not in seg.columns:
            continue
        seg_c = seg.dropna(subset=["enhanced_speed"])
        x = seg_c["t_rel"] if axe == T("Time (s)") else seg_c["dist_rel"]
        # Lissage léger (rolling 3s)
        y = seg_c["enhanced_speed"].rolling(3, center=True, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=x, y=y, name=coureur,
            mode="lines",
            line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
            hovertemplate=f"<b>{coureur}</b><br>%{{x:.0f}} · %{{y:.2f}} m/s<extra></extra>",
        ))

    if fig.data:
        xlabel = T("Time (s)") if axe == T("Time (s)") else T("Distance (m)")
        fig.update_layout(**LAYOUT, height=420,
                          xaxis=dict(**_AXIS, title=xlabel),
                          yaxis=dict(**_AXIS, title="Vitesse (m/s)"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(T("Données FIT non disponibles pour cette sélection."))

    st.divider()
    st.subheader(T("Vitesse max instantanée :comparaison"))
    vmax_rows = []
    for coureur in coureurs_sel:
        for s in seances_sel:
            seg = get_fit(coureur, s, "tour2")
            if seg is None or "enhanced_speed" not in seg.columns:
                continue
            vmax = seg["enhanced_speed"].max()
            if pd.notna(vmax):
                vmax_rows.append({"Coureur": coureur, "Séance": s,
                                  "Vmax (m/s)": round(vmax, 2),
                                  "Vmax (km/h)": round(vmax * 3.6, 1)})
    if vmax_rows:
        st.dataframe(pd.DataFrame(vmax_rows).sort_values(["Séance", "Vmax (m/s)"],
                     ascending=[True, False]), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  6 :ACCÉLÉRATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "accel":
    st.title(T("Analyse des accélérations :Tour 2"))
    st.caption(T("Dérivée de la vitesse (m/s²) · positif = accélération · négatif = ralentissement"))

    seance_a = st.selectbox(T("Séance"), sorted(df["Séance"].unique()))

    fig = go.Figure()
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_a, "tour2")
        if seg is None or "enhanced_speed" not in seg.columns:
            continue
        seg_c = seg.dropna(subset=["enhanced_speed"]).copy()
        if len(seg_c) < 4:
            continue
        v = seg_c["enhanced_speed"].rolling(3, center=True, min_periods=1).mean()
        accel = v.diff() / seg_c["t_rel"].diff().replace(0, np.nan)
        accel = accel.rolling(3, center=True, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=seg_c["t_rel"], y=accel,
            name=coureur, mode="lines",
            line=dict(color=COLORS.get(coureur, "#888"), width=2),
            hovertemplate=f"<b>{coureur}</b><br>t=%{{x:.0f}}s · a=%{{y:.3f}} m/s²<extra></extra>",
        ))

    if fig.data:
        fig.add_hline(y=0, line=dict(color="#444", width=1))
        fig.update_layout(**LAYOUT, height=400,
                          xaxis=dict(**_AXIS, title="Temps (s)"),
                          yaxis=dict(**_AXIS, title="Accélération (m/s²)"))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(T("Accél. max au départ"))
            st.caption(T("Pic d'accélération dans les 10 premières secondes"))
        with col2:
            st.subheader(T("Accél. moy sur le lap"))
        with col3:
            st.subheader(T("Décél. en fin de course"))
            st.caption(T("Accélération moy sur les 10 dernières secondes"))

        for coureur in coureurs_sel:
            seg = get_fit(coureur, seance_a, "tour2")
            if seg is None or "enhanced_speed" not in seg.columns:
                continue
            seg_c = seg.dropna(subset=["enhanced_speed"]).copy()
            if len(seg_c) < 4:
                continue
            v = seg_c["enhanced_speed"].rolling(3, center=True, min_periods=1).mean()
            t = seg_c["t_rel"]
            accel = (v.diff() / t.diff().replace(0, np.nan)).rolling(3, center=True, min_periods=1).mean()
            accel.index = seg_c.index
            t.index = seg_c.index

            a_start = accel[t <= t.min() + 10].max()
            a_mean  = accel.mean()
            a_end   = accel[t >= t.max() - 10].mean()

            color = COLORS.get(coureur, "#888")
            with col1:
                st.metric(coureur, f"{a_start:.3f} m/s²" if pd.notna(a_start) else "N/A",
                          delta=None, label_visibility="visible")
            with col2:
                st.metric(coureur, f"{a_mean:.3f} m/s²" if pd.notna(a_mean) else "N/A")
            with col3:
                st.metric(coureur, f"{a_end:.3f} m/s²" if pd.notna(a_end) else "N/A")
    else:
        st.info(T("Données FIT non disponibles."))


# ══════════════════════════════════════════════════════════════════════════════
#  7 :RÉCUPÉRATION CARDIAQUE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "recovery":
    st.title(T("Récupération cardiaque post-Tour 2"))
    st.caption(T("Descente de la FC après la fin du lap d'effort maximal"))

    seance_r = st.selectbox(T("Séance"), sorted(df["Séance"].unique()))
    seuil_bpm = st.slider("Seuil de récupération (bpm)", 100, 150, 120)

    fig = go.Figure()
    recov_data = []
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_r, "post_tour2")
        if seg is None or "heart_rate" not in seg.columns:
            continue
        seg_c = seg.dropna(subset=["heart_rate"])
        if seg_c.empty:
            continue

        fc_start = seg_c["heart_rate"].iloc[0]
        # Temps pour passer sous le seuil
        below = seg_c[seg_c["heart_rate"] <= seuil_bpm]
        t_seuil = below["t_rel"].iloc[0] if not below.empty else None

        fig.add_trace(go.Scatter(
            x=seg_c["t_rel"], y=seg_c["heart_rate"],
            name=coureur, mode="lines",
            line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
            hovertemplate=f"<b>{coureur}</b><br>t=%{{x:.0f}}s · %{{y:.0f}} bpm<extra></extra>",
        ))
        recov_data.append({
            "Coureur": coureur,
            "FC départ (bpm)": int(fc_start),
            f"Temps < {seuil_bpm} bpm (s)": f"{int(t_seuil)}s" if t_seuil else "> 4 min",
            "FC à 60s (bpm)": int(seg_c[seg_c["t_rel"] <= 60]["heart_rate"].iloc[-1])
                              if not seg_c[seg_c["t_rel"] <= 60].empty else "N/A",
        })

    fig.add_hline(y=seuil_bpm, line=dict(color="#FF8F00", dash="dot", width=1.5),
                  annotation_text=f"seuil {seuil_bpm} bpm",
                  annotation_font_color="#FF8F00")
    if fig.data:
        fig.update_layout(**LAYOUT, height=400,
                          xaxis=dict(**_AXIS, title="Secondes après fin Tour 2"),
                          yaxis=dict(**_AXIS, title="FC (bpm)"))
        st.plotly_chart(fig, use_container_width=True)

        if recov_data:
            st.subheader(T("Tableau de récupération"))
            st.dataframe(pd.DataFrame(recov_data).set_index("Coureur"),
                         use_container_width=True)
    else:
        st.info(T("Données FIT post-Tour 2 non disponibles."))


# ══════════════════════════════════════════════════════════════════════════════
#  8 :HEATMAP MÉTÉO
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "heatmap":
    st.title(T("Heatmap Météo × Performance"))

    has_meteo = "temperature_c" in df.columns and df["temperature_c"].notna().any()
    if not has_meteo:
        st.warning(T("Données météo non disponibles."))
        st.stop()

    metrique = st.selectbox(T("Métrique"), ["Temps400m_s", "FC_moy", "Puissance_w"],
                             format_func=lambda x: {
                                 "Temps400m_s": "Temps 400m (s)",
                                 "FC_moy": "FC moyenne (bpm)",
                                 "Puissance_w": "Puissance (W)"
                             }[x])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Heatmap Température × Coureur"))
        pivot = df.pivot_table(index="Coureur", columns="Séance",
                               values=metrique, aggfunc="mean")
        temp_labels = {s: f"S{s}\n{df[df['Séance']==s]['temperature_c'].mean():.1f}°C"
                       for s in pivot.columns}
        fig = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[temp_labels.get(c, f"S{c}") for c in pivot.columns],
            y=pivot.index.tolist(),
            text=np.round(pivot.values, 1),
            texttemplate="%{text}",
            textfont=dict(color="white", size=13),
            colorscale=[[0, "#1B5E20"], [0.5, "#F9A825"], [1, "#B71C1C"]],
            reversescale=(metrique == "Temps400m_s"),
            showscale=True,
            hovertemplate="<b>%{y}</b> · %{x}<br>%{z:.1f}<extra></extra>",
        ))
        fig.update_layout(**LAYOUT, height=360)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Scatter Température × Métrique"))
        df_sc = df.dropna(subset=["temperature_c", metrique])
        fig2 = go.Figure()
        for coureur in coureurs_sel:
            dc = df_sc[df_sc["Coureur"] == coureur]
            if dc.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=dc["temperature_c"], y=dc[metrique],
                name=coureur, mode="markers",
                marker=dict(size=16, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                hovertemplate=f"<b>{coureur}</b><br>%{{x:.1f}}°C → %{{y:.1f}}<extra></extra>",
            ))
        add_trendline(fig2, df_sc["temperature_c"], df_sc[metrique])
        inv = (metrique == "Temps400m_s")
        fig2.update_layout(**LAYOUT, height=360,
                           xaxis=dict(**_AXIS, title="Température (°C)"),
                           yaxis=dict(**_AXIS, autorange="reversed" if inv else True,
                                      title=metrique))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Humidité × Temps 400m"))
    df_h = df.dropna(subset=["humidite_pct", "Temps400m_s"])
    fig3 = go.Figure()
    for coureur in coureurs_sel:
        dc = df_h[df_h["Coureur"] == coureur]
        if dc.empty:
            continue
        fig3.add_trace(go.Scatter(
            x=dc["humidite_pct"], y=dc["Temps400m_s"],
            name=coureur, mode="markers",
            marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                        line=dict(width=2, color="#0d0d0d")),
            hovertemplate=f"<b>{coureur}</b><br>%{{x}}% · {{}}<extra></extra>",
        ))
    add_trendline(fig3, df_h["humidite_pct"], df_h["Temps400m_s"])
    fig3.update_layout(**LAYOUT, height=340,
                       xaxis=dict(**_AXIS, title="Humidité (%)"),
                       yaxis=dict(**_AXIS, autorange="reversed", title="Temps 400m (s)"))
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  9 :PROGRESSION
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "progress":
    st.title(T("Courbes de progression :Tour 2"))
    st.caption(T("Évolution séance par séance · Khalil absent S3 (maladie)"))

    metrique_p = st.radio(T("Métrique"), ["Temps400m_s", "FC_max", "Puissance_w"],
                           format_func=lambda x: {
                               "Temps400m_s": "Temps au 400m",
                               "FC_max": "FC max",
                               "Puissance_w": "Puissance"
                           }[x], horizontal=True)
    inv_y = (metrique_p == "Temps400m_s")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Évolution absolue"))
        fig = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance").dropna(subset=[metrique_p])
            if dc.empty:
                continue
            fig.add_trace(go.Scatter(
                x=dc["Séance"], y=dc[metrique_p],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=11, line=dict(width=2, color="#0d0d0d")),
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{y:.1f}}<extra></extra>",
            ))
        fig.update_layout(
            **LAYOUT, height=380,
            xaxis=dict(**_AXIS, title="Séance", dtick=1),
            yaxis=dict(**_AXIS, autorange="reversed" if inv_y else True),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Progression vs Séance 1 (%)"))
        st.caption(T("Positif = amélioration · négatif = régression"))

        fig2 = go.Figure()
        for coureur in coureurs_sel:
            dc = df[df["Coureur"] == coureur].sort_values("Séance").dropna(subset=[metrique_p])
            if dc.empty or dc[dc["Séance"] == 1].empty:
                continue
            base = dc[dc["Séance"] == 1][metrique_p].values[0]
            rest = dc[dc["Séance"] > 1].copy()
            if inv_y:
                rest["pct"] = (base - rest[metrique_p]) / base * 100
            else:
                rest["pct"] = (rest[metrique_p] - base) / base * 100
            fig2.add_trace(go.Scatter(
                x=rest["Séance"], y=rest["pct"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=11),
                text=[f"{v:+.1f}%" for v in rest["pct"]],
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
            ))
        fig2.add_hline(y=0, line=dict(color="#444", width=1))
        fig2.update_layout(**LAYOUT, height=380,
                           xaxis=dict(**_AXIS, title="Séance", dtick=1),
                           yaxis=dict(**_AXIS, title="%"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Tableau de synthèse :Temps 400m toutes séances"))
    rows = []
    for coureur in sorted(coureurs_sel):
        row = {"Coureur": coureur}
        dc = df[df["Coureur"] == coureur].sort_values("Séance")
        for s in sorted(df_all["Séance"].unique()):
            r = dc[dc["Séance"] == s]
            row[f"S{s}"] = r["Temps400m_str"].values[0] if not r.empty else "-"
        dc_c = df[df["Coureur"] == coureur].dropna(subset=["Temps400m_s"])
        row["Meilleur"] = dc_c.loc[dc_c["Temps400m_s"].idxmin(), "Temps400m_str"] if not dc_c.empty else "-"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows).set_index("Coureur"), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  10 :CARTE GPS ANIMÉE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "gps":
    st.title(T("Carte GPS :Simulation Tour 2"))
    st.caption(T("Positionnement second-par-second sur le parcours réel · Parc de Champagne, Reims"))

    seance_map = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="map_seance")

    segs = {}
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_map, "tour2")
        if seg is not None:
            seg = seg.dropna(subset=["position_lat", "position_long"]).copy()
            if not seg.empty:
                segs[coureur] = seg

    if not segs:
        st.info(T("Données GPS non disponibles."))
    else:
        max_t = int(max(s["t_rel"].max() for s in segs.values()))
        center_lat = np.mean([s["position_lat"].mean() for s in segs.values()])
        center_lon = np.mean([s["position_long"].mean() for s in segs.values()])

        col_mode, _ = st.columns([2, 3])
        with col_mode:
            mode = st.radio(T("Mode"), [T("Interactive slider"), T("Plotly animation")], horizontal=True)

        if mode == T("Interactive slider"):
            t_sel = st.slider("⏱ Secondes depuis départ Tour 2", 0, max_t, 0)

            fig = go.Figure()
            for coureur, seg in segs.items():
                color = COLORS.get(coureur, "#888")
                # Tracé complet (transparent)
                fig.add_trace(go.Scattermapbox(
                    lat=seg["position_lat"].tolist(),
                    lon=seg["position_long"].tolist(),
                    mode="lines",
                    line=dict(color=color, width=3),
                    opacity=0.35,
                    name=coureur,
                    showlegend=True,
                ))
                # Position actuelle
                row = seg.iloc[(seg["t_rel"] - t_sel).abs().argsort().iloc[0]]
                finished = t_sel > seg["t_rel"].max()
                v_kmh = (row.get("enhanced_speed", 0) or 0) * 3.6
                fig.add_trace(go.Scattermapbox(
                    lat=[row["position_lat"]],
                    lon=[row["position_long"]],
                    mode="markers+text",
                    marker=dict(size=18 if not finished else 10,
                                color=color,
                                opacity=1.0 if not finished else 0.3),
                    text=[f"{coureur}{'✓' if finished else ''}"],
                    textposition="top right",
                    name=f"{coureur} pos",
                    showlegend=False,
                    hovertext=f"{coureur} · {v_kmh:.1f} km/h{' · ARRIVÉ' if finished else ''}",
                    hoverinfo="text",
                ))

            fig.update_layout(
                mapbox=dict(style="open-street-map",
                            center=dict(lat=center_lat, lon=center_lon), zoom=16),
                **LAYOUT, height=550,
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            # Build padded DataFrame for px animation
            rows_anim = []
            for coureur, seg in segs.items():
                t_max_c = seg["t_rel"].max()
                for t in range(0, max_t + 1):
                    row = seg.iloc[(seg["t_rel"] - t).abs().argsort().iloc[0]]
                    finished = t > t_max_c
                    rows_anim.append({
                        "Coureur": coureur,
                        "t": t,
                        "lat": row["position_lat"],
                        "lon": row["position_long"],
                        "Vitesse (km/h)": round((row.get("enhanced_speed", 0) or 0) * 3.6, 1),
                        "Statut": "Terminé" if finished else "En course",
                    })

            anim_df = pd.DataFrame(rows_anim)
            fig_anim = px.scatter_mapbox(
                anim_df, lat="lat", lon="lon",
                color="Coureur",
                color_discrete_map=COLORS,
                animation_frame="t",
                hover_name="Coureur",
                hover_data={"Vitesse (km/h)": True, "Statut": True, "t": False, "lat": False, "lon": False},
                size_max=18,
                zoom=16,
                mapbox_style="open-street-map",
                center={"lat": center_lat, "lon": center_lon},
            )
            # Add static path traces
            for coureur, seg in segs.items():
                fig_anim.add_trace(go.Scattermapbox(
                    lat=seg["position_lat"].tolist(),
                    lon=seg["position_long"].tolist(),
                    mode="lines",
                    line=dict(color=COLORS.get(coureur, "#888"), width=2),
                    opacity=0.3,
                    name=f"{coureur} (tracé)",
                    showlegend=False,
                ))
            fig_anim.update_layout(**LAYOUT, height=580)
            st.plotly_chart(fig_anim, use_container_width=True)

        # Stats GPS
        st.divider()
        st.subheader(T("Vitesse max GPS par coureur"))
        gps_stats = []
        for coureur, seg in segs.items():
            gps_stats.append({
                "Coureur": coureur,
                "Vmax (km/h)": round(seg["enhanced_speed"].max() * 3.6, 1),
                "Vmoy (km/h)": round(seg["enhanced_speed"].mean() * 3.6, 1),
                "Durée Tour 2 (s)": int(seg["t_rel"].max()),
            })
        st.dataframe(pd.DataFrame(gps_stats).set_index("Coureur"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  11 :TOUR 1 / 2 / 3
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "laps":
    st.title(T("Comparaison Tour 1 / Tour 2 / Tour 3"))
    st.caption(T("Échauffement vs Effort maximal vs Récupération :structure réelle de la séance 3×400m"))

    seance_t = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="t123_seance")
    metrique_t = st.radio(T("Metric"), [T("Speed (m/s)"), T("HR (bpm)"), T("Cadence (spm)")],
                          horizontal=True, key="t123_met")

    col_map = {"Speed (m/s)": "enhanced_speed", "HR (bpm)": "heart_rate", "Cadence (spm)": "cadence"}
    col_t = col_map[metrique_t]

    TOUR_COLORS = {"Tour 1": "#607D8B", "Tour 2": "#FF5722", "Tour 3": "#4CAF50"}
    TOUR_DASH   = {"Tour 1": "dot", "Tour 2": "solid", "Tour 3": "dash"}

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Profil au fil du temps"))
        st.caption(T("Superposition des 3 tours pour chaque coureur"))
        coureur_t = st.selectbox(T("Coureur"), coureurs_sel, key="t123_coureur")

        tours = load_all_tours(coureur_t, seance_t)
        if tours is None:
            st.info(f"Données insuffisantes pour détecter les 3 tours de {coureur_t} S{seance_t}.")
        else:
            fig = go.Figure()
            for tname, tdf in tours.items():
                label = tname.replace("tour", "Tour ")
                if col_t not in tdf.columns or tdf[col_t].isna().all():
                    continue
                y = tdf[col_t].rolling(3, center=True, min_periods=1).mean()
                if col_t == "cadence":
                    y = y * 2  # single-foot → total spm
                fig.add_trace(go.Scatter(
                    x=tdf["t_lap"], y=y,
                    name=label, mode="lines",
                    line=dict(color=TOUR_COLORS.get(label, "#888"),
                              dash=TOUR_DASH.get(label, "solid"), width=2.5),
                    hovertemplate=f"<b>{label}</b><br>t=%{{x:.0f}}s · %{{y:.2f}}<extra></extra>",
                ))
            fig.update_layout(**LAYOUT, height=380,
                              xaxis=dict(**_AXIS, title="Temps dans le tour (s)"),
                              yaxis=dict(**_AXIS, title=metrique_t))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Moyenne par tour :tous coureurs"))
        st.caption(T("Comparaison de l'effort moyen sur chaque tour"))

        summary_rows = []
        for coureur in coureurs_sel:
            tours = load_all_tours(coureur, seance_t)
            if tours is None:
                continue
            for tname, tdf in tours.items():
                label = tname.replace("tour", "Tour ")
                if col_t not in tdf.columns or tdf[col_t].isna().all():
                    continue
                val = tdf[col_t].mean()
                if col_t == "cadence":
                    val *= 2
                summary_rows.append({"Coureur": coureur, "Tour": label, "val": val})

        if summary_rows:
            df_sum = pd.DataFrame(summary_rows)
            fig2 = go.Figure()
            for tour_label in ["Tour 1", "Tour 2", "Tour 3"]:
                d = df_sum[df_sum["Tour"] == tour_label]
                if d.empty:
                    continue
                fig2.add_trace(go.Bar(
                    name=tour_label,
                    x=d["Coureur"], y=d["val"],
                    marker_color=TOUR_COLORS.get(tour_label, "#888"),
                    text=[f"{v:.1f}" for v in d["val"]],
                    textposition="outside", textfont=dict(color="white", size=10),
                ))
            fig2.update_layout(**LAYOUT, barmode="group", height=380,
                               yaxis=dict(**_AXIS, title=metrique_t))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Tableau récapitulatif :moyennes par tour"))
    recap = []
    for coureur in sorted(coureurs_sel):
        tours = load_all_tours(coureur, seance_t)
        if tours is None:
            continue
        row = {"Coureur": coureur}
        for tname, tdf in tours.items():
            label = tname.replace("tour", "Tour ")
            v_moy = tdf["enhanced_speed"].mean() * 3.6 if "enhanced_speed" in tdf.columns else None
            fc_moy = tdf["heart_rate"].mean() if "heart_rate" in tdf.columns else None
            dur = int(tdf["t_lap"].max()) if not tdf.empty else None
            row[f"{label} :Allure"] = f"{v_moy:.1f} km/h" if v_moy else "N/A"
            row[f"{label} :FC moy"] = f"{fc_moy:.0f} bpm" if fc_moy and not pd.isna(fc_moy) else "N/A"
            row[f"{label} :Durée"] = f"{dur}s" if dur else "N/A"
        recap.append(row)
    if recap:
        st.dataframe(pd.DataFrame(recap).set_index("Coureur"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  12 :SPLITS 100M
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "splits":
    st.title(T("Splits 100m :Tour 2"))
    st.caption(T("Temps pour chaque tranche de 100m · révèle la stratégie de course"))

    seance_sp = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="split_seance")

    def get_splits(coureur, seance):
        seg = get_fit(coureur, seance, "tour2")
        if seg is None or "dist_rel" not in seg.columns:
            return None
        seg = seg.dropna(subset=["dist_rel"]).copy()
        if seg.empty or seg["dist_rel"].max() < 10:
            return None
        splits = []
        prev_t = 0.0
        for mark in [100, 200, 300, 400]:
            above = seg[seg["dist_rel"] >= mark]
            if above.empty:
                break
            t_cross = above["t_rel"].iloc[0]
            splits.append({"100m": f"{mark-100}–{mark}m", "Temps (s)": round(t_cross - prev_t, 1)})
            prev_t = t_cross
        return splits

    # Tableau des splits
    all_splits = {}
    for coureur in coureurs_sel:
        sp = get_splits(coureur, seance_sp)
        if sp:
            all_splits[coureur] = sp

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Temps par 100m (secondes)"))
        fig = go.Figure()
        for coureur, splits in all_splits.items():
            x = [s["100m"] for s in splits]
            y = [s["Temps (s)"] for s in splits]
            fig.add_trace(go.Scatter(
                x=x, y=y, name=coureur,
                mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=12),
                text=[f"{v}s" for v in y],
                hovertemplate=f"<b>{coureur}</b> · %{{x}}<br>%{{y}}s<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, height=380,
                          xaxis=dict(**_AXIS, title="Segment"),
                          yaxis=dict(**_AXIS, title="Temps (s)"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Allure par 100m (min/km)"))
        fig2 = go.Figure()
        for coureur, splits in all_splits.items():
            x = [s["100m"] for s in splits]
            # 100m en t secondes → allure en s/km = t * 10
            y = [s["Temps (s)"] * 10 for s in splits]
            labels = [f"{int(v)//60}:{int(v)%60:02d}/km" for v in y]
            fig2.add_trace(go.Scatter(
                x=x, y=y, name=coureur,
                mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=12),
                text=labels,
                hovertemplate=f"<b>{coureur}</b> · %{{x}}<br>%{{text}}<extra></extra>",
            ))
        fig2.update_layout(**LAYOUT, height=380,
                           xaxis=dict(**_AXIS, title="Segment"),
                           yaxis=dict(**_AXIS, autorange="reversed", title="s/km"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Analyse : qui gère le mieux son effort ?"))
    st.caption(T("Ratio dernier 100m / premier 100m · < 1 = accélération finale · > 1 = ralentissement"))
    ratio_rows = []
    for coureur, splits in all_splits.items():
        if len(splits) >= 2:
            ratio = splits[-1]["Temps (s)"] / splits[0]["Temps (s)"]
            ratio_rows.append({
                "Coureur": coureur,
                "0–100m (s)": splits[0]["Temps (s)"],
                "300–400m (s)": splits[-1]["Temps (s)"],
                "Ratio fin/début": round(ratio, 3),
                "Interprétation": "Accélère " if ratio < 0.95 else ("Stable " if ratio < 1.05 else "Ralentit "),
            })
    if ratio_rows:
        st.dataframe(pd.DataFrame(ratio_rows).set_index("Coureur"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  13 :DISTRIBUTION DES VITESSES
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "dist":
    st.title(T("Distribution des vitesses :Tour 2"))
    st.caption(T("Quelle % du lap chaque coureur passe à quelle vitesse ?"))

    seance_dv = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="dv_seance")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Histogramme de vitesse (km/h)"))
        fig = go.Figure()
        for coureur in coureurs_sel:
            seg = get_fit(coureur, seance_dv, "tour2")
            if seg is None or "enhanced_speed" not in seg.columns:
                continue
            v = seg["enhanced_speed"].dropna() * 3.6
            fig.add_trace(go.Histogram(
                x=v, name=coureur,
                marker_color=COLORS.get(coureur, "#888"),
                opacity=0.65,
                histnorm="percent",
                xbins=dict(size=0.5),
                hovertemplate=f"<b>{coureur}</b><br>%{{x:.1f}} km/h · %{{y:.1f}}%<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, barmode="overlay", height=380,
                          xaxis=dict(**_AXIS, title="Vitesse (km/h)"),
                          yaxis=dict(**_AXIS, title="% du temps"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Violin plot :dispersion des vitesses"))
        fig2 = go.Figure()
        for coureur in coureurs_sel:
            seg = get_fit(coureur, seance_dv, "tour2")
            if seg is None or "enhanced_speed" not in seg.columns:
                continue
            v = seg["enhanced_speed"].dropna() * 3.6
            fig2.add_trace(go.Violin(
                y=v, name=coureur,
                fillcolor=COLORS.get(coureur, "#888"),
                line_color=COLORS.get(coureur, "#888"),
                opacity=0.7,
                box_visible=True,
                meanline_visible=True,
            ))
        fig2.update_layout(**LAYOUT, height=380,
                           yaxis=dict(**_AXIS, title="Vitesse (km/h)"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Zones de vitesse (% du temps par zone)"))
    zones = [(0, 10, "< 10 km/h"), (10, 15, "10–15"), (15, 20, "15–20"),
             (20, 25, "20–25"), (25, 30, "25–30"), (30, 100, "> 30 km/h")]
    zone_rows = []
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_dv, "tour2")
        if seg is None or "enhanced_speed" not in seg.columns:
            continue
        v = seg["enhanced_speed"].dropna() * 3.6
        row = {"Coureur": coureur}
        for lo, hi, label in zones:
            pct = ((v >= lo) & (v < hi)).sum() / len(v) * 100
            row[label] = f"{pct:.0f}%"
        zone_rows.append(row)
    if zone_rows:
        st.dataframe(pd.DataFrame(zone_rows).set_index("Coureur"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  14 :ALLURE INSTANTANÉE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "pace":
    st.title(T("Allure instantanée :Tour 2"))
    st.caption(T("min/km second-par-second · plus bas = plus rapide"))

    seance_ai = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="ai_seance")
    axe_ai = st.radio(T("X Axis"), [T("Time (s)"), T("Distance (m)")], horizontal=True, key="ai_axe")

    fig = go.Figure()
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_ai, "tour2")
        if seg is None or "enhanced_speed" not in seg.columns:
            continue
        seg_c = seg.dropna(subset=["enhanced_speed"]).copy()
        # Allure en s/km = 1000 / vitesse_ms, capée à 600 s/km (10 min/km)
        seg_c["allure_s_km"] = (1000 / seg_c["enhanced_speed"].replace(0, np.nan)).clip(upper=600)
        seg_c["allure_s_km"] = seg_c["allure_s_km"].rolling(3, center=True, min_periods=1).mean()
        seg_c["allure_label"] = seg_c["allure_s_km"].apply(
            lambda s: f"{int(s)//60}:{int(s)%60:02d}/km" if pd.notna(s) else "N/A"
        )
        x = seg_c["t_rel"] if axe_ai == T("Time (s)") else seg_c["dist_rel"]
        fig.add_trace(go.Scatter(
            x=x, y=seg_c["allure_s_km"],
            name=coureur, mode="lines",
            line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
            text=seg_c["allure_label"],
            hovertemplate=f"<b>{coureur}</b><br>%{{text}}<extra></extra>",
        ))
    fig.update_layout(
        **LAYOUT, height=420,
        xaxis=dict(**_AXIS, title=axe_ai),
        yaxis=dict(**_AXIS, autorange="reversed", title="Allure (s/km)",
                   tickvals=list(range(120, 601, 30)),
                   ticktext=[f"{v//60}:{v%60:02d}" for v in range(120, 601, 30)]),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader(T("Comparaison toutes séances :allure min atteinte"))
    fig2 = go.Figure()
    for coureur in coureurs_sel:
        pts = []
        for s in sorted(df_all["Séance"].unique()):
            seg = get_fit(coureur, s, "tour2")
            if seg is None or "enhanced_speed" not in seg.columns:
                continue
            v_max = seg["enhanced_speed"].max()
            if pd.notna(v_max) and v_max > 0:
                pts.append({"Séance": s, "allure_min": 1000 / v_max})
        if pts:
            d = pd.DataFrame(pts)
            fig2.add_trace(go.Scatter(
                x=d["Séance"], y=d["allure_min"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=10),
                text=d["allure_min"].apply(lambda s: f"{int(s)//60}:{int(s)%60:02d}/km"),
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
            ))
    fig2.update_layout(**LAYOUT, height=320,
                       xaxis=dict(**_AXIS, title="Séance", dtick=1),
                       yaxis=dict(**_AXIS, autorange="reversed", title="Allure sprint (s/km)"))
    st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  15 :PUISSANCE W/KG
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "wkg":
    st.title(T("Puissance relative :W/kg"))
    st.caption(T("Corrige le biais du profil Garmin Arthur 70 kg en rapportant la puissance au poids réel"))

    poids_info = " · ".join(f"{c} {POIDS.get(c, '?')} kg" for c in sorted(COUREURS_CONNUS) if c in coureurs_sel)
    st.info(f"Poids utilisés : {poids_info}")

    df_wkg = df.copy()
    df_wkg["Puissance_wkg"] = df_wkg.apply(
        lambda r: r["Puissance_w"] / POIDS.get(r["Coureur"], 70) if pd.notna(r["Puissance_w"]) else None,
        axis=1
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("W/kg par séance"))
        fig = go.Figure()
        for coureur in coureurs_sel:
            dc = df_wkg[df_wkg["Coureur"] == coureur].sort_values("Séance").dropna(subset=["Puissance_wkg"])
            if dc.empty:
                continue
            fig.add_trace(go.Scatter(
                x=dc["Séance"], y=dc["Puissance_wkg"],
                name=coureur, mode="lines+markers",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                marker=dict(size=11),
                text=[f"{v:.2f} W/kg" for v in dc["Puissance_wkg"]],
                hovertemplate=f"<b>{coureur}</b> · S%{{x}}<br>%{{text}}<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, height=360,
                          xaxis=dict(**_AXIS, title="Séance", dtick=1),
                          yaxis=dict(**_AXIS, title="W/kg"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("Comparaison Watts bruts vs W/kg"))
        st.caption(T("Voir si le classement change après correction du poids"))
        df_cmp = df_wkg.groupby("Coureur").agg(
            Puissance_brute=("Puissance_w", "mean"),
            Puissance_wkg=("Puissance_wkg", "mean"),
        ).reset_index().dropna()
        df_cmp = df_cmp.sort_values("Puissance_wkg", ascending=False)

        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            name="Watts bruts",
            x=df_cmp["Coureur"], y=df_cmp["Puissance_brute"],
            marker_color=[COLORS.get(c, "#888") for c in df_cmp["Coureur"]],
            opacity=0.3, 
            text=[f"{v:.0f}W" for v in df_cmp["Puissance_brute"]],
            textposition="outside",
            yaxis="y1",
        ))
        
        fig2.add_trace(go.Scatter(
            name="W/kg",
            x=df_cmp["Coureur"], y=df_cmp["Puissance_wkg"],
            mode="markers+text",
            marker=dict(size=18, color=[COLORS.get(c, "#888") for c in df_cmp["Coureur"]],
                        line=dict(width=2, color="#fff")),
            text=[f"{v:.2f}" for v in df_cmp["Puissance_wkg"]],
            textposition="top center",
            yaxis="y2", 
        ))

        fig2.update_layout(
            **LAYOUT, 
            height=400,
            showlegend=False, 
            yaxis=dict(
                **_AXIS, 
                title="Watts",
                range=[0, df_cmp["Puissance_brute"].max() * 1.2] 
            ),
            yaxis2=dict(
                **_AXIS, 
                overlaying="y", 
                side="right", 
                title="W/kg", 
                showgrid=False,
                range=[df_cmp["Puissance_wkg"].min() * 0.9, df_cmp["Puissance_wkg"].max() * 1.1],
                zeroline=False
            ),
        )
        st.plotly_chart(fig2, use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
#  16 :FC VS DISTANCE
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "hrdist":
    st.title(T("FC vs Distance :Tour 2"))
    st.caption(T("Réponse cardiaque en fonction de la position sur le 400m"))

    seance_fd = st.selectbox(T("Séance"), sorted(df["Séance"].unique()), key="fd_seance")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("FC vs Distance parcourue"))
        fig = go.Figure()
        for coureur in coureurs_sel:
            seg = get_fit(coureur, seance_fd, "tour2")
            if seg is None or "heart_rate" not in seg.columns:
                continue
            seg_c = seg.dropna(subset=["heart_rate", "dist_rel"])
            if seg_c.empty:
                continue
            y = seg_c["heart_rate"].rolling(3, center=True, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=seg_c["dist_rel"], y=y,
                name=coureur, mode="lines",
                line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
                hovertemplate=f"<b>{coureur}</b><br>%{{x:.0f}}m · %{{y:.0f}} bpm<extra></extra>",
            ))
        fig.update_layout(**LAYOUT, height=380,
                          xaxis=dict(**_AXIS, title="Distance (m)"),
                          yaxis=dict(**_AXIS, title="FC (bpm)"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(T("FC vs Vitesse (scatter)"))
        st.caption(T("Montre si la FC suit la vitesse instantanée"))
        fig2 = go.Figure()
        for coureur in coureurs_sel:
            seg = get_fit(coureur, seance_fd, "tour2")
            if seg is None:
                continue
            seg_c = seg.dropna(subset=["heart_rate", "enhanced_speed"])
            if seg_c.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=seg_c["enhanced_speed"] * 3.6,
                y=seg_c["heart_rate"],
                name=coureur, mode="markers",
                marker=dict(size=6, color=COLORS.get(coureur, "#888"), opacity=0.7),
                hovertemplate=f"<b>{coureur}</b><br>%{{x:.1f}} km/h · %{{y:.0f}} bpm<extra></extra>",
            ))
        fig2.update_layout(**LAYOUT, height=380,
                           xaxis=dict(**_AXIS, title="Vitesse (km/h)"),
                           yaxis=dict(**_AXIS, title="FC (bpm)"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("FC max / FC moy par 100m :qui souffre le plus en fin de course ?"))
    fig3 = go.Figure()
    marks = [("0–100m", 0, 100), ("100–200m", 100, 200), ("200–300m", 200, 300), ("300–400m", 300, 400)]
    for coureur in coureurs_sel:
        seg = get_fit(coureur, seance_fd, "tour2")
        if seg is None or "heart_rate" not in seg.columns:
            continue
        seg_c = seg.dropna(subset=["heart_rate", "dist_rel"])
        fc_by_zone = []
        for label, lo, hi in marks:
            zone = seg_c[(seg_c["dist_rel"] >= lo) & (seg_c["dist_rel"] < hi)]
            fc_by_zone.append(zone["heart_rate"].mean() if not zone.empty else None)
        fig3.add_trace(go.Scatter(
            x=[m[0] for m in marks], y=fc_by_zone,
            name=coureur, mode="lines+markers",
            line=dict(color=COLORS.get(coureur, "#888"), width=2.5),
            marker=dict(size=10),
            hovertemplate=f"<b>{coureur}</b> · %{{x}}<br>%{{y:.0f}} bpm<extra></extra>",
        ))
    fig3.update_layout(**LAYOUT, height=320,
                       xaxis=dict(**_AXIS, title="Zone 100m"),
                       yaxis=dict(**_AXIS, title="FC moy (bpm)"))
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  17 :VENT & DIRECTION
# ══════════════════════════════════════════════════════════════════════════════
elif page_key == "wind":
    st.title(T("Vent & Conditions météo détaillées"))

    has_meteo = "temperature_c" in df.columns and df["temperature_c"].notna().any()
    if not has_meteo:
        st.warning(T("Données météo non disponibles."))
        st.stop()

    df_meteo_all = df_all.drop_duplicates("Séance").sort_values("Séance")

    # ── Rose des vents par séance ──────────────────────────────────────────────
    st.subheader(T("Direction du vent par séance"))
    st.caption(T("S1 & S3 : même force (23.6 km/h) mais directions opposées :impact potentiel différent sur le parcours"))

    fig_wind = go.Figure()
    for _, row in df_meteo_all.iterrows():
        if pd.isna(row.get("vent_direction_deg")):
            continue
        angle = row["vent_direction_deg"]
        force = row["vent_kmh"]
        seance_n = int(row["Séance"])
        # Tracé radial
        fig_wind.add_trace(go.Scatterpolar(
            r=[0, force],
            theta=[angle, angle],
            mode="lines+markers",
            name=f"S{seance_n} ({row['Date']})",
            line=dict(width=3),
            marker=dict(size=[4, 12]),
            hovertemplate=f"S{seance_n} · {angle}° · {force:.1f} km/h<extra></extra>",
        ))
    fig_wind.update_layout(
        **LAYOUT, height=400,
        polar=dict(
            bgcolor="#1a1a1a",
            radialaxis=dict(visible=True, range=[0, 30], tickcolor="#555",
                            gridcolor="#333", color="#888"),
            angularaxis=dict(direction="clockwise", rotation=90,
                             tickmode="array",
                             tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                             ticktext=["N", "NE", "E", "SE", "S", "SO", "O", "NO"],
                             tickcolor="#555", gridcolor="#333", color="#e0e0e0"),
        ),
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(T("Tableau météo complet par séance"))
        meteo_table = df_meteo_all[[
            "Séance", "Date", "temperature_c", "temperature_ressentie_c",
            "humidite_pct", "vent_kmh", "vent_direction_deg", "precipitation_mm"
        ]].copy()
        meteo_table.columns = ["Séance", "Date", "Temp (°C)", "Ressenti (°C)",
                               "Humidité (%)", "Vent (km/h)", "Dir. vent (°)", "Précip. (mm)"]
        st.dataframe(meteo_table.set_index("Séance"), use_container_width=True)

    with col2:
        st.subheader(T("Corrélation vent × performance"))
        st.caption(T("Vent fort = temps plus lent ?"))
        df_vent = df_all.dropna(subset=["vent_kmh", "Temps400m_s"])
        fig2 = go.Figure()
        for coureur in sorted(df_all["Coureur"].unique()):
            dc = df_vent[df_vent["Coureur"] == coureur]
            if dc.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=dc["vent_kmh"], y=dc["Temps400m_s"],
                name=coureur, mode="markers",
                marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                            line=dict(width=2, color="#0d0d0d")),
                text=dc["Temps400m_str"],
                customdata=dc["Séance"],
                hovertemplate=f"<b>{coureur}</b> · S%{{customdata}}<br>"
                              f"Vent : %{{x:.1f}} km/h · %{{text}}<extra></extra>",
            ))
        add_trendline(fig2, df_vent["vent_kmh"], df_vent["Temps400m_s"])
        fig2.update_layout(**LAYOUT, height=360,
                           xaxis=dict(**_AXIS, title="Vent (km/h)"),
                           yaxis=dict(**_AXIS, autorange="reversed", title="Temps 400m (s)"))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T("Indice de confort :Température ressentie vs Temps 400m"))
    df_res = df_all.dropna(subset=["temperature_ressentie_c", "Temps400m_s"])
    fig3 = go.Figure()
    for coureur in sorted(df_all["Coureur"].unique()):
        dc = df_res[df_res["Coureur"] == coureur]
        if dc.empty:
            continue
        fig3.add_trace(go.Scatter(
            x=dc["temperature_ressentie_c"], y=dc["Temps400m_s"],
            name=coureur, mode="markers",
            marker=dict(size=14, color=COLORS.get(coureur, "#888"),
                        line=dict(width=2, color="#0d0d0d")),
            text=dc["Temps400m_str"],
            customdata=dc["Séance"],
            hovertemplate=f"<b>{coureur}</b> · S%{{customdata}}<br>"
                          f"Ressenti : %{{x:.1f}}°C · %{{text}}<extra></extra>",
        ))
    add_trendline(fig3, df_res["temperature_ressentie_c"], df_res["Temps400m_s"])
    fig3.update_layout(**LAYOUT, height=340,
                       xaxis=dict(**_AXIS, title="Température ressentie (°C)"),
                       yaxis=dict(**_AXIS, autorange="reversed", title="Temps 400m (s)"))
    st.plotly_chart(fig3, use_container_width=True)
