import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from household import (ACTIVITIES, DEVICES, RATES, UPLOAD_RATES, PRESETS, BANDS,
                       SIGNALS, network_summary, improve)
from speed_test import render_speed_test, valid_result
from results import STATES, checks, verdict

st.set_page_config(page_title='SmartNet · Internet en casa', page_icon='📶', layout='wide')
st.markdown('''<style>.block-container{max-width:1180px;padding-top:2rem}
[data-testid="stMetric"]{border:1px solid #94a3b8;border-radius:16px;padding:16px}
div.stButton>button{border-radius:12px;min-height:44px}
[class*="st-key-family_card_"][class*="_good"]{border-top:5px solid #22c55e}
[class*="st-key-family_card_"][class*="_tight"]{border-top:5px solid #eab308}
[class*="st-key-family_card_"][class*="_over"]{border-top:5px solid #ef4444}
[class*="st-key-family_card_"][class*="_unknown"]{border-top:5px solid #94a3b8}
.st-key-family_summary{border-left:6px solid #0ea5e9}
</style>''', unsafe_allow_html=True)
ROW_PREFIXES = ('device_', 'activity_', 'count_', 'band_')

def clear_rows():
    for key in list(st.session_state):
        if key.startswith(ROW_PREFIXES):
            del st.session_state[key]

def load_preset():
    clear_rows()
    st.session_state.rows = [dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n, band=BANDS[3])
                            for d,a,n in PRESETS[st.session_state.preset]]

def choose_device(i):
    device = st.session_state[f'device_{i}']
    activity = 6 if device == DEVICES[4] else 7 if device in [DEVICES[7], DEVICES[8], DEVICES[9], DEVICES[10]] else 0
    st.session_state[f'activity_{i}'] = ACTIVITIES[activity]

def apply_measurement():
    result = st.session_state.last_speed
    st.session_state.measured = float(result['download'])
    st.session_state.upload_capacity = float(result['upload'])
    st.session_state.use_test = True
    st.session_state.know_upload = True

if 'rows' not in st.session_state:
    st.session_state.preset = 'Una tarde en casa'
    load_preset()

st.caption('📶 SMARTNET · INTERNET EN CASA')
st.title('¿Alcanza tu internet para todos?')
st.write('Mide tu conexión, cuenta qué están haciendo en casa y prueba soluciones antes de cambiar de plan.')
st.caption('El test mide la conexión de este equipo; el simulador estima demanda. No detectamos automáticamente equipos, banda, señal ni interferencias.')

st.subheader('1 · Conoce tu conexión')
with st.expander('📶 Hacer un test de velocidad aquí', expanded=True):
    st.write('Hazlo desde el equipo y lugar donde notas lentitud. Pausa otras descargas para una referencia más limpia. Repite cerca del router o con cable para comparar.')
    location = st.selectbox('¿Dónde estás haciendo la prueba?', ['Donde noto lentitud', 'Cerca del router', 'Con cable de red', 'Otro lugar'], key='test_location')
    result = render_speed_test(location)
    if valid_result(result):
        if st.session_state.get('speed_id') != result['id']:
            st.session_state.speed_id = result['id']
            st.session_state.last_speed = result
            history = st.session_state.get('speed_history', [])
            history.append(dict(result, lugar=result.get('location', 'Sin etiqueta')))
            st.session_state.speed_history = history[-5:]
    if 'last_speed' in st.session_state:
        result = st.session_state.last_speed
        st.write(f"**Última prueba:** {result['download']:.1f} Mbps de descarga · {result['upload']:.1f} Mbps de subida · respuesta HTTP {result['latency']:.0f} ms.")
        st.caption(f"Fecha UTC: {result['timestamp']}. Variación entre respuestas HTTP: {result['jitter']:.0f} ms. No es un ping ICMP ni mide pérdida de paquetes.")
        if result['latency'] >= 150:
            st.info('La respuesta HTTP fue alta en esta prueba. Puede influir en actividades interactivas; repite cerca del router o con cable. No permite atribuir el problema al Wi-Fi por sí sola.')
        st.button('Usar esta medición en mi simulación', on_click=apply_measurement, key='apply_speed')
        if len(st.session_state.speed_history) > 1:
            st.dataframe(pd.DataFrame(st.session_state.speed_history)[['timestamp','lugar','download','upload','latency']].rename(columns={'download':'Descarga Mbps','upload':'Subida Mbps','latency':'Respuesta HTTP ms'}), hide_index=True)
    st.caption('Prueba breve y aproximada: incluye el camino hasta Cloudflare, navegador y tráfico simultáneo. No certifica el plan ni identifica por sí sola la causa de lentitud. Los resultados se conservan solo durante esta sesión.')

plan = st.selectbox('¿Cuántos megas tiene tu plan?', ['No sé mi velocidad', 'Ingresar otra velocidad', '20 Mbps', '100 Mbps', '300 Mbps', '500 Mbps', '600 Mbps', '800 Mbps', '940 Mbps', '1000 Mbps'], index=4, key='plan')
st.caption('En Chile “600 megas” suele referirse a 600 Mbps. Estas opciones son ejemplos, no ofertas comerciales vigentes. Revisa la boleta o app de tu compañía. GB de una bolsa de datos no son Mbps.')
known = plan != 'No sé mi velocidad'
if not known:
    capacity = st.number_input('Velocidad hipotética para probar (Mbps)', min_value=0.1, value=100.0, key='trial_capacity')
elif plan == 'Ingresar otra velocidad':
    capacity = st.number_input('Descarga de referencia (Mbps)', min_value=0.1, value=20.0, key='custom_capacity')
else:
    capacity = float(plan.split()[0])
use_test = st.checkbox('Usar una velocidad medida en vez de la del plan', key='use_test')
if use_test:
    capacity = st.number_input('Descarga medida (Mbps)', min_value=0.001, value=100.0, format='%.2f', key='measured')
    known = True
    st.caption('Esta es una referencia del equipo y lugar probado, no la capacidad total comprobada de toda la casa. Si había otras actividades, refleja capacidad disponible durante esa prueba; no permite separar sus causas.')
know_upload = st.checkbox('Conozco mi velocidad de subida (o la obtuve en el test)', key='know_upload')
upload = st.number_input('Subida de referencia (Mbps)', min_value=0.001, value=20.0, format='%.2f', key='upload_capacity') if know_upload else None
if upload is None:
    st.caption('Sin referencia de subida mostraremos su demanda, pero no podremos decir si cámaras, llamadas o respaldos la superan.')

st.subheader('2 · Tu Wi-Fi: ¿2,4 o 5 GHz?')
st.write('Elige la banda de cada equipo más abajo. Si no la sabes, selecciona “No sé la banda”; el cálculo de internet sigue funcionando.')
with st.expander('¿Cuál me conviene?'):
    st.table(pd.DataFrame({'Característica':['Alcance y paredes','Velocidad potencial','Interferencia habitual','Uso orientativo'], '2,4 GHz':['Suele llegar más lejos y atravesar mejor paredes','Generalmente menor','Suele haber más redes y aparatos compartiendo espectro','Equipos alejados y dispositivos inteligentes'], '5 GHz':['Suele perder más señal con distancia y paredes','Generalmente mayor en condiciones favorables','Generalmente más canales disponibles; también puede congestionarse','Video, PC y consolas cerca del router']}))
    st.write('5 GHz no siempre es mejor: lejos del router puede rendir peor. La banda no fija una velocidad universal. Router, equipos, ancho de canal, señal y vecinos influyen. Un equipo conectado sin uso genera mucha menos demanda que uno descargando.')
    st.caption('Puedes buscar la banda en las propiedades Wi-Fi de Windows o en la app del router. El nombre de la red no siempre identifica la banda. Cambiar la banda aquí solo simula; no reconfigura el equipo ni el router.')
model_wifi = st.checkbox('Comparar las dos bandas con capacidades supuestas', key='model_wifi')
band_caps = {}
if model_wifi:
    st.info('Modelo educativo, no medición del canal. Los valores 80 y 300 Mbps son hipótesis editables. La distancia aplica factores supuestos y no detecta señal real.')
    cols = st.columns(2)
    for col, band, default in zip(cols, BANDS[:2], [80.0,300.0]):
        with col:
            nominal = st.number_input(f'Capacidad supuesta {band} (Mbps)', min_value=0.1, value=default, key=f'wifi_capacity_{band}')
            signal = st.selectbox(f'Escenario de señal {band}', list(SIGNALS), key=f'signal_{band}')
            band_caps[band] = nominal * SIGNALS[signal]
            st.caption(f'Referencia efectiva supuesta: {band_caps[band]:g} Mbps. Se aplica al grupo completo de esa banda; es una simplificación.')

st.subheader('3 · ¿Qué están haciendo al mismo tiempo?')
st.selectbox('Prueba un ejemplo o arma tu casa', list(PRESETS), key='preset', on_change=load_preset)
st.caption('Cada fila agrupa equipos con la misma actividad y banda. Cuenta cada equipo una sola vez. Para cámaras, elige “Cámara transmitiendo a la nube”; una cámara que graba solo en memoria local no equivale a subir video a internet.')
rows=[]
for i,row in enumerate(st.session_state.rows):
    with st.container(border=True):
        a,b,c = st.columns([3,4,2])
        device = a.selectbox(f'Equipo {i+1}', DEVICES, index=DEVICES.index(row['device']), key=f'device_{i}', on_change=choose_device, args=(i,))
        activity = b.selectbox(f'Actividad {i+1}', ACTIVITIES, index=ACTIVITIES.index(row['activity']), key=f'activity_{i}')
        count = c.number_input(f'Cantidad {i+1}', min_value=0, max_value=100, value=row['count'], step=1, key=f'count_{i}')
        band = st.selectbox(f'Conexión del grupo {i+1}', BANDS, index=BANDS.index(row.get('band',BANDS[3])), key=f'band_{i}')
        if st.button('Quitar este grupo', key=f'remove_{i}'):
            updated = [dict(device=st.session_state.get(f'device_{j}',r['device']), activity=st.session_state.get(f'activity_{j}',r['activity']), count=int(st.session_state.get(f'count_{j}',r['count'])), band=st.session_state.get(f'band_{j}',r.get('band',BANDS[3]))) for j,r in enumerate(st.session_state.rows) if j!=i]
            st.session_state.rows=updated
            clear_rows()
            st.rerun()
        rows.append(dict(device=device, activity=activity, count=int(count), band=band))
st.session_state.rows=rows
if st.button('＋ Agregar otro equipo', key='add'):
    st.session_state.rows.append(dict(device=DEVICES[0], activity=ACTIVITIES[0], count=1, band=BANDS[3]))
    st.rerun()

summary = network_summary(rows,capacity,upload,band_caps)
items = checks(summary, known, model_wifi)
incomplete_bands = bool(model_wifi and summary['bands'][BANDS[3]]['matrix'].sum())
active = bool(summary['matrix'].sum())
overall, headline, explanation = verdict(items, active, incomplete_bands)
st.subheader('4 · Así está tu casa en este ejemplo')
with st.container(border=True,key='family_summary'):
    st.markdown(f'### {headline}')
    st.write(explanation)
    st.caption('Piensa en internet como una entrada y una salida: ver series trae datos; una cámara que transmite envía datos. Cada lado puede llenarse por separado.')
st.caption('Es una estimación de las actividades que ingresaste, no un diagnóstico automático de tu red.')
if not known:
    st.info('🔎 Falta saber la velocidad de tu casa. Puedes medirla arriba o encontrar los megas en tu boleta. Los números de descarga actuales son solo un ejemplo.')
if incomplete_bands:
    st.info('🔎 Algunos equipos tienen “No sé la banda”. Están contados para internet, pero todavía no podemos ubicarlos en 2,4 o 5 GHz.')

if active:
    cols=st.columns(2)
    for index,item in enumerate(items):
        icon,label=STATES[item['state']]
        with cols[index%2]:
            with st.container(border=True,key=f"family_card_{index}_{item['state']}"):
                st.markdown(f"#### {item['title']}")
                st.write(item['explanation'])
                st.markdown(f'**{icon} {label}**')
                if item['usage'] is not None:
                    st.progress(min(item['usage']/100,1.0))
                    if item['state']=='over':
                        st.write('Las actividades necesitan más espacio del que hay disponible en esta referencia.')
                    elif item['state']=='tight':
                        st.write('Cabe muy justo: si se suma otra actividad, podría faltar espacio.')
                    else:
                        st.write('Estas actividades caben y todavía queda margen en el cálculo.')
                    if item['state'] in ['over','tight']:
                        st.caption(item['tip'])
                elif item['key']=='upload':
                    st.write('El test de arriba puede darte la velocidad de subida. Luego pulsa “Usar esta medición”.')
                else:
                    st.write('Haz el test de arriba o ingresa una velocidad que conozcas.')
                if item['key'] in BANDS[:2]:
                    st.caption('Esta tarjeta usa una capacidad y señal supuestas; no medidas.')

    activity_down = summary['matrix'].sum(axis=0)*RATES
    activity_up = summary['matrix'].sum(axis=0)*UPLOAD_RATES
    with st.expander('🍰 ¿Qué se lleva la mayor parte?'):
        st.write('No todos los equipos piden lo mismo. Estas son las actividades que más datos necesitan en tu ejemplo:')
        left,right=st.columns(2)
        for col,values,title in [(left,activity_down,'Para recibir datos'),(right,activity_up,'Para enviar datos')]:
            with col:
                st.markdown(f'**{title}**')
                total_activity=float(values.sum())
                for i in np.argsort(-values)[:3]:
                    if values[i]>0:
                        st.write(f'{ACTIVITIES[i]} · {values[i]/total_activity*100:.0f}% de lo que pide tu casa')
                        st.progress(float(values[i]/total_activity))
        st.caption('Estas porciones comparan actividades entre sí; no indican cuánto queda de tu plan.')

with st.expander('🔢 Quiero ver los números'):
    a,b,c=st.columns(3)
    a.metric('Demanda de descarga',f"{summary['down']:g} Mbps")
    b.metric('Descarga de referencia',f'{capacity:g} Mbps')
    c.metric('Demanda / referencia',f"{summary['down_usage']:.1f}%")
    st.write(f"Subida que necesitan tus equipos: **{summary['up']:g} Mbps**.")
    if upload is not None:
        st.write(f"Subida de referencia: **{upload:g} Mbps** · demanda / referencia: **{summary['up_usage']:.1f}%**.")
    else:
        st.write('Subida de referencia: todavía desconocida.')
    if model_wifi:
        for band in BANDS[:2]:
            data=summary['bands'][band]
            st.write(f"**{band}:** {data['down']:g} de descarga + {data['up']:g} de subida / {data['capacity']:g} Mbps supuestos → **{data['usage']:.1f}%**.")
        st.caption('Las bandas comparten internet. Su cálculo local suma descarga y subida como simplificación. Cable no utiliza estas capacidades Wi-Fi; equipos sin banda conocida no se asignan a ninguna.')
    st.caption('Menos de 80%: verde. Desde 80% hasta 100%: amarillo. Más de 100%: rojo. El 80% es un margen educativo; no un estándar técnico. Una barra llena puede representar más de 100%.')

st.subheader('5 · ¿Qué podemos probar en familia?')
st.write('Activa una idea y mira cómo cambia el resultado. Aquí solo hacemos una prueba: no apagamos ni cambiamos tus equipos.')
left,right=st.columns(2)
with left:
    with st.container(border=True):
        st.markdown('#### ⏸️ Las descargas pueden esperar')
        st.write('Dejar un juego o archivo grande para cuando nadie esté en clases o viendo series.')
        pause=st.checkbox('Probar dejar las descargas para después',key='pause')
        if not any(r['activity']==ACTIVITIES[5] and r['count'] for r in rows):
            st.caption('En tu ejemplo no hay descargas grandes: esta idea no cambiará el resultado.')
with right:
    with st.container(border=True):
        st.markdown('#### 📺 Disfrutar la película en HD')
        st.write('Cambiar los videos de 4K a HD para que pidan menos internet.')
        lower=st.checkbox('Probar videos en HD en vez de 4K',key='lower')
        if not any(r['activity']==ACTIVITIES[3] and r['count'] for r in rows):
            st.caption('En tu ejemplo no hay videos 4K: esta idea no cambiará el resultado.')
move=False
if model_wifi:
    with st.container(border=True):
        st.markdown('#### 📶 Repartir los equipos entre las dos bandas')
        st.write('Probar cómo quedaría la red si los equipos de 2,4 GHz pasaran a 5 GHz.')
        move=st.checkbox('Probar el cambio a 5 GHz',key='move')
        st.caption('Solo funcionaría con equipos compatibles y buena señal. Aquí se mueve todo el grupo; para mover solo algunos, cambia su banda en el formulario de arriba. Más lejos del router, 5 GHz puede rendir peor.')
new_rows=improve(rows,pause,lower)
if move:
    for row in new_rows:
        if row.get('band')==BANDS[0]:
            row['band']=BANDS[1]
new=network_summary(new_rows,capacity,upload,band_caps)
if pause or lower or move:
    new_items=checks(new,known,model_wifi)
    changed=(new['down']!=summary['down'] or new['up']!=summary['up'] or any(before['usage']!=after['usage'] for before,after in zip(items,new_items)))
    st.markdown('### ✨ ¿Qué cambia con estas ideas?')
    if not active:
        st.info('Primero agrega equipos para probar estas ideas en tu casa.')
    elif not changed:
        st.info('Todo queda igual: las ideas elegidas no afectan las actividades que agregaste.')
    else:
        if not known and summary['up_usage'] is None:
            st.write('Tus actividades piden menos datos, pero falta conocer tu velocidad para saber si alcanza. Puedes medirla arriba.')
        for before,after in zip(items,new_items):
            if before['usage']!=after['usage']:
                bi,bl=STATES[before['state']]
                ai,al=STATES[after['state']]
                with st.container(border=True):
                    st.markdown(f"**{before['title']}**")
                    first,second=st.columns(2)
                    first.write(f'Antes: {bi} **{bl}**')
                    second.write(f'Con tus cambios: {ai} **{al}**')
                    if after['usage'] < before['usage']:
                        st.write('Ahora queda más espacio para compartir la conexión.')
                    else:
                        st.write('Esta parte recibe más demanda. Revisa si todavía tiene margen.')
        _,new_headline,new_explanation=verdict(new_items,active,incomplete_bands)
        st.markdown(f'**{new_headline}**')
        st.write(new_explanation)
    if move:
        st.caption('Cambiar de banda reparte el uso del Wi-Fi; no reduce lo que toda la casa pide a internet. Mover equipos puede llenar la banda de destino.')
    with st.expander('Ver la comparación en números'):
        st.metric('Demanda de descarga con estos cambios',f"{new['down']:g} Mbps",delta=f"{new['down']-summary['down']:g} Mbps",delta_color='inverse')
        st.dataframe(pd.DataFrame({'Parte de la conexión':[i['title'] for i in items], 'Antes (%)':[i['usage'] for i in items], 'Con los cambios (%)':[i['usage'] for i in new_items]}),hide_index=True)

if summary['up_usage'] is not None and summary['up_usage']>=80:
    st.info('📷 Una idea para tus cámaras: revisa si envían video todo el día o solo cuando detectan movimiento. Evita respaldar archivos al mismo tiempo. Reducir calidad también puede reducir el detalle de la grabación.')
with st.expander('🛋️ ¿Y si igual anda lento? Hagamos tres pruebas fáciles'):
    st.markdown('**1. Acércate al router y repite el test.** Si mejora, vale la pena revisar la señal, las paredes o las interferencias. Deja el router en un lugar central y despejado.')
    st.markdown('**2. Compara con cable, si puedes.** Así puedes revisar si cambia el resultado al dejar de usar Wi-Fi. En juegos también influyen el tiempo de respuesta y los cortes; este cálculo no los descarta.')
    st.markdown('**3. Guarda los resultados para consultar a tu compañía.** Si sigue lento por cable y sin otras descargas, repite la prueba a distintas horas. No necesitas decidir cambiar de plan solo por este simulador.')

with st.expander('Para la asignatura · Matrices, bandas y funciones'):
    st.write('A organiza tipos de equipo (filas) y actividades (columnas). Dos vectores b representan descarga y subida; A · b calcula demanda por equipo. Las submatrices A₂,₄ y A₅ agrupan solo los equipos de cada banda.')
    st.dataframe(pd.DataFrame(summary['matrix'],index=DEVICES,columns=ACTIVITIES))
    st.dataframe(pd.DataFrame({'Actividad':ACTIVITIES,'b descarga (Mbps)':RATES,'b subida (Mbps)':UPLOAD_RATES}),hide_index=True)
    st.latex(r'D=\sum_i(A b_d)_i,\quad T=\sum_i(A b_s)_i,\quad U_d=100D/B_d,\quad U_s=100T/B_s')
    st.latex(r'U_k=100\frac{\sum_i[A_k(b_d+b_s)]_i}{C_k},\qquad S(n)=100\frac{n c}{C}')
    st.caption('S(n) es el caso simplificado de n equipos con consumo idéntico c. Para 10 × 10 Mbps: 125% con C=80 y 33,3% con C=300. No significa que 2,4 y 5 GHz siempre tengan esas capacidades.')
    for band in BANDS[:2]:
        st.write(f'**Matriz de {band}**')
        st.dataframe(pd.DataFrame(summary['bands'][band]['matrix'],index=DEVICES,columns=ACTIVITIES))
    st.write(f"Descarga D = {summary['down']:g} Mbps; U = {summary['down_usage']:g}%. Subida T = {summary['up']:g} Mbps.")
    x=np.linspace(0,max(capacity*1.2,summary['down']*1.1),100)
    fig=px.line(x=x,y=x/capacity*100,labels={'x':'Demanda de descarga (Mbps)','y':'Utilización de referencia (%)'})
    fig.add_hline(y=100,line_dash='dash')
    fig.add_scatter(x=[summary['down']],y=[summary['down_usage']],mode='markers',name='Tu casa')
    st.plotly_chart(fig,width='stretch')
    st.caption('Ejemplo original: selecciona “Ejemplo de la asignatura”, descarga personalizada de 20 Mbps y desmarca usar medición. Entrega 14,5 Mbps y 72,5%.')
with st.expander('Supuestos y privacidad'):
    st.write('Consumos ilustrativos por equipo activo, no estándares ni mediciones: navegación 0,5/0,1; HD 5/0,1; llamada 1,5/1,5; 4K 25/0,1; juego 3/0,5; descarga 50/0,5; cámara nube 0,1/2; IoT en espera 0,02/0,02; música 0,3/0,05; respaldo nube 0,5/10; conectado sin uso 0,01/0,01 Mbps (descarga/subida).')
    st.write('Las descargas pueden ocupar la capacidad disponible real. Las cámaras y respaldos usan principalmente subida. El modelo no incluye tráfico solo local, interferencia real, ancho de canal, retransmisiones ni pérdida de paquetes. Las capacidades Wi-Fi y sus factores de señal son hipótesis editables.')
    st.write('El test intercambia datos aleatorios con Cloudflare y requiere internet; puede consumir hasta 45 MB. Es una prueba breve secuencial, no una certificación de velocidad máxima. El escenario de tu casa no se envía a Cloudflare. Los resultados se conservan en la sesión de SmartNet.')
report=pd.DataFrame(rows,columns=['device','activity','count','band'])
if not report.empty:
    report['Descarga estimada Mbps']=[r['count']*RATES[ACTIVITIES.index(r['activity'])] for r in rows]
    report['Subida estimada Mbps']=[r['count']*UPLOAD_RATES[ACTIVITIES.index(r['activity'])] for r in rows]
st.download_button('Descargar mi escenario',report.to_csv(index=False).encode('utf-8-sig'),'smartnet.csv','text/csv')
st.caption('SmartNet · Funciones y Matrices · Analista Programador · INACAP')
