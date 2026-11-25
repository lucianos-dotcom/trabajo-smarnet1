import pandas as pd
import streamlit as st
from household import (ACTIVITIES, DEVICES, RATES, UPLOAD_RATES, PRESETS, BANDS,
                       SIGNALS, network_summary, improve, suggest_bands)
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
st.session_state.setdefault('row_revision', 0)
DEFAULT_WIFI_CAPS = dict(zip(BANDS[:2], (80.0, 300.0)))
CLASSROOM_UPLOADS = {
    'Wi-Fi saturado · Plan simétrico 300/300 Mbps': 300.0,
    'Wi-Fi saturado · Plan asimétrico 300/10 Mbps': 10.0,
}
CLASSROOM_GROUPS = [(4, 6, 2), (0, 2, 1), (5, 1, 3), (2, 3, 1), (1, 5, 1)]
# Streamlit can retain the previous household module across a code update.
SCENARIOS = {
    name: groups for name, groups in PRESETS.items()
    if name not in ('Ejemplo de la asignatura', 'Demostración de clase: ambas bandas saturadas',
                    'Casa con Wi-Fi saturado')
}
SCENARIOS.update(dict.fromkeys(CLASSROOM_UPLOADS, CLASSROOM_GROUPS))
CLASSROOM_WIFI_CAPS = dict(zip(BANDS[:2], (80.0, 140.0)))
CLASSROOM_SIGNAL_OPTIONS = dict(zip(BANDS[:2], (2, 1)))

def row_key(field, i):
    return f'{field}_{st.session_state.row_revision}_{i}'

def replace_rows(rows):
    # Reused positions must start with the new rows' values in the browser.
    st.session_state.rows = rows
    st.session_state.row_revision += 1

def load_preset():
    st.session_state.show_band_proposal = False
    preset = st.session_state.preset
    groups = SCENARIOS[preset]
    bands = [BANDS[3]] * len(groups)
    if preset in CLASSROOM_UPLOADS:
        bands = [BANDS[0], BANDS[0], BANDS[0], BANDS[1], BANDS[1]]
        st.session_state.classroom_wifi_revision = st.session_state.row_revision + 1
    replace_rows([
        dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n, band=band)
        for (d, a, n), band in zip(groups, bands, strict=True)
    ])

def choose_device(i):
    device = st.session_state[row_key('device', i)]
    activity = 6 if device == DEVICES[4] else 7 if device in [DEVICES[7], DEVICES[8], DEVICES[9], DEVICES[10]] else 0
    st.session_state[row_key('activity', i)] = ACTIVITIES[activity]

def current_rows():
    return [
        {field: st.session_state.get(row_key(field, i), value)
         for field, value in dict(row, band=row.get('band', BANDS[3])).items()}
        for i, row in enumerate(st.session_state.rows)
    ]

def remove_row(index):
    rows = current_rows()
    rows.pop(index)
    replace_rows(rows)

def apply_measurement():
    result = st.session_state.last_speed
    st.session_state.measured = float(result['download'])
    st.session_state.upload_capacity = float(result['upload'])
    st.session_state.use_test = True
    st.session_state.know_upload = True

if 'rows' not in st.session_state:
    st.session_state.preset = 'Una tarde en casa'
    load_preset()

st.title('SmartNet · ¿Alcanza tu internet para todos?')
st.write('Elige una velocidad, arma un escenario y revisa si la conexión alcanza para todos.')

st.subheader('1 · Conoce tu conexión')
classroom_demo = st.session_state.preset in CLASSROOM_UPLOADS
if classroom_demo:
    # Keep the manual widget values while the demonstration hides those controls.
    for key in ('test_location', 'plan', 'trial_capacity', 'custom_capacity', 'use_test',
                'measured', 'know_upload', 'upload_capacity'):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    capacity = 300.0
    upload = CLASSROOM_UPLOADS[st.session_state.preset]
    known = True
    st.write(f"Plan del ejemplo: **{capacity:g} Mbps de descarga** y **{upload:g} Mbps de subida**.")
else:
    with st.expander('📶 Hacer un test de velocidad aquí'):
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
        st.caption('Mide la conexión de este navegador mediante Cloudflare y guarda el resultado durante la sesión.')

    plan = st.selectbox('¿Cuántos megas tiene tu plan?', ['No sé mi velocidad', 'Ingresar otra velocidad', '20 Mbps', '100 Mbps', '300 Mbps', '500 Mbps', '600 Mbps', '800 Mbps', '940 Mbps', '1000 Mbps'], index=4, key='plan')
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
    know_upload = st.checkbox('Conozco mi velocidad de subida (o la obtuve en el test)', key='know_upload')
    upload = st.number_input('Subida de referencia (Mbps)', min_value=0.001, value=20.0, format='%.2f', key='upload_capacity') if know_upload else None

st.subheader('2 · Arma tu escenario')
st.selectbox('Prueba un ejemplo o arma tu casa', list(SCENARIOS), key='preset', on_change=load_preset)
if classroom_demo:
    st.write('En la tarde, dos cámaras del patio suben video, alguien está en una videollamada '
             'y tres tablets reproducen videos en HD lejos del router. En otra habitación, un Smart TV '
             'reproduce una serie en 4K y un notebook descarga un juego.')
    st.caption('El ejemplo parte con 20 Mbps de capacidad Wi-Fi en 2,4 GHz y 70 Mbps en 5 GHz. '
               'Son valores supuestos según la señal del escenario y se pueden editar en Ajustes de Wi-Fi.')
else:
    st.caption('Agrupa los equipos que hacen lo mismo y usan la misma conexión.')
rows=[]
for i,row in enumerate(st.session_state.rows):
    with st.container(border=True):
        a,b,c,d = st.columns([3,4,2,3])
        device = a.selectbox(f'Equipo {i+1}', DEVICES, index=DEVICES.index(row['device']), key=row_key('device', i), on_change=choose_device, args=(i,))
        activity = b.selectbox(f'Actividad {i+1}', ACTIVITIES, index=ACTIVITIES.index(row['activity']), key=row_key('activity', i))
        count = c.number_input(f'Cantidad {i+1}', min_value=0, max_value=100, value=row['count'], step=1, key=row_key('count', i))
        band = d.selectbox(f'Conexión del grupo {i+1}', BANDS, index=BANDS.index(row.get('band',BANDS[3])), key=row_key('band', i))
        st.button('Quitar este grupo', key=row_key('remove', i), on_click=remove_row, args=(i,))
        rows.append(dict(device=device, activity=activity, count=int(count), band=band))
st.session_state.rows=rows
if st.button('＋ Agregar otro equipo', key='add'):
    st.session_state.rows.append(dict(device=DEVICES[0], activity=ACTIVITIES[0], count=1, band=BANDS[3]))
    st.rerun()

default_band_caps = CLASSROOM_WIFI_CAPS if classroom_demo else DEFAULT_WIFI_CAPS
wifi_key_prefix = f'classroom_{st.session_state.classroom_wifi_revision}_' if classroom_demo else ''
with st.expander('Ajustes de Wi-Fi'):
    model_wifi = st.checkbox('Comparar las dos bandas con capacidades supuestas',
                             value=classroom_demo, key=f'{wifi_key_prefix}model_wifi')
    band_caps = {}
    if model_wifi:
        st.caption('Estas referencias son editables. Los equipos que usan 5 GHz suelen rendir mejor cerca del router.')
        for col, (band, default) in zip(st.columns(2), default_band_caps.items()):
            with col:
                nominal = st.number_input(f'Capacidad supuesta {band} (Mbps)', min_value=0.1,
                                          value=default, key=f'{wifi_key_prefix}wifi_capacity_{band}')
                signal_index = CLASSROOM_SIGNAL_OPTIONS[band] if classroom_demo else 0
                signal = st.selectbox(f'Escenario de señal {band}', list(SIGNALS), index=signal_index,
                                      key=f'{wifi_key_prefix}signal_{band}')
                band_caps[band] = nominal * SIGNALS[signal]

summary = network_summary(rows, capacity, upload, band_caps)
items = checks(summary, known, model_wifi)
incomplete_bands = bool(model_wifi and summary['bands'][BANDS[3]]['matrix'].sum())
active = bool(summary['matrix'].sum())
_, headline, explanation = verdict(items, active, incomplete_bands)

st.subheader('3 · Revisa el resultado')
with st.container(border=True, key='family_summary'):
    st.markdown(f'### {headline}')
    st.write(explanation)

if active:
    cols = st.columns(2)
    for index, item in enumerate(items):
        icon, label = STATES[item['state']]
        with cols[index % 2]:
            with st.container(border=True, key=f"family_card_{index}_{item['state']}"):
                st.markdown(f"#### {item['title']}")
                st.markdown(f'**{icon} {label}**')
                if item['key'] == 'upload':
                    if upload is None:
                        st.write(f"Tus equipos necesitan **{summary['up']:g} Mbps de subida**.")
                        st.caption('En Conoce tu conexión, marca «Conozco mi velocidad de subida» '
                                   'e ingresa el valor, o usa el test de velocidad.')
                    else:
                        reference = 'del ejemplo' if classroom_demo else 'de referencia'
                        st.write(f"Necesitas **{summary['up']:g} Mbps** de los **{upload:g} Mbps** de subida "
                                 f"{reference} (**{summary['up_usage']:.1f}%**).")
                if item['state'] in ('tight', 'over'):
                    st.caption(item['tip'])
    if incomplete_bands:
        st.caption('Asigna las bandas pendientes para completar la comparación Wi-Fi.')

with st.expander('🔢 Quiero ver los números'):
    a, b, c = st.columns(3)
    a.metric('Demanda de descarga', f"{summary['down']:g} Mbps")
    b.metric('Descarga de referencia', f'{capacity:g} Mbps')
    c.metric('Demanda / referencia', f"{summary['down_usage']:.1f}%")
    st.write(f"Subida que necesitan tus equipos: **{summary['up']:g} Mbps**.")
    if upload is not None:
        label = 'Subida del ejemplo' if classroom_demo else 'Subida de referencia'
        st.write(f"{label}: **{upload:g} Mbps** · uso estimado: **{summary['up_usage']:.1f}%**.")
    else:
        st.write('Subida de referencia: pendiente. Falta ese dato para saber si alcanza.')
    if model_wifi:
        for band in BANDS[:2]:
            data = summary['bands'][band]
            st.write(f"Ocupación estimada en {band}: **{data['usage']:.1f}%**.")

with st.expander('Prueba una mejora'):
    pause = st.checkbox('Probar dejar las descargas para después', key='pause')
    lower = st.checkbox('Probar videos en HD en vez de 4K', key='lower')
    if pause or lower:
        improved = network_summary(improve(rows, pause, lower), capacity, upload, band_caps)
        if improved['down'] == summary['down']:
            st.info('Todo queda igual: las ideas elegidas no afectan las actividades que agregaste.')
        else:
            st.metric('Demanda de descarga con estos cambios', f"{improved['down']:g} Mbps",
                      delta=f"{improved['down'] - summary['down']:g} Mbps", delta_color='inverse')

    can_suggest = any(row['count'] and row['band'] != BANDS[2] for row in rows)
    if st.button('Probar cambio de bandas', key='try_bands', disabled=not can_suggest):
        st.session_state.show_band_proposal = True
    if can_suggest and st.session_state.get('show_band_proposal'):
        proposed = suggest_bands(rows)
        changes = [
            f"Grupo {i} · {before['device']}: {before['band']} → {after['band']}"
            for i, (before, after) in enumerate(zip(rows, proposed), start=1)
            if before['count'] and before['band'] != after['band']
        ]
        st.markdown('#### Propuesta de bandas Wi-Fi')
        if changes:
            for change in changes:
                st.write(change)
        else:
            st.write('Los grupos activos ya están en las bandas sugeridas.')
        preview_caps = band_caps or default_band_caps
        if classroom_demo and not model_wifi:
            preview_caps = {
                band: nominal * list(SIGNALS.values())[CLASSROOM_SIGNAL_OPTIONS[band]]
                for band, nominal in CLASSROOM_WIFI_CAPS.items()
            }
        before = summary if model_wifi else network_summary(rows, capacity, upload, preview_caps)
        after = network_summary(proposed, capacity, upload, preview_caps)
        unknown_bands = before['bands'][BANDS[3]]['matrix'].sum() > 0
        for band in BANDS[:2]:
            previous = 'faltan datos' if unknown_bands else f"{before['bands'][band]['usage']:.1f}%"
            st.write(f"{band} · Antes: {previous} · Con la propuesta: {after['bands'][band]['usage']:.1f}%")
        st.caption('Simulación con capacidades supuestas. El cambio reparte la carga del Wi-Fi; '
                   'la demanda de internet se mantiene. Antes de probarlo en casa, revisa la señal y la compatibilidad.')

report=pd.DataFrame(rows,columns=['device','activity','count','band'])
if not report.empty:
    report['Descarga estimada Mbps']=[r['count']*RATES[ACTIVITIES.index(r['activity'])] for r in rows]
    report['Subida estimada Mbps']=[r['count']*UPLOAD_RATES[ACTIVITIES.index(r['activity'])] for r in rows]
st.download_button('Descargar mi escenario',report.to_csv(index=False).encode('utf-8-sig'),'smartnet.csv','text/csv')
st.caption('SmartNet · Funciones y Matrices · Analista Programador · INACAP')
