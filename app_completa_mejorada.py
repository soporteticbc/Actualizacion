
import os
from io import BytesIO
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

# =============================
# Configuración básica de la app
# =============================
st.set_page_config(
    page_title="Evaluación de Estudiantes",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos simples (tarjetas y footer)
st.markdown(
    """
    
    """,
    unsafe_allow_html=True,
)

# =============================
# Conexión a Supabase
# =============================
SUPABASE_URL = "https://hdgzzerdfphnalntfmnh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhkZ3p6ZXJkZnBobmFsbnRmbW5oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI2ODQ3NDYsImV4cCI6MjA2ODI2MDc0Nn0.PrZGzatAjsVcMepmKdhlT303Cf1FbFAcGnhzlrUhPeU"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# Archivos locales
# =============================
ARCHIVO_ESTUDIANTES = "estudiantes 1 1 1.csv"
ARCHIVO_PREGUNTAS  = "preguntas 1 1 1.csv"
ARCHIVO_MAESTROS   = "maestros.csv"

# =============================
# Funciones auxiliares
# =============================
@st.cache_data(ttl=600)
def cargar_csv(ruta: str, encoding: str = "latin1"):
    if os.path.exists(ruta):
        return pd.read_csv(ruta, encoding=encoding)
    return None

@st.cache_data(ttl=120)
def obtener_respuestas_filtradas(filtro: dict | None = None) -> pd.DataFrame:
    try:
        q = supabase.table("respuestas").select("*")
        if filtro:
            for k, v in filtro.items():
                q = q.eq(k, v)
        data = q.execute().data
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error consultando Supabase: {e}")
        return pd.DataFrame()

# =============================
# Sidebar / Menú
# =============================
menu = [
    "🏠 Inicio",
    "📝 Evaluar estudiantes",
    "📊 Ver reportes",
    "📚 Reportes generales por estudiante",
]
opcion = st.sidebar.selectbox("Menú", menu)

maestros_df = cargar_csv(ARCHIVO_MAESTROS)
if maestros_df is None or maestros_df.empty:
    st.error("No se encontró el archivo de maestros.")
    st.stop()

lista_maestros = sorted(maestros_df["maestro"].dropna().unique())
maestro = st.sidebar.selectbox("👤 Selecciona tu nombre", lista_maestros)

# =============================
# Página de inicio
# =============================
if opcion == "🏠 Inicio":
        st.image("imagen_inicio.png", width=250)
        st.markdown("<h1 style='text-align:center; color:#1E3A8A;'>Evaluación Estudiantil</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>Bienvenido al sistema de evaluación del Colegio Bautista Cristiano.</p>", unsafe_allow_html=True)
        st.markdown("---")

# =============================
# Sección: Evaluar estudiantes
# =============================
if opcion == "📝 Evaluar estudiantes":
    estudiantes_df = cargar_csv(ARCHIVO_ESTUDIANTES)
    preguntas_df   = cargar_csv(ARCHIVO_PREGUNTAS)

    if (estudiantes_df is None) or (preguntas_df is None):
        st.error("Faltan archivos de estudiantes o preguntas.")
        st.stop()

    cursos_maestro = maestros_df.loc[maestros_df["maestro"] == maestro, "curso"].dropna().unique()

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        curso = st.selectbox("🏫 Curso", sorted(cursos_maestro))
    with c2:
        materias_maestro = maestros_df[(maestros_df["maestro"] == maestro) & (maestros_df["curso"] == curso)]["materia"].dropna().unique()
        materia = st.selectbox("📘 Materia", sorted(materias_maestro))
    with c3:
        estudiantes_curso = estudiantes_df.loc[estudiantes_df["curso"] == curso]
        estudiante = st.selectbox("🧑‍🎓 Estudiante", sorted(estudiantes_curso["nombre"].dropna().unique()))

    # Tarjeta informativa
    st.markdown(
        f"""
        <div class="kpi-card">
            <div style="font-size:18px; font-weight:700;">👦 {estudiante}</div>
            <div class="soft">Curso: <b>{curso}</b> &nbsp;|&nbsp; Materia: <b>{materia}</b> &nbsp;|&nbsp; Maestro: <b>{maestro}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📋 Cuestionario")
    preguntas_materia = preguntas_df.loc[preguntas_df["materia"] == materia]

    opciones = [
        "Incumplimiento",
        "Incumplimiento parcial",
        "Cumplimiento",
        "Excede cumplimiento",
    ]

    respuestas_payload = []
    if not preguntas_materia.empty:
        for _, row in preguntas_materia.iterrows():
            pregunta = str(row.get("texto", ""))
            if not pregunta:
                continue
            st.markdown(f"<div class='question'>📌 {pregunta}</div>", unsafe_allow_html=True)
            resp = st.radio(
                label="",
                options=opciones,
                key=f"radio_{pregunta}",
                horizontal=True,
            )
            respuestas_payload.append(
                {
                    "maestro": maestro,
                    "curso": curso,
                    "estudiante": estudiante,
                    "materia": materia,
                    "pregunta": pregunta,
                    "respuesta": resp,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

    if st.button("✅ Guardar evaluación", use_container_width=True) and respuestas_payload:
        q = supabase.table("respuestas").select("*").match({
            "maestro": maestro,
            "curso": curso,
            "estudiante": estudiante,
            "materia": materia,
        }).execute()

        if q.data:
            st.warning("⚠️ Ya has evaluado a este estudiante para esta materia.")
        else:
            for registro in respuestas_payload:
                supabase.table("respuestas").insert(registro).execute()
            st.balloons()
            st.success("¡Evaluación guardada exitosamente!")
            obtener_respuestas_filtradas.clear()

# =============================
# Sección: Ver reportes
# =============================
if opcion == "📊 Ver reportes":
    df = obtener_respuestas_filtradas({"maestro": maestro})

    if df.empty:
        st.info("Aún no hay respuestas para este maestro.")
    else:
        c1, c2 = st.columns([1, 1])
        with c1:
            estudiante = st.selectbox("🧑‍🎓 Estudiante", sorted(df["estudiante"].dropna().unique()))
        with c2:
            materia = st.selectbox("📘 Materia", sorted(df["materia"].dropna().unique()))

        df_f = df[(df["estudiante"] == estudiante) & (df["materia"] == materia)].copy()
        if df_f.empty:
            st.warning("No hay datos para esa combinación.")
            st.stop()

        total_resp = len(df_f)
        positivas = (df_f["respuesta"].isin(["Cumplimiento", "Excede cumplimiento"]).sum())
        pct_positivas = (positivas / total_resp * 100) if total_resp else 0
        preguntas_unicas = df_f["pregunta"].nunique()

        k1, k2, k3 = st.columns(3)
        with k1:
            st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
            st.metric("⭐ Total de respuestas", f"{total_resp}")
            st.markdown("</div>", unsafe_allow_html=True)
        with k2:
            st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
            st.metric("📈 % positivas", f"{pct_positivas:.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        with k3:
            st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
            st.metric("📚 Preguntas evaluadas", f"{preguntas_unicas}")
            st.markdown("</div>", unsafe_allow_html=True)

        conteo = df_f["respuesta"].value_counts().reset_index()
        conteo.columns = ["respuesta", "cantidad"]
        orden = ["Incumplimiento", "Incumplimiento parcial", "Cumplimiento", "Excede cumplimiento"]
        conteo["respuesta"] = pd.Categorical(conteo["respuesta"], categories=orden, ordered=True)
        conteo = conteo.sort_values("respuesta")

        fig_pie = px.pie(conteo, names="respuesta", values="cantidad", hole=0.35)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

# =============================
# Sección: Reportes generales por estudiante
# =============================
if opcion == "📚 Reportes generales por estudiante":
    df_total = obtener_respuestas_filtradas()
    if df_total.empty:
        st.info("No hay respuestas disponibles.")
    else:
        estudiante = st.selectbox("🧑‍🎓 Estudiante", sorted(df_total["estudiante"].dropna().unique()))
        df_est = df_total[df_total["estudiante"] == estudiante].copy()
        if df_est.empty:
            st.warning("Este estudiante aún no tiene evaluaciones.")
            st.stop()

        orden = ["Incumplimiento", "Incumplimiento parcial", "Cumplimiento", "Excede cumplimiento"]
        df_est["respuesta"] = pd.Categorical(df_est["respuesta"], categories=orden, ordered=True)
        resumen = df_est.groupby(["materia", "respuesta"]).size().reset_index(name="cantidad")

        fig_bar = px.bar(
            resumen,
            x="materia",
            y="cantidad",
            color="respuesta",
            barmode="stack",
            category_orders={"respuesta": orden},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        matriz = df_est.groupby(["materia", "respuesta"]).size().unstack(fill_value=0)
        st.dataframe(matriz, use_container_width=True)


st.markdown("""
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    text-align: center;
    padding: 14px 0;
    font-size: 17px;
    color: #0F172A;
    background-color: #F1F5F9;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    font-family: 'Segoe UI', sans-serif;
    z-index: 9999;
}
</style>
<div class="footer">
🧑‍💻 <b>Desarrollador por: Steven Polanco (IT support)</b>
</div>
""", unsafe_allow_html=True)

