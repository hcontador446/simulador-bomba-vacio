import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador - Bomba de Vacío", page_icon="⚙️", layout="wide")

# 2. --- MENÚ LATERAL ---
st.sidebar.title("⚙️ Panel de Control")

propiedades_gas = {
    "Aire": {"color": "#555555", "vibracion": 0.05, "masa": "29 g/mol"},
    "Nitrógeno (N2)": {"color": "#0000FF", "vibracion": 0.05, "masa": "28 g/mol"},
    "Argón (Ar)": {"color": "#800080", "vibracion": 0.015, "masa": "40 g/mol"},
    "Helio (He)": {"color": "#FF007F", "vibracion": 0.25, "masa": "4 g/mol"}
}

tipo_gas = st.sidebar.selectbox("Tipo de Gas", list(propiedades_gas.keys()))
num_particulas = st.sidebar.slider("Cantidad de Partículas Iniciales", 100, 3000, 1000, 100)

st.sidebar.markdown("### Instrumentación")
tipo_sensor = st.sidebar.selectbox("Tipo de Sensor de Presión", ["Sensor Capacitivo", "Sensor Pirani"])

st.sidebar.markdown("### Parámetros Operativos")
velocidad = st.sidebar.slider("Velocidad de la Bomba (RPM)", 100, 3000, 1500, 100)
fuerza_succion = st.sidebar.slider("Fuerza de Succión", 1.0, 10.0, 5.0, 1.0)
ancho_puerto = st.sidebar.slider("Ancho del Puerto de Vacío (Radio)", 1.0, 4.0, 2.5, 0.5)

st.sidebar.markdown("### Parámetros de Simulación")
pasos_simulacion = st.sidebar.slider("Pasos de Simulación (Frames)", 30, 150, 60, 10)
agitacion_termica = st.sidebar.slider("Agitación Térmica (Multiplicador)", 0.0, 5.0, 1.0, 0.1)

st.sidebar.divider()
st.sidebar.info("Proyecto Universitario - Termodinámica y Vacío.")

# --- LÓGICA DEL SENSOR DE PRESIÓN ---
if tipo_sensor == "Sensor Capacitivo":
    factor_sensor = 1.0
elif tipo_sensor == "Sensor Pirani":
    if tipo_gas == "Helio (He)":
        factor_sensor = 1.5
    elif tipo_gas == "Argón (Ar)":
        factor_sensor = 0.75
    else:
        factor_sensor = 1.0

st.title("Simulador 3D: Dinámica de Fluidos y Evacuación")
st.write(f"Evaluando **{tipo_gas}** con un **{tipo_sensor}**. El factor de corrección térmico es **{factor_sensor}x**.")

color_actual = propiedades_gas[tipo_gas]["color"]
jitter_amp = propiedades_gas[tipo_gas]["vibracion"] * agitacion_termica
frame_duration = max(20, int(40000 / velocidad)) 

# 3. --- PARÁMETROS GEOMÉTRICOS ---
R_s = 10; R_r = 6; altura = 20; excentricidad = -3.5

theta_cilindros = np.linspace(0, 2*np.pi, 60)
z_vals = np.linspace(0, altura, 2)
theta_grid, z_grid = np.meshgrid(theta_cilindros, z_vals)

x_s = R_s * np.cos(theta_grid); y_s = R_s * np.sin(theta_grid)
x_r = R_r * np.cos(theta_grid); y_r = R_r * np.sin(theta_grid) + excentricidad

def crear_tuberia(angulo, radio_tubo, longitud, radio_estator, z_centro):
    u = np.linspace(radio_estator, radio_estator + longitud, 10)
    v = np.linspace(0, 2*np.pi, 30)
    U, V = np.meshgrid(u, v)
    x_prime = U; y_prime = radio_tubo * np.cos(V); z_prime = radio_tubo * np.sin(V) + z_centro
    X = x_prime * np.cos(angulo) - y_prime * np.sin(angulo)
    Y = x_prime * np.sin(angulo) + y_prime * np.cos(angulo)
    return X, Y, z_prime

x_in, y_in, z_in = crear_tuberia(np.pi/4, 2.5, 4, R_s, altura/2)
x_out, y_out, z_out = crear_tuberia(5*np.pi/4, ancho_puerto, 4, R_s, altura/2)

def calcular_extremos_paleta(angulo, desplazamiento_y, radio_estator):
    a = 1; b = 2 * desplazamiento_y * np.sin(angulo); c = desplazamiento_y**2 - radio_estator**2
    discriminante = b**2 - 4*a*c
    r1 = (-b + np.sqrt(discriminante)) / (2*a)
    r2 = (-b - np.sqrt(discriminante)) / (2*a)
    return (r1 * np.cos(angulo), desplazamiento_y + r1 * np.sin(angulo)), (r2 * np.cos(angulo), desplazamiento_y + r2 * np.sin(angulo))

# 4. --- LÓGICA DE EVACUACIÓN Y PARTÍCULAS ---
np.random.seed(42)
theta_0_particulas = np.random.uniform(0, 2*np.pi, num_particulas)
r_frac_particulas = np.random.uniform(0.1, 0.9, num_particulas)
z_particulas = np.random.uniform(0.5, altura - 0.5, num_particulas)

angulo_salida_base = 4.2
ajuste_puerto = ancho_puerto * 0.1
ajuste_succion = fuerza_succion * 0.03
angulo_salida_efectivo = max(3.2, angulo_salida_base - ajuste_puerto - ajuste_succion)
angulo_objetivo = np.where(theta_0_particulas < angulo_salida_efectivo, angulo_salida_efectivo, angulo_salida_efectivo + 2*np.pi)

# 5. --- GENERACIÓN DE FRAMES ---
angulos_rotacion = np.linspace(0, 2.2 * np.pi, pasos_simulacion) 
frames = []
historial_tiempo = []
historial_particulas = []
historial_sensor = []

max_escala_sensor = num_particulas * 1.5

for i, angulo_base in enumerate(angulos_rotacion):
    frame_data = []
    
    # A) Paletas 3D
    for angulo in [angulo_base, angulo_base + np.pi/2]:
        p1, p2 = calcular_extremos_paleta(angulo, excentricidad, R_s)
        x_pal = np.array([[p1[0], p2[0]], [p1[0], p2[0]]])
        y_pal = np.array([[p1[1], p2[1]], [p1[1], p2[1]]])
        frame_data.append(go.Surface(x=x_pal, y=y_pal, z=np.array([[0, 0], [altura, altura]])))
    
    # B) Partículas 3D 
    angulo_actual_absoluto = theta_0_particulas + angulo_base
    valid_mask = angulo_actual_absoluto < angulo_objetivo 
    
    t_valid = angulo_actual_absoluto[valid_mask] % (2*np.pi)
    rf_valid = r_frac_particulas[valid_mask]
    z_valid = z_particulas[valid_mask]
    
    r_jitter = np.random.normal(0, jitter_amp, size=len(t_valid))
    z_jitter = np.random.normal(0, jitter_amp, size=len(t_valid))
    
    r_rot_actual = excentricidad * np.sin(t_valid) + np.sqrt(R_r**2 - excentricidad**2 * np.cos(t_valid)**2)
    r_pos = r_rot_actual + rf_valid * (R_s - r_rot_actual) + r_jitter
    r_pos = np.clip(r_pos, r_rot_actual, R_s - 0.2) 
    z_pos = np.clip(z_valid + z_jitter, 0.5, altura - 0.5)
    
    frame_data.append(go.Scatter3d(
        x=r_pos * np.cos(t_valid), y=r_pos * np.sin(t_valid), z=z_pos,
        mode='markers', marker=dict(size=3, color=color_actual, opacity=0.8)
    ))
    
    # C) Cálculos de Presión
    presion_real = np.sum(valid_mask)
    presion_sensor = presion_real * factor_sensor 
    
    historial_tiempo.append(i)
    historial_particulas.append(presion_real)
    historial_sensor.append(presion_sensor)
    
    # D) Gráfica 2D (Línea Real vs Línea Sensor)
    frame_data.append(go.Scatter(x=list(historial_tiempo), y=list(historial_particulas), mode='lines', line=dict(color='gray', width=2, dash='dash'), name='Presión Real'))
    frame_data.append(go.Scatter(x=list(historial_tiempo), y=list(historial_sensor), mode='lines', line=dict(color=color_actual, width=3), name='Lectura Sensor'))
    
    # E) Medidor tipo Reloj (Gauge)
    frame_data.append(go.Indicator(
        mode="gauge+number", value=presion_sensor, title={'text': "Presión Sensor (mbar sim.)"},
        gauge=dict(
            axis=dict(range=[0, max_escala_sensor]),
            bar=dict(color="black", thickness=0.2),
            steps=[
                dict(range=[0, max_escala_sensor * 0.3], color="#A8E6CF"),        # Verde: Buen vacío
                dict(range=[max_escala_sensor * 0.3, max_escala_sensor * 0.7], color="#FFD3B6"), # Amarillo: Vacío medio
                dict(range=[max_escala_sensor * 0.7, max_escala_sensor], color="#FF8A8A")        # Rojo: Presión alta
            ]
        )
    ))
    
    frames.append(go.Frame(data=frame_data, traces=[4, 5, 6, 7, 8, 9], name=f'frame{i}'))

# 6. --- ENSAMBLAJE DE LA INTERFAZ ---
# Ajustamos la cuadrícula: 2 filas. F1C1 = 3D, F2C1 = Reloj, F1C2 (ocupa 2 filas) = Gráfica 2D
fig = make_subplots(
    rows=2, cols=2, 
    column_widths=[0.60, 0.40], row_heights=[0.75, 0.25],
    specs=[[{"type": "surface"}, {"type": "xy", "rowspan": 2}], 
           [{"type": "indicator"}, None]],
    subplot_titles=("Cámara de Vacío 3D", "Evacuación: Real vs Lectura del Sensor", "")
)

luz_metal = dict(ambient=0.4, diffuse=0.8, specular=0.8, roughness=0.2, fresnel=0.2)
luz_cristal = dict(ambient=0.6, diffuse=0.5, specular=1.0, roughness=0.1, fresnel=0.6)

# Trazos estáticos (Cámara 3D) [0, 1, 2, 3]
fig.add_trace(go.Surface(x=x_s, y=y_s, z=z_grid, colorscale=[[0, 'rgba(60, 60, 60, 0.4)'], [1, 'rgba(100, 100, 100, 0.4)']], showscale=False, opacity=0.45, lighting=luz_cristal), row=1, col=1)
fig.add_trace(go.Surface(x=x_r, y=y_r, z=z_grid, colorscale=[[0, '#333333'], [0.5, '#778899'], [1, '#DCDCDC']], showscale=False, opacity=1.0, lighting=luz_metal), row=1, col=1)
fig.add_trace(go.Surface(x=x_in, y=y_in, z=z_in, colorscale=[[0, 'rgba(60, 60, 60, 0.6)'], [1, 'rgba(100, 100, 100, 0.6)']], showscale=False, opacity=0.6, lighting=luz_cristal), row=1, col=1)
fig.add_trace(go.Surface(x=x_out, y=y_out, z=z_out, colorscale=[[0, 'rgba(60, 60, 60, 0.6)'], [1, 'rgba(100, 100, 100, 0.6)']], showscale=False, opacity=0.6, lighting=luz_cristal), row=1, col=1)

# Trazos dinámicos del frame inicial [4, 5, 6, 7, 8, 9]
fig.add_trace(go.Surface(x=frames[0].data[0].x, y=frames[0].data[0].y, z=frames[0].data[0].z, colorscale=[[0, '#8B4513'], [1, '#DA8A67']], showscale=False, lighting=luz_metal), row=1, col=1)
fig.add_trace(go.Surface(x=frames[0].data[1].x, y=frames[0].data[1].y, z=frames[0].data[1].z, colorscale=[[0, '#8B4513'], [1, '#DA8A67']], showscale=False, lighting=luz_metal), row=1, col=1)
fig.add_trace(frames[0].data[2], row=1, col=1) 
fig.add_trace(frames[0].data[3], row=1, col=2) # Linea Real
fig.add_trace(frames[0].data[4], row=1, col=2) # Linea Sensor
fig.add_trace(frames[0].data[5], row=2, col=1) # Gauge

fig.frames = frames
color_fondo = '#E6F3FF'

fig.update_layout(
    paper_bgcolor=color_fondo, plot_bgcolor='white', 
    margin=dict(l=10, r=10, b=10, t=50),
    showlegend=True, legend=dict(x=0.75, y=0.95, bgcolor="rgba(255,255,255,0.8)"), # Leyenda para las líneas
    scene=dict(
        bgcolor=color_fondo,
        xaxis=dict(visible=False, range=[-15, 15]), yaxis=dict(visible=False, range=[-15, 15]), zaxis=dict(visible=False, range=[0, 20]),
        aspectmode='manual', aspectratio=dict(x=1, y=1, z=1),
        camera=dict(eye=dict(x=1.3, y=-1.6, z=1.5))
    ),
    updatemenus=[dict(
        type="buttons", showactive=False, x=0.01, y=1.05, 
        buttons=[
            dict(label="▶ Iniciar Simulación", method="animate", args=[None, {"frame": {"duration": frame_duration, "redraw": True}, "fromcurrent": True, "transition": {"duration": 0}}]),
            dict(label="⏸ Pausar", method="animate", args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}])
        ], bgcolor='white', font=dict(color='black', size=14)
    )]
)

fig.update_xaxes(title_text="Tiempo (Frames)", range=[0, pasos_simulacion], row=1, col=2, showgrid=True, gridcolor='lightgray')
fig.update_yaxes(title_text="Presión (mbar sim.)", range=[0, max_escala_sensor], row=1, col=2, showgrid=True, gridcolor='lightgray')

st.plotly_chart(fig, use_container_width=True)