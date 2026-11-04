import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from household import ACTIVITIES, DEVICES, RATES, PRESETS, evaluate, improve

st.set_page_config(page_title='SmartNet · Internet en casa', page_icon='📶', layout='wide')
st.markdown('''<style>
.block-container{max-width:1120px;padding-top:2rem}
[data-testid="stMetric"]{border:1px solid #94a3b8;border-radius:16px;padding:18px}
div.stButton>button{border-radius:12px;min-height:44px}
</style>''', unsafe_allow_html=True)

def load_preset():
    for key in list(st.session_state):
        if key.startswith(('device_', 'activity_', 'count_')):
            del st.session_state[key]
    st.session_state.rows = [dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n) for d,a,n in PRESETS[st.session_state.preset]]

if 'rows' not in st.session_state:
    st.session_state.preset = 'Una tarde en casa'
    load_preset()

st.caption('📶 SMARTNET · INTERNET EN CASA')
st.title('¿Alcanza tu internet para todos?')
st.write('Cuéntanos qué están haciendo en tu casa y prueba cómo evitar que la conexión se quede corta.')
st.caption('Simulación educativa. No escanea tu Wi-Fi ni mide el tráfico real; estima la demanda de las actividades que ingreses.')

st.subheader('1 · Elige la velocidad de tu internet')
plan = st.selectbox('¿Cuántos megas tiene tu plan?', ['No sé mi velocidad', 'Ingresar otra velocidad', '20 Mbps', '100 Mbps', '300 Mbps', '500 Mbps', '600 Mbps', '800 Mbps', '940 Mbps', '1000 Mbps'], index=4, key='plan')
st.caption('En Chile los planes suelen anunciar “megas”: por ejemplo, 600 megas = 600 Mbps. Las opciones son ejemplos orientativos, no un catálogo vigente de compañías.')
known = plan != 'No sé mi velocidad'
if not known:
    st.info('Busca los megas en la boleta o app de tu compañía. También puedes hacer un test de velocidad en el equipo y lugar donde usas internet.')
    capacity = st.number_input('Mientras tanto, ¿con qué velocidad quieres probar? (Mbps)', min_value=0.1, value=100.0, key='trial_capacity')
    st.caption('El resultado será hipotético hasta que conozcas tu velocidad.')
elif plan == 'Ingresar otra velocidad':
    capacity = st.number_input('Velocidad de descarga (Mbps)', min_value=0.1, value=20.0, key='custom_capacity')
else:
    capacity = float(plan.split()[0])
with st.expander('Tengo un test de velocidad o uso internet móvil'):
    st.write('En fibra, cable o internet hogar 4G/5G, usa preferentemente la descarga que obtengas con un test en tu equipo. La velocidad de un plan no garantiza esa misma capacidad por Wi-Fi. No ingreses los GB de tu bolsa: indican cantidad de datos, no velocidad.')
    use_test = st.checkbox('Usar mi velocidad medida en vez de la del plan', key='use_test')
    measured = st.number_input('Descarga que mostró el test (Mbps)', min_value=0.1, value=100.0, key='measured')
    if use_test:
        capacity = measured
        known = True

st.subheader('2 · ¿Qué están haciendo al mismo tiempo?')
st.selectbox('Prueba un ejemplo o arma tu casa', list(PRESETS), key='preset', on_change=load_preset)
st.caption('Agrega solo equipos en uso. Cuenta cada equipo una vez: elige su actividad principal. Un celular conectado sin uso no equivale a uno viendo videos.')
rows = []
for i, row in enumerate(st.session_state.rows):
    with st.container(border=True):
        a,b,c,d = st.columns([3,4,2,1])
        device = a.selectbox(f'Equipo {i+1}', DEVICES, index=DEVICES.index(row['device']), key=f'device_{i}')
        activity = b.selectbox(f'Actividad {i+1}', ACTIVITIES, index=ACTIVITIES.index(row['activity']), key=f'activity_{i}')
        count = c.number_input(f'Cantidad {i+1}', min_value=0, max_value=100, value=row['count'], step=1, key=f'count_{i}')
        if d.button('Quitar', key=f'remove_{i}'):
            # Conservar las ediciones de todas las filas antes de reordenar.
            updated = [dict(device=st.session_state.get(f'device_{j}',r['device']), activity=st.session_state.get(f'activity_{j}',r['activity']), count=int(st.session_state.get(f'count_{j}',r['count']))) for j,r in enumerate(st.session_state.rows) if j != i]
            st.session_state.rows = updated
            for key in list(st.session_state):
                if key.startswith(('device_', 'activity_', 'count_')):
                    del st.session_state[key]
            st.rerun()
        rows.append(dict(device=device, activity=activity, count=int(count)))
st.session_state.rows = rows
if st.button('＋ Agregar otro equipo', key='add'):
    st.session_state.rows.append(dict(device=DEVICES[0], activity=ACTIVITIES[0], count=1))
    st.rerun()

matrix, demand, total, usage, level = evaluate(rows, capacity)
st.subheader('3 · Así se ve tu casa')
if not known:
    st.warning('Escenario hipotético: confirma tu velocidad para interpretar el resultado en tu casa.')
if not matrix.sum():
    st.info('Agrega al menos un equipo en uso para simular tu casa.')
elif usage > 100:
    st.error('🔴 Posible saturación: las actividades piden más de lo que permite la velocidad elegida. Algunas podrían competir por la conexión.')
elif usage >= 80:
    st.warning('🟡 Queda poco margen: la demanda está cerca de la capacidad. Una descarga adicional podría afectar las otras actividades.')
else:
    st.success('🟢 Hay margen para estas actividades según el modelo. Esto no garantiza una buena señal Wi-Fi en todas las piezas.')
a,b,c = st.columns(3)
a.metric('Lo que necesita tu casa', f'{total:g} Mbps')
b.metric('Velocidad usada como referencia', f'{capacity:g} Mbps')
c.metric('Parte de la conexión ocupada', f'{usage:.1f}%')
st.progress(min(usage / 100, 1.0))
st.caption('100% significa que la demanda iguala la capacidad. Sobre 100%, la barra se llena y el porcentaje sigue mostrando el exceso. Amarillo desde 80%: margen preventivo orientativo.')

st.subheader('4 · Prueba una solución antes de cambiar de plan')
pause = st.checkbox('Dejar las descargas de juegos o archivos para más tarde', key='pause')
lower = st.checkbox('Ver en HD en vez de 4K', key='lower')
new_rows = improve(rows, pause, lower)
_, _, new_total, new_usage, new_level = evaluate(new_rows, capacity)
if pause or lower:
    st.metric('Demanda con estos cambios', f'{new_total:g} Mbps', delta=f'{new_total-total:g} Mbps', delta_color='inverse')
    st.write(f'Pasarías de **{usage:.1f}% a {new_usage:.1f}%** de la conexión. Resultado estimado: **{new_level.lower()}**.')
    if new_total == total:
        st.caption('Estos cambios no afectan tu escenario: no hay descargas o videos en 4K activos que reducir.')
    elif new_usage > 100:
        st.warning('Todavía supera la referencia. Prueba repartir más actividades en distintos horarios.')
with st.expander('Mi internet anda lento aunque aquí aparezca verde'):
    st.write('La velocidad y la señal Wi-Fi son cosas distintas. Prueba acercarte al router y repetir un test; si mejora, puede haber un problema de cobertura. Ubica el router en un lugar central y despejado. Para una consola o PC fijo, prueba cable de red si es posible.')
    st.write('Si se corta un juego, importan también el ping y la estabilidad. En videollamadas y cámaras importa la velocidad de subida. Este simulador representa principalmente demanda de descarga y no diagnostica esos problemas. No se incluyen cámaras de seguridad: necesitan un análisis de subida.')
    st.write('Si incluso cerca del router o por cable sigue lento, compara varios tests y consulta a tu compañía. El simulador por sí solo no indica que debas contratar un plan más caro.')

with st.expander('Ver qué actividades piden más internet'):
    by_activity = matrix.sum(axis=0) * RATES
    st.plotly_chart(px.bar(x=by_activity, y=ACTIVITIES, orientation='h', labels={'x':'Demanda estimada (Mbps)', 'y':'Actividad'}, color_discrete_sequence=['#0ea5e9']), width='stretch')

with st.expander('Para la asignatura · Matrices y funciones'):
    st.write('Las filas de A son tipos de equipo; las columnas, actividades. b contiene la demanda de referencia de cada actividad. A · b entrega Mbps por equipo.')
    st.dataframe(pd.DataFrame(matrix, index=DEVICES, columns=ACTIVITIES))
    st.dataframe(pd.DataFrame({'Actividad':ACTIVITIES, 'b (Mbps)':RATES}), hide_index=True)
    st.dataframe(pd.DataFrame({'Equipo':DEVICES, 'A · b (Mbps)':demand}), hide_index=True)
    st.latex(r'C=\sum_i(A\cdot b)_i \qquad U(C)=\frac{C}{B}\times100')
    st.write(f'C = {total:g} Mbps; U(C) = ({total:g} / {capacity:g}) × 100 = {usage:g}%.')
    x = np.linspace(0, max(capacity*1.2, total*1.1), 100)
    fig = px.line(x=x,y=x/capacity*100,labels={'x':'Demanda C (Mbps)','y':'U(C) (%)'})
    fig.add_hline(y=100,line_dash='dash')
    fig.add_scatter(x=[total],y=[usage],mode='markers',name='Tu casa')
    st.plotly_chart(fig,width='stretch')
    st.caption('Para reproducir la entrega: elige “Ejemplo de la asignatura” y una velocidad personalizada de 20 Mbps. Resultado: 14,5 Mbps y 72,5%.')
with st.expander('Referencias y límites de esta simulación'):
    st.write('Los consumos son supuestos didácticos fijos por equipo activo, no mediciones ni requisitos garantizados de una plataforma. Video HD: 5 Mbps; 4K: 25; navegación: 0,5; videollamada: 1,5; juego online: 3; descarga: 50.')
    st.write('Una descarga usa un valor supuesto de 50 Mbps para comparar escenarios, pero en la realidad puede usar gran parte de la conexión disponible. Jugar no equivale a descargar un juego. Calidad de video, compresión y aplicaciones cambian el consumo.')
    st.write('Las velocidades ofrecidas en Chile cambian según compañía, dirección y tecnología. Confirma tu plan en la boleta o app de tu proveedor; SmartNet no compara ofertas comerciales ni precios. No se incluye medición de interferencia, latencia, cobertura o capacidad de subida.')
report = pd.DataFrame(matrix, index=DEVICES, columns=ACTIVITIES)
report['Demanda (Mbps)'] = demand
st.download_button('Descargar mis datos',report.to_csv().encode('utf-8-sig'),'smartnet.csv','text/csv')
st.caption('SmartNet · Proyecto educativo de Funciones y Matrices · Analista Programador · INACAP')
