import streamlit as st
import pandas as pd
import os, re
from datetime import datetime, date
from typing import List

DATA_DIR = "cache/public"

st.set_page_config(page_title="Panel de Estadísticas – CrazyBet (público)", layout="wide")
st.title("📊 Panel de Estadísticas – CrazyBet")

# ---------- Utilidades ----------
def american_to_decimal(odds):
    try:
        o = float(odds)
    except Exception:
        return None
    if o > 0:
        return 1.0 + (o / 100.0)
    if o < 0:
        return 1.0 + (100.0 / abs(o))
    return None

@st.cache_data(show_spinner=False)
def fechas_disponibles() -> List[date]:
    """Escanea cache/public y devuelve las fechas disponibles (YYYY-MM-DD) ordenadas."""
    if not os.path.exists(DATA_DIR):
        return []
    fechas = []
    for fname in os.listdir(DATA_DIR):
        m = re.match(r"all_ev_plus_(\d{4}-\d{2}-\d{2})\.json$", fname)
        if m:
            try:
                fechas.append(datetime.strptime(m.group(1), "%Y-%m-%d").date())
            except Exception:
                pass
    return sorted(fechas)

@st.cache_data(show_spinner=False)
def cargar_por_fechas(fechas: List[date]) -> pd.DataFrame:
    """
    Lee todos los all_ev_plus_YYYY-MM-DD.json indicados,
    asigna 'fecha' a cada fila a partir del nombre del archivo,
    y completa/normaliza columnas base si faltan.
    """
    frames = []
    for d in fechas:
        fname = f"all_ev_plus_{d.strftime('%Y-%m-%d')}.json"
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_json(path)
            df["fecha"] = d.strftime("%Y-%m-%d")  # fecha tomada del nombre del archivo
            frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)

    # columnas base si faltan (incluye team)
    base_cols = [
        ("deporte", "MLB"),
        ("jugador", ""), ("team", ""), ("tipo", ""), ("linea", None),
        ("lado", ""), ("probabilidad", None), ("resultado", ""), ("odds", None),
        ("streak", None), ("streak_type", None),
    ]
    for c, default in base_cols:
        if c not in out.columns:
            out[c] = default

    # tipos numéricos
    for c in ["probabilidad", "odds", "linea", "streak"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # normaliza columnas de texto: NaN/None/"None" -> ""
    text_cols = ["deporte","jugador","team","tipo","lado","resultado","streak_type"]
    for c in text_cols:
        if c in out.columns:
            out[c] = out[c].astype(str)
            out[c] = out[c].where(out[c].notna(), "")
            out[c] = out[c].replace({"None": ""})

    return out

# ---------- Fechas / rango ----------
fechas = fechas_disponibles()
if not fechas:
    st.warning("No hay archivos en cache/public con formato all_ev_plus_YYYY-MM-DD.json.")
    st.stop()

st.sidebar.header("🔎 Filtros básicos")
# Rango (siempre 2 fechas)
rango = st.sidebar.date_input(
    "Rango de fechas",
    (fechas[-1], fechas[-1]),
    min_value=fechas[0],
    max_value=fechas[-1],
)

if isinstance(rango, tuple) and len(rango) == 2:
    f_ini, f_fin = rango
else:
    st.info("Selecciona **dos** fechas (inicio y fin).")
    st.stop()

# limitar a fechas disponibles realmente
fechas_rango = [f for f in fechas if f_ini <= f <= f_fin]
df = cargar_por_fechas(fechas_rango)
if df.empty:
    st.warning("No se encontraron datos en el rango seleccionado.")
    st.stop()

# ---------- Filtros estilo panel personal (sin EV) ----------
deportes = sorted([x for x in df["deporte"].dropna().astype(str).unique().tolist() if x])
jugadores = sorted([x for x in df["jugador"].dropna().astype(str).unique().tolist() if x])
tipos = sorted([x for x in df["tipo"].dropna().astype(str).unique().tolist() if x])
lados = sorted([x for x in df["lado"].dropna().astype(str).unique().tolist() if x])

dep_sel = st.sidebar.selectbox("Deporte", ["Todos"] + deportes, index=0)
jug_sel = st.sidebar.selectbox("Jugador", ["Todos"] + jugadores, index=0)
tipo_sel = st.sidebar.selectbox("Tipo de apuesta", ["Todos"] + tipos, index=0)
lado_sel = st.sidebar.selectbox("Lado", ["Todos"] + lados, index=0)

# Aplicación de filtros básicos
df_filtrado = df.copy()
if dep_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["deporte"] == dep_sel]
if jug_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["jugador"] == jug_sel]
if tipo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["tipo"] == tipo_sel]
if lado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["lado"] == lado_sel]

# ---------- Filtros avanzados activables (sin EV) ----------
st.sidebar.header("🧰 Filtros avanzados")
use_prob = st.sidebar.checkbox("Filtrar por probabilidad")
use_odds = st.sidebar.checkbox("Filtrar por Odds")
use_streak = st.sidebar.checkbox("Filtrar por Streak")

filtrados_por_metricas = 0
antes = len(df_filtrado)

if use_prob and "probabilidad" in df_filtrado.columns:
    pmin = float(df_filtrado["probabilidad"].min() if pd.notna(df_filtrado["probabilidad"].min()) else 0.0)
    pmax = float(df_filtrado["probabilidad"].max() if pd.notna(df_filtrado["probabilidad"].max()) else 1.0)
    pmin_sel, pmax_sel = st.sidebar.slider("Rango de probabilidad", 0.0, 1.0, (round(pmin, 2), round(pmax, 2)))
    df_filtrado = df_filtrado[df_filtrado["probabilidad"].between(pmin_sel, pmax_sel, inclusive="both")]

if use_odds and "odds" in df_filtrado.columns:
    omin = int(df_filtrado["odds"].min() if pd.notna(df_filtrado["odds"].min()) else -500)
    omax = int(df_filtrado["odds"].max() if pd.notna(df_filtrado["odds"].max()) else 500)
    o_sel = st.sidebar.slider("Odds mínimas (americanas)", min(-500, omin), max(500, omax), omin)
    df_filtrado = df_filtrado[df_filtrado["odds"] >= o_sel]

if use_streak and "streak" in df_filtrado.columns:
    smin = int(df_filtrado["streak"].min() if pd.notna(df_filtrado["streak"].min()) else 0)
    smax = int(df_filtrado["streak"].max() if pd.notna(df_filtrado["streak"].max()) else 0)
    s_sel = st.sidebar.slider("Streak mínimo", min(0, smin), max(10, smax if smax is not None else 0), smin if smin is not None else 0)
    df_filtrado = df_filtrado[(df_filtrado["streak"].fillna(0).astype(int) >= s_sel)]

filtrados_por_metricas = antes - len(df_filtrado)

# ---------- Métricas (sin EV) y transformación pública ----------
STAKE = 2.0

# Métricas base
total = len(df_filtrado)
aciertos = int(df_filtrado["resultado"].astype(str).str.startswith("✅").sum()) if total else 0
fallidos = int(df_filtrado["resultado"].astype(str).str.startswith("❌").sum()) if total else 0
voids   = int(df_filtrado["resultado"].astype(str).str.startswith("⛔").sum()) if total else 0
errores = int(df_filtrado["resultado"].astype(str).str.startswith("❓").sum()) if total else 0
accuracy = round(100.0 * aciertos / total, 2) if total else 0.0

# Convertir odds a decimal y calcular ganancia por fila
df_pub = df_filtrado.copy()
df_pub["odds"] = df_pub["odds"].apply(american_to_decimal)  # 'odds' pasa a ser decimal
df_pub["stake"] = STAKE

def _ganancia_row(row):
    res = str(row.get("resultado", ""))
    dec = row.get("odds", None)
    if res.startswith("✅") and dec is not None:
        return (dec - 1.0) * STAKE
    if res.startswith("❌"):
        return -1.0 * STAKE
    return 0.0  # ⛔️ / ❓

df_pub["ganancia_real"] = df_pub.apply(_ganancia_row, axis=1)

ganancia_real = float(df_pub["ganancia_real"].sum()) if total else 0.0
roi = round(100.0 * ganancia_real / (total * STAKE), 2) if total else 0.0

# ---------- Render del resumen ----------
st.markdown("## 📌 Resumen General")
st.markdown(
    f"""
- **Rango de fechas:** {fechas_rango[0]} → {fechas_rango[-1]}
- **Total picks:** {total}
- ✅ **Aciertos:** {aciertos}
- ❌ **Fallidos:** {fallidos}
- ⛔️ **Void:** {voids}
- ❓ **Error:** {errores}
- 🧪 **Filtrados por métricas:** {filtrados_por_metricas}
- 📊 **Accuracy:** {accuracy}%
- 📈 **ROI:** {roi}%
- 💵 **Ganancia real:** {ganancia_real:.2f}
"""
)

# ---------- Tabla pública (solo columnas solicitadas, sin EV) ----------
cols_public = [
    "fecha", "deporte", "jugador", "team", "tipo", "linea",
    "lado", "probabilidad", "resultado", "odds",   # 'odds' ya es decimal
    "streak", "streak_type", "stake", "ganancia_real",
]
# Asegura que existan
for c in cols_public:
    if c not in df_pub.columns:
        df_pub[c] = None

df_show = df_pub.reindex(columns=cols_public)

# limpieza final de texto (evita 'None')
for c in ["deporte","jugador","team","tipo","lado","resultado","streak","streak_type"]:
    if c in df_show.columns:
        df_show[c] = df_show[c].astype(str).replace({"None": ""})
        df_show[c] = df_show[c].where(df_show[c].notna(), "")

st.subheader("Vista pública")
st.dataframe(df_show, use_container_width=True)

# ---------- Descarga CSV (solo columnas solicitadas) ----------
csv = df_show.to_csv(index=False).encode("utf-8")
st.download_button(
    "Descargar CSV",
    data=csv,
    file_name=f"public_{fechas_rango[0]}_{fechas_rango[-1]}.csv"
)

st.caption("Datos en solo lectura desde JSON estáticos. No hay conexión a base de datos.")
