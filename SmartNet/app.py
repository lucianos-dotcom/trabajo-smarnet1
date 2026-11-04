import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from model import TYPES, ACTIVITIES, RATES, BASE, calculate

st.set_page_config(page_title='SmartNet · Wi-Fi', page_icon='📶', layout='wide')
st.markdown('<style>.block-container{max-width:1200px} [data-testid="stMetric"]{border:1px solid #64748b;border-radius:14px;padding:18px}</style>', unsafe_allow_html=True)
st.caption('📶 SMARTNET · FUNCIONES Y MATRICES · INACAP')
st.title('Comprende la demanda de tu Wi-Fi')
st.write('Explora cómo influyen los dispositivos y sus actividades simultáneas en tu conexión.')
st.info('Simulador educativo: estima demanda con valores de referencia. No mide tráfico ni detecta saturación real.')
with st.sidebar:
    st.header('Tu escenario')
    capacity = st.number_input('Capacidad B (Mbps)', min_value=0.1, value=20.0, step=5.0, key='capacity')
    st.caption('La capacidad disponible puede diferir de la velocidad contratada.')
    st.subheader('Consumo por actividad')
    rates = np.array([st.number_input(f'{activity} (Mbps)', min_value=0.0, value=float(rate), step=0.5, key=f'rate_{activity}') for activity, rate in zip(ACTIVITIES, RATES)])
    st.caption('Valores ilustrativos editables; no son mediciones ni estándares universales.')
    st.button('Restaurar ejemplo', on_click=lambda: st.session_state.clear())
st.subheader('1. Organiza tus dispositivos')
st.caption('Filas = tipos de equipo; columnas = actividades. Cuenta cada dispositivo una sola vez según su actividad principal simultánea.')
initial = pd.DataFrame(BASE, columns=ACTIVITIES)
initial.insert(0, 'Equipo', TYPES)
edited = st.data_editor(initial, disabled=['Equipo'], hide_index=True, key='devices', num_rows='fixed', width='stretch', column_config={name:st.column_config.NumberColumn(name, min_value=0, max_value=1000, step=1, required=True) for name in ACTIVITIES})
try:
    matrix = edited[ACTIVITIES].to_numpy(dtype=float)
    demand, total, usage, status = calculate(matrix, capacity, rates)
except (ValueError, TypeError) as exc:
    st.error(str(exc))
    st.stop()
st.subheader('2. Interpreta el resultado')
a, b, c = st.columns(3)
a.metric('Demanda estimada', f'{total:.1f} Mbps')
b.metric('Demanda / referencia', f'{usage:.1f}%')
c.metric('Dispositivos', str(int(matrix.sum())))
if usage > 100:
    st.error(f'{status}: excede la referencia en {total-capacity:.1f} Mbps. Reduce actividades simultáneas o prueba una capacidad mayor.')
elif usage == 100:
    st.warning('Al límite: la demanda iguala la capacidad; no queda margen en este modelo.')
else:
    st.success(f'{status}: quedan {capacity-total:.1f} Mbps de margen estimado.')
left, right = st.columns(2)
with left:
    st.plotly_chart(px.bar(x=TYPES, y=demand, labels={'x':'Tipo de equipo', 'y':'Demanda (Mbps)'}, title='Demanda por equipo', color_discrete_sequence=['#0ea5e9']), width='stretch')
with right:
    st.plotly_chart(px.bar(x=['Demanda', 'Capacidad'], y=[total, capacity], labels={'x':'Referencia', 'y':'Mbps'}, title='¿Alcanza la capacidad?', color_discrete_sequence=['#14b8a6']), width='stretch')
with st.expander('3. Matrices y función, paso a paso', expanded=True):
    st.write('A contiene cantidades y b contiene Mbps por actividad. A · b entrega la demanda por tipo de equipo.')
    cols = st.columns(3)
    cols[0].write('**Matriz A**')
    cols[0].dataframe(pd.DataFrame(matrix.astype(int), index=TYPES, columns=ACTIVITIES))
    cols[1].write('**Vector b (Mbps)**')
    cols[1].dataframe(pd.DataFrame({'Mbps':rates}, index=ACTIVITIES))
    cols[2].write('**A · b (Mbps)**')
    cols[2].dataframe(pd.DataFrame({'Mbps':demand}, index=TYPES))
    st.latex(r'C=\sum_i(A\cdot b)_i \qquad U(C)=\frac{C}{B}\times100')
    st.write(f"C = {' + '.join(f'{v:g}' for v in demand)} = **{total:g} Mbps**")
    st.write(f'U({total:g}) = ({total:g} / {capacity:g}) × 100 = **{usage:g}%**')
    x = np.linspace(0, max(capacity*1.5, total*1.2), 100)
    fig = px.line(x=x, y=x/capacity*100, labels={'x':'Demanda C (Mbps)', 'y':'U(C) (%)'}, title='Función de demanda respecto de B')
    fig.add_hline(y=100, line_dash='dash', annotation_text='100% = capacidad de referencia')
    fig.add_scatter(x=[total], y=[usage], mode='markers', name='Escenario actual')
    st.plotly_chart(fig, width='stretch')
st.subheader('4. Compara escenarios')
if st.button('Guardar escenario actual para comparar'):
    st.session_state['comparison'] = (matrix.copy(), capacity, rates.copy())
if 'comparison' in st.session_state:
    old_matrix, old_capacity, old_rates = st.session_state['comparison']
    _, old_total, old_usage, old_status = calculate(old_matrix, old_capacity, old_rates)
    st.dataframe(pd.DataFrame({'Escenario':['Guardado','Actual'], 'Capacidad (Mbps)':[old_capacity,capacity], 'Demanda (Mbps)':[old_total,total], 'Porcentaje (%)':[old_usage,usage], 'Estado':[old_status,status]}), hide_index=True, width='stretch')
    st.caption('El escenario guardado conserva cantidades, capacidad y consumos durante esta sesión.')
else:
    st.caption('Guarda un escenario, cambia las cantidades o la capacidad y compara los resultados.')
report = edited.copy()
report['Demanda (Mbps)'] = demand
st.download_button('Descargar detalle en CSV', report.to_csv(index=False).encode('utf-8-sig'), 'smartnet.csv', 'text/csv')
st.caption('Modelo simplificado: no considera cobertura, interferencia, protocolos ni diferencias entre subida y bajada.')
