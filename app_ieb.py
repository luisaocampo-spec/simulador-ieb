import streamlit as st
import pandas as pd
import time
import json
import os
import re

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="Simulador Auditoría IEB", page_icon="🛸", layout="wide")

# Estilos CSS: Letra extra grande para respuestas y preguntas, dejando el menú intacto
st.markdown("""
    <style>
    /* Aumentar la etiqueta principal del radio (Seleccione la respuesta...) */
    .stRadio > label > div > p {
        font-size: 22px !important;
        font-weight: bold !important;
        color: #333 !important;
        margin-bottom: 15px !important;
    }
    /* Aumentar el tamaño del texto de cada OPCIÓN de respuesta */
    .stRadio p { 
        font-size: 22px !important; 
        line-height: 1.6 !important;
    }
    /* Darle más espacio (aire) entre cada opción para que sea fácil hacer clic */
    div[role="radiogroup"] > label {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    /* Aumentar el tamaño de los mensajes de Correcto/Incorrecto */
    .stAlert p { 
        font-size: 22px !important; 
    }
    /* Botón de Contestar más grande */
    .stButton button {
        padding: 10px 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES BASE
def limpiar_referencias(text):
    if isinstance(text, str) and "[" in text:
        partes = text.split("[")
        resultado = partes[0]
        for p in partes[1:]:
            if "]" in p:
                resultado += p.split("]", 1)[1]
            else:
                resultado += "[" + p 
        return resultado.strip()
    elif isinstance(text, str):
        return text.strip()
    return text

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('preguntas.csv', sep=';', encoding='latin-1')
    except Exception:
        df = pd.read_csv('preguntas.csv', sep=',', encoding='utf-8')
    for col in df.columns:
        df[col] = df[col].apply(limpiar_referencias)
    return df

try:
    df_completo = load_data()
except Exception as e:
    st.error(f"❌ Error al cargar el CSV: {e}")
    st.stop()

# 3. ESTADOS DE LA SESIÓN
if 'index' not in st.session_state:
    st.session_state.index = 0
if 'results' not in st.session_state:
    st.session_state.results = {}  
if 'user_choices' not in st.session_state:
    st.session_state.user_choices = {} 
if 'modo_repaso' not in st.session_state:
    st.session_state.modo_repaso = False

# Cronómetro
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'total_elapsed' not in st.session_state:
    st.session_state.total_elapsed = 0.0
if 'last_start_time' not in st.session_state:
    st.session_state.last_start_time = time.time()

# 4. LÓGICA DE GUARDADO/CARGA JSON
def guardar_progreso():
    data = {
        'results': st.session_state.results,
        'user_choices': st.session_state.user_choices,
        'total_elapsed': st.session_state.total_elapsed + (0 if st.session_state.is_paused else (time.time() - st.session_state.last_start_time))
    }
    with open('progreso.json', 'w') as f:
        json.dump(data, f)
    st.toast("💾 Progreso guardado con éxito")

def cargar_progreso():
    if os.path.exists('progreso.json'):
        with open('progreso.json', 'r') as f:
            data = json.load(f)
        st.session_state.results = {int(k): v for k, v in data['results'].items()}
        st.session_state.user_choices = {int(k): v for k, v in data['user_choices'].items()}
        st.session_state.total_elapsed = data.get('total_elapsed', 0.0)
        st.session_state.last_start_time = time.time()
        st.toast("📂 Progreso cargado")
    else:
        st.toast("⚠️ No hay progreso guardado")

# 5. FILTRADO DE DATOS
if st.session_state.modo_repaso:
    falladas = [i for i, v in st.session_state.results.items() if not v]
    df_activo = df_completo.iloc[falladas].reset_index()
else:
    df_activo = df_completo.copy().reset_index()

total_q_activo = len(df_activo)

# Calcular Tiempo
if st.session_state.is_paused:
    current_time = st.session_state.total_elapsed
else:
    current_time = st.session_state.total_elapsed + (time.time() - st.session_state.last_start_time)

mins, secs = divmod(int(current_time), 60)
tiempo_str = f"{mins:02d}:{secs:02d}"

# Calcular Estadísticas
correctas = sum(1 for v in st.session_state.results.values() if v == True)
incorrectas = sum(1 for v in st.session_state.results.values() if v == False)
respondidas = len(st.session_state.results)
puntaje = (correctas / len(df_completo)) * 100 if len(df_completo) > 0 else 0

# 6. INTERFAZ GRÁFICA
col_main, col_nav = st.columns([3, 1], gap="large")

with col_main:
    st.title("🛸 Simulador UAS - IEB" + (" (MODO REPASO)" if st.session_state.modo_repaso else ""))
    
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Correctas", correctas)
    c2.metric("❌ Incorrectas", incorrectas)
    c3.metric("📈 Puntaje", f"{puntaje:.1f}%")
    c4.metric("⏱️ Tiempo", tiempo_str)
    
    if st.session_state.is_paused:
        if st.button("▶️ Reanudar Tiempo", type="primary"):
            st.session_state.is_paused = False
            st.session_state.last_start_time = time.time()
            st.rerun()
        st.warning("⏸️ **Simulacro en pausa.**")
    else:
        if st.button("⏸️ Pausar Tiempo"):
            st.session_state.is_paused = True
            st.session_state.total_elapsed += time.time() - st.session_state.last_start_time
            st.rerun()
            
    st.markdown("---")

    # MODO EXAMEN / PREGUNTAS
    if not st.session_state.is_paused and st.session_state.index < total_q_activo:
        row = df_activo.iloc[st.session_state.index]
        real_index = row['index'] 
        
        st.write(f"**Pregunta {st.session_state.index + 1} de {total_q_activo}** | 📊 Respondidas globales: {respondidas} / {len(df_completo)}")
        st.progress((st.session_state.index + 1) / total_q_activo)
        
        # PREGUNTA EN TAMAÑO EXTRA GRANDE
        st.markdown(f"<div style='font-size: 28px; font-weight: bold; color: #1f77b4; line-height: 1.4; margin-bottom: 20px;'>{row['Pregunta']}</div>", unsafe_allow_html=True)

        opciones_map = {
            "Opción A": row['Opción A'],
            "Opción B": row['Opción B'],
            "Opción C": row['Opción C'],
            "Opción D": row['Opción D']
        }
        
        col_correcta = str(row['Respuesta Correcta']).strip()
        texto_correcto = opciones_map.get(col_correcta, "Opción no encontrada")
        ya_respondida = real_index in st.session_state.results
        
        # CAJA CON SCROLL PARA LAS RESPUESTAS (Alto fijo de 450px)
        with st.container(height=450, border=True):
            seleccion = st.radio(
                "Seleccione la respuesta correcta:",
                options=list(opciones_map.values()),
                index=None,
                disabled=ya_respondida, 
                key=f"radio_{real_index}"
            )

        st.write("") # Espacio en blanco

        # RESULTADOS
        if ya_respondida:
            eleccion_usuario = st.session_state.user_choices[real_index]
            es_correcta = st.session_state.results[real_index]
            
            st.markdown(f"<div style='font-size: 22px;'><b>Tu respuesta:</b> {eleccion_usuario}</div><br>", unsafe_allow_html=True)
            if es_correcta:
                st.success("✅ **¡CORRECTO!**")
            else:
                st.error("❌ **INCORRECTO**")
                st.info(f"La respuesta correcta era: **{texto_correcto}**")
                
                if 'Explicación' in df_activo.columns and pd.notna(row['Explicación']):
                    with st.expander("📚 Ver Referencia Documental"):
                        st.write(row['Explicación'])
                
            if st.button("Siguiente Pregunta ➡️", type="primary"):
                if st.session_state.index < total_q_activo - 1:
                    st.session_state.index += 1
                    st.rerun()
        else:
            if st.button("Contestar 📩", type="primary"):
                if seleccion:
                    st.session_state.user_choices[real_index] = seleccion
                    st.session_state.results[real_index] = (seleccion == texto_correcto)
                    st.rerun()
                else:
                    st.warning("⚠️ Elige una opción antes de enviar.")

    # PANTALLA FINAL
    elif not st.session_state.is_paused and st.session_state.index >= total_q_activo:
        st.balloons()
        st.header("🏁 ¡Análisis del Simulacro!")
        
        if puntaje >= 80:
            st.success("🏆 **APROBADO:** Cumples con el estándar.")
        else:
            st.error("⚠️ **NO APROBADO:** Nivel por debajo del 80% exigido.")
            
        if incorrectas > 0:
            st.subheader("📚 Preguntas a repasar:")
            for i, row in df_completo.iterrows():
                if i in st.session_state.results and not st.session_state.results[i]:
                    with st.expander(f"Pregunta {i+1}: {str(row['Pregunta'])[:60]}..."):
                        col_c = str(row['Respuesta Correcta']).strip()
                        text_c = row.get(col_c, "No encontrada")
                        st.write(f"**Pregunta:** {row['Pregunta']}")
                        st.write(f"**Tu respuesta:** {st.session_state.user_choices[i]}")
                        st.write(f"**Correcta:** ✅ {text_c}")

# ================= ÁREA DE NAVEGACIÓN Y HERRAMIENTAS =================
with col_nav:
    st.markdown("### 🛠️ Herramientas")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("💾 Guardar"): guardar_progreso()
    with c_btn2:
        if st.button("📂 Cargar"): cargar_progreso(); st.rerun()
        
    st.markdown("---")
    
    if incorrectas > 0 and not st.session_state.modo_repaso:
        if st.button("📚 Repasar Falladas", use_container_width=True):
            st.session_state.modo_repaso = True
            st.session_state.index = 0
            st.rerun()
            
    if st.session_state.modo_repaso:
        if st.button("🔙 Volver a Modo Normal", use_container_width=True):
            st.session_state.modo_repaso = False
            st.session_state.index = 0
            st.rerun()

    if st.button("🔄 Reiniciar Todo", use_container_width=True):
        st.session_state.index = 0
        st.session_state.results = {}
        st.session_state.user_choices = {}
        st.session_state.is_paused = False
        st.session_state.total_elapsed = 0.0
        st.session_state.last_start_time = time.time()
        st.session_state.modo_repaso = False
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 🗺️ Mapa de Preguntas")
    with st.container(height=350):
        for idx in range(total_q_activo):
            real_id = df_activo.iloc[idx]['index']
            if real_id in st.session_state.results:
                estado = "✅" if st.session_state.results[real_id] else "❌"
            else:
                estado = "⚪" 
            
            prefix = "➡️ " if idx == st.session_state.index else ""
            if st.button(f"{prefix}{estado} P {real_id + 1}", key=f"nav_{idx}", use_container_width=True, disabled=st.session_state.is_paused):
                st.session_state.index = idx
                st.rerun()
                
    st.markdown("---")
    st.info("👩‍✈️ **Creado por:**\n\n**Luisa Fernanda Ocampo**\n\n*Jefe de Pilotos*")