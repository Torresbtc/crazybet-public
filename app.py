import streamlit as st
import pandas as pd
import os
from datetime import datetime

DATA_DIR = "cache/public"

st.set_page_config(page_title="CrazyBet – Resumen Público", layout="wide")
st.title("📊 Resumen General – CrazyBet (Solo lectura)")

@st.cache_data(show_spinner=False)
def listar_fechas():
    archivos = [f for f in os.listdir(DATA_DIR) if f.startswith("all_ev_plus_") and f.endswith(".json")]
    fechas = [f.replace("all_ev_plus_", "").replace(".json", "") for f in archivos]
    return sorted(fechas, key=lambda x: datetime.strptime(x, "%Y-%m-%d"))

@st.cache_data(show_spinner=False)
def cargar_json(fecha):
    path = os.path.join(DATA_DIR, f"all_ev_plus_{fecha}.json")
    return pd.read_json(path)

fechas = listar_fechas()
if not fechas:
    st.warning("No hay archivos disponibles en cache/public.")
    st.stop()

fecha_sel = st.sidebar.selectbox("Fecha", list(reversed(fechas)))
df = cargar_json(fecha_sel)

# Filtros
tipos = sorted(df["tipo"].dropna().unique().tolist())
lados = sorted(df["lado"].dropna().unique().tolist())
resultados = sorted(df["resultado"].dropna().unique().tolist())

f_tipo = st.sidebar.multiselect("Tipo", tipos, default=tipos)
f_lado = st.sidebar.multiselect("Lado", lados, default=lados)
f_result = st.sidebar.multiselect("Resultado", resultados, default=resultados)
buscar = st.sidebar.text_input("Buscar jugador")

df_f = df[df["tipo"].isin(f_tipo) & df["lado"].isin(f_lado) & df["resultado"].isin(f_result)]
if buscar.strip():
    df_f = df_f[df_f["jugador"].str.lower().str.contains(buscar.lower())]

# Métricas
total = len(df_f)
aciertos = int((df_f["resultado"].astype(str).str.startswith("✅")).sum()) if total else 0
acc = round(100 * aciertos / total, 2) if total else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Picks", total)
c2.metric("Aciertos", aciertos)
c3.metric("Accuracy %", acc)

# Tabla
st.dataframe(df_f, use_container_width=True)

# Descargar CSV
csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV", csv, file_name=f"resumen_{fecha_sel}.csv")

st.caption("Datos en solo lectura desde JSON estáticos. No hay conexión a base de datos.")
