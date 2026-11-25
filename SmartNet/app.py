from math import isclose
from pathlib import Path

import pandas as pd
import streamlit as st
from household import (ACTIVITIES, DEVICES, PRESETS, BANDS,
                       SIGNALS, network_summary, improve, suggest_bands)
from report_image import simulation_png
from speed_test import render_speed_test, valid_result
from results import STATES, checks, state, verdict

st.set_page_config(page_title='SmartNet · Internet en casa', page_icon='📶', layout='wide')
styles = Path(__file__).with_name('styles.css').read_text(encoding='utf-8')
st.markdown(f'<style>{styles}</style>', unsafe_allow_html=True)
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

def show_usage_comparison(before, after):
    # Give each pair one scale and leave room beyond 100% to show overload.
    scale = max(100.0, before or 0, after or 0) * 1.06
    previous = 'faltan datos' if before is None else f'{before:.1f}%'
    current = 'faltan datos' if after is None else f'{after:.1f}%'
    bars = []
    for label, value, text in [('Antes', before, previous), ('Con la propuesta', after, current)]:
        track = ''
        if value is not None:
            track = (
                f'<span class="smartnet-bar-track" aria-hidden="true">'
                f'<span class="smartnet-bar-fill {state(value)}" style="width:{value / scale * 100:.2f}%"></span>'
                f'<span class="smartnet-bar-limit" style="left:{100 / scale * 100:.2f}%"></span></span>'
            )
        bars.append(
            f'<div><div class="smartnet-bar-label"><span>{label}</span><strong>{text}</strong></div>{track}</div>'
        )
    st.markdown(
        f'<div class="smartnet-bars" role="img" aria-label="Antes: {previous} · Con la propuesta: {current}">'
        f'{"".join(bars)}</div>',
        unsafe_allow_html=True,
    )


def comparison_values(initial, final, known, compare_wifi):
    unknown_initial = bool(initial['bands'][BANDS[3]]['matrix'].sum())
    unknown_final = bool(final['bands'][BANDS[3]]['matrix'].sum())
    result = []
    for before, after in zip(checks(initial, known, compare_wifi), checks(final, known, compare_wifi)):
        part = before['key']
        is_band = part in BANDS[:2]
        title = {'download': 'Descarga del plan', 'upload': 'Subida del plan'}.get(part, part)
        before_usage = None if is_band and unknown_initial else before['usage']
        after_usage = None if is_band and unknown_final else after['usage']
        result.append((title, before_usage, after_usage))
    return result


def wifi_usage(report):
    if report['bands'][BANDS[3]]['matrix'].sum():
        return {}
    return {band: report['bands'][band]['usage'] for band in BANDS[:2]}


def recommend_wifi_step(rows, current, capacity, upload, caps, pause, lower, move):
    usage = wifi_usage(current)
    if not usage or max(usage.values()) <= 100:
        return

    def rank(load):
        return sum(value > 100 for value in load.values()), max(load.values())

    alternatives = [
        ('Deja la descarga para después', True, lower, move, not pause),
        ('Cambia los videos de 4K a HD', pause, True, move, not lower),
        ('Prueba cambiar equipos de banda', pause, lower, True, not move),
    ]
    best = rank(usage)
    recommendation = None
    for action, try_pause, try_hd, try_move, available in alternatives:
        if not available:
            continue
        candidate = improve(rows, try_pause, try_hd)
        if try_move:
            candidate = suggest_bands(candidate)
        result = wifi_usage(network_summary(candidate, capacity, upload, caps))
        if result and rank(result) < best:
            best = rank(result)
            recommendation = action, result

    if recommendation:
        action, result = recommendation
        gains = [
            f"{band} bajaría de {usage[band]:.1f}% a {result[band]:.1f}%"
            for band in BANDS[:2] if result[band] < usage[band] and not isclose(result[band], usage[band])
        ]
        increases = [
            f"{band} subiría de {usage[band]:.1f}% a {result[band]:.1f}%"
            for band in BANDS[:2] if result[band] > usage[band] and not isclose(result[band], usage[band])
        ]
        remaining = [band for band in BANDS[:2] if result[band] > 100]
        takeaway = (
            f" Aún faltaría capacidad en {' y '.join(remaining)}." if remaining
            else ' Las dos bandas quedarían con capacidad para las actividades simuladas.'
        )
        effects = ' y '.join(gains + increases)
        st.info(f"**Siguiente paso. {action}.** {effects}.{takeaway}")


PRESENTATION_PAGES = (
    ('connection', '¿Con qué velocidad cuenta la casa?'),
    ('equipment', '¿Qué equipos usan la conexión?'),
    ('result', '¿Qué mejorarías en esta casa?'),
)


def set_presentation_step(step):
    st.session_state.presentation_step = step


if 'rows' not in st.session_state:
    st.session_state.preset = 'Una tarde en casa'
    load_preset()

with st.container(key='hero'):
    st.title('SmartNet · ¿Alcanza tu internet para todos?')
    st.write('Descubre qué parte de la conexión se queda corta y prueba cómo darle más espacio.')
    st.markdown(
        '<div class="smartnet-route" role="img" aria-label="Internet se comunica con el router, que se comunica con los equipos">'
        '<span>Internet</span> ⇄ <span>Router</span> ⇄ <span>Equipos de casa</span></div>',
        unsafe_allow_html=True,
    )

presentation_step = min(st.session_state.get('presentation_step', 0), len(PRESENTATION_PAGES) - 1)
page_key, question = PRESENTATION_PAGES[presentation_step]
hidden_pages = ', '.join(f'.st-key-page_{key}' for key, _ in PRESENTATION_PAGES if key != page_key)
st.markdown(f'<style>{hidden_pages} {{display: none !important;}}</style>', unsafe_allow_html=True)
with st.container(border=True, key='presentation_nav'):
    st.progress((presentation_step + 1) / len(PRESENTATION_PAGES),
                text=f'Pantalla {presentation_step + 1} de {len(PRESENTATION_PAGES)}')
    st.subheader(question)
    back, forward = st.columns(2)
    back.button('← Atrás', key='presentation_back', disabled=presentation_step == 0,
                on_click=set_presentation_step, args=(max(0, presentation_step - 1),))
    if presentation_step < len(PRESENTATION_PAGES) - 1:
        next_label = 'Ver resultado →' if page_key == 'equipment' else 'Siguiente →'
        forward.button(next_label, key='presentation_next', type='primary',
                       on_click=set_presentation_step, args=(presentation_step + 1,))
    else:
        forward.button('Volver a la primera pregunta', key='presentation_restart',
                       on_click=set_presentation_step, args=(0,))

with st.container(key='presentation_frame'):
    with st.container(key='page_connection'):
        classroom_demo = st.session_state.preset in CLASSROOM_UPLOADS
        with st.container(border=True):
            st.markdown('#### 📶 Test de velocidad')
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
                if not classroom_demo:
                    st.button('Usar esta medición en mi simulación', on_click=apply_measurement, key='apply_speed')
                if len(st.session_state.speed_history) > 1:
                    st.dataframe(pd.DataFrame(st.session_state.speed_history)[['timestamp','lugar','download','upload','latency']].rename(columns={'download':'Descarga Mbps','upload':'Subida Mbps','latency':'Respuesta HTTP ms'}), hide_index=True)
            st.caption('Mide la conexión de este navegador mediante Cloudflare y guarda el resultado durante la sesión.')

        if classroom_demo:
            # Keep the manual widget values while the demonstration hides those controls.
            for key in ('plan', 'trial_capacity', 'custom_capacity', 'use_test',
                        'measured', 'know_upload', 'upload_capacity'):
                if key in st.session_state:
                    st.session_state[key] = st.session_state[key]
            capacity = 300.0
            upload = CLASSROOM_UPLOADS[st.session_state.preset]
            known = True
            st.write(f"Plan del ejemplo: **{capacity:g} Mbps de descarga** y **{upload:g} Mbps de subida**.")
        else:
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


    with st.container(key='page_equipment'):
        st.selectbox('Prueba un ejemplo o arma tu casa', list(SCENARIOS), key='preset', on_change=load_preset)
        with st.container(key=f'scenario_{st.session_state.row_revision}'):
            custom_scenario = st.session_state.preset == 'Empezar desde cero'
            if classroom_demo:
                st.write('Dos cámaras, una videollamada y tres tablets comparten 2,4 GHz. '
                         'En 5 GHz, un televisor reproduce una serie en 4K mientras un notebook descarga un juego.')
            if not custom_scenario:
                equipment = sum(row['count'] for row in current_rows())
                st.caption(f'Equipos en este escenario: {equipment}.')
            st.caption('Agrupa los equipos que hacen lo mismo y usan la misma conexión.')
            rows = []
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
                if classroom_demo:
                    st.caption('El ejemplo parte con 20 Mbps en 2,4 GHz y 70 Mbps en 5 GHz según la señal supuesta.')
                st.caption('Estas referencias son editables. Los equipos que usan 5 GHz suelen rendir mejor cerca del router.')
                for col, (band, default) in zip(st.columns(2), default_band_caps.items()):
                    with col:
                        nominal = st.number_input(f'Capacidad supuesta {band} (Mbps)', min_value=0.1,
                                                  value=default, key=f'{wifi_key_prefix}wifi_capacity_{band}')
                        signal_index = CLASSROOM_SIGNAL_OPTIONS[band] if classroom_demo else 0
                        signal = st.selectbox(f'Escenario de señal {band}', list(SIGNALS), index=signal_index,
                                              key=f'{wifi_key_prefix}signal_{band}')
                        band_caps[band] = nominal * SIGNALS[signal]


    with st.container(key='page_result'):
        summary = network_summary(rows, capacity, upload, band_caps)
        items = checks(summary, known, model_wifi)
        incomplete_bands = bool(model_wifi and summary['bands'][BANDS[3]]['matrix'].sum())
        active = bool(summary['matrix'].sum())
        _, headline, explanation = verdict(items, active, incomplete_bands)

        with st.container(border=True, key='slide_context'):
            st.markdown(f"**{st.session_state.preset}**")
            total_equipment = sum(row['count'] for row in rows)
            download_note = 'descarga' if known else 'descarga hipotética'
            upload_note = f'{upload:g} Mbps de subida' if upload is not None else 'subida por confirmar'
            st.caption(f'{total_equipment} equipos · {capacity:g} Mbps de {download_note} · {upload_note}')
        st.subheader('Resultado de la simulación')
        with st.container(border=True, key='family_summary'):
            st.markdown(f'### {headline}')
            if (all(item['state'] in ('good', 'tight') for item in items[:2])
                    and any(item['state'] == 'over' for item in items[2:])):
                st.write('El plan alcanza para enviar y recibir los datos. En este ejemplo, el problema está '
                         'en el Wi-Fi entre el router y los equipos.')
            else:
                st.write(explanation)

            if active:
                result_labels = {'download': 'Descarga', 'upload': 'Subida'}
                statuses = []
                for item in items:
                    icon, label = STATES[item['state']]
                    part = result_labels.get(item['key'], item['key'])
                    statuses.append(f'{icon} **{part}** · {label}')
                st.caption('  |  '.join(statuses))

        baseline = improved = summary
        changes = []
        with st.container(border=True, key='improvements'):
            st.subheader('Prueba una mejora')
            st.write('Prueba una acción y fíjate en qué parte queda con más espacio. Puedes combinar varias.')

            downloads, video, wifi = st.columns(3)
            with downloads.container(border=True, key='action_pause'):
                st.markdown('#### 🎮 Deja la descarga para después')
                st.write('Si se corta una clase o serie, prueba pausar la descarga del juego o archivo.')
                pause = st.checkbox('Probar dejar las descargas para después', key='pause')
            with video.container(border=True, key='action_hd'):
                st.markdown('#### 📺 Cambia de 4K a HD')
                st.write('Si varias personas ven videos al mismo tiempo, prueba bajar la calidad de los que están en 4K.')
                lower = st.checkbox('Probar videos en HD en vez de 4K', key='lower')
            with wifi.container(border=True, key='action_bands'):
                st.markdown('#### 📶 Reparte los equipos entre bandas')
                st.write('Prueba otra distribución entre 2,4 GHz y 5 GHz. Puede aliviar una banda y cargar la otra.')
                can_suggest = any(row['count'] and row['band'] != BANDS[2] for row in rows)
                band_proposal = can_suggest and st.session_state.get('show_band_proposal', False)
                button_label = 'Retirar cambio de bandas' if band_proposal else 'Probar cambio de bandas'
                if st.button(button_label, key='try_bands', disabled=not can_suggest):
                    st.session_state.show_band_proposal = not band_proposal
                    st.rerun()

            compare_wifi = model_wifi or band_proposal
            preview_caps = band_caps or default_band_caps
            if classroom_demo and not model_wifi:
                preview_caps = {
                    band: nominal * list(SIGNALS.values())[CLASSROOM_SIGNAL_OPTIONS[band]]
                    for band, nominal in CLASSROOM_WIFI_CAPS.items()
                }

            if not (pause or lower or band_proposal):
                if model_wifi:
                    recommend_wifi_step(rows, summary, capacity, upload, preview_caps, pause, lower, band_proposal)
                elif items[0]['state'] == 'over' and any(
                    row['count'] and row['activity'] == ACTIVITIES[5] for row in rows
                ):
                    st.info('Si la descarga del plan se queda corta, prueba dejar las descargas grandes para después.')

            if pause or lower or band_proposal:
                activity_changes = improve(rows, pause, lower)
                proposed = activity_changes
                if band_proposal:
                    proposed = suggest_bands(proposed)
                    changes = [
                        (i, before['device'], before['band'], after['band'])
                        for i, (before, after) in enumerate(zip(rows, proposed), start=1)
                        if after['count'] and before['band'] != after['band']
                    ]

                baseline = network_summary(rows, capacity, upload, preview_caps) if compare_wifi and not model_wifi else summary
                improved = network_summary(proposed, capacity, upload, preview_caps if compare_wifi else {})
                if band_proposal and changes:
                    with st.container(border=True, key='final_explanation'):
                        st.markdown('#### Qué pasaría al mover los equipos')
                        for i, device, old_band, new_band in changes:
                            st.write(f'Grupo {i} · {device}: {old_band} → {new_band}')
                        st.caption('En casa, revisa que cada equipo admita la banda y tenga buena señal en su ubicación.')
                    without_move = wifi_usage(network_summary(activity_changes, capacity, upload, preview_caps))
                    with_move = wifi_usage(improved)
                    if without_move and with_move:
                        shifts = [
                            f"**{band}** {'baja' if with_move[band] < without_move[band] else 'sube'} "
                            f"de **{without_move[band]:.1f}%** a **{with_move[band]:.1f}%**"
                            for band in BANDS[:2] if not isclose(without_move[band], with_move[band])
                        ]
                        if shifts:
                            st.write(f"Al cambiar de banda, {' y '.join(shifts)}. "
                                     'Los equipos llevan su tráfico a la banda de destino.')
                    elif with_move:
                        st.caption('Para comparar el efecto del cambio, asigna las bandas originales de tus equipos.')
                elif band_proposal:
                    st.info('Los grupos activos ya están en las bandas sugeridas.')
                if [row for row in proposed if row['count']] == [row for row in rows if row['count']]:
                    st.info('Todo queda igual: las ideas elegidas no afectan las actividades que agregaste.')
                else:
                    st.markdown('#### Antes y después')
                    st.caption('La marca vertical indica el 100%. Pasar esa marca significa que falta capacidad.')
                    if not isclose(summary['down'], improved['down']):
                        st.metric('Demanda de descarga con estos cambios', f"{improved['down']:g} Mbps",
                                  delta=f"{improved['down'] - summary['down']:g} Mbps", delta_color='inverse')

                    if compare_wifi:
                        if improved['bands'][BANDS[3]]['matrix'].sum():
                            st.caption('Completa las bandas de los equipos para saber si el Wi-Fi alcanzaría.')
                        elif any(improved['bands'][band]['usage'] > 100 for band in BANDS[:2]):
                            st.warning('El Wi-Fi todavía se queda corto en al menos una banda.')
                        else:
                            st.success('Con estos cambios, las dos bandas tienen capacidad para las actividades simuladas.')
                        recommend_wifi_step(rows, improved, capacity, upload, preview_caps, pause, lower, band_proposal)

                    comparisons = comparison_values(baseline, improved, known, compare_wifi)
                    for i, (title, before_usage, after_usage) in enumerate(comparisons):
                        if i % 2 == 0:
                            st.markdown('##### Plan de internet' if i == 0 else '##### Wi-Fi de la casa')
                            result_cols = st.columns(2)
                        with result_cols[i % 2].container(border=True):
                            st.markdown(f'**{title}**')
                            show_usage_comparison(before_usage, after_usage)
                            if after_usage is not None:
                                icon, label = STATES[state(after_usage)]
                                st.markdown(f'**{icon} {label}**')
                            if before_usage is not None and after_usage is not None:
                                if isclose(before_usage, after_usage):
                                    st.caption('La carga queda igual.')
                                elif after_usage < before_usage:
                                    st.caption('La carga baja.')
                                else:
                                    st.caption('La carga sube.')

        if active:
            with st.expander('Ver detalle del resultado'):
                for index, item in enumerate(items):
                    if index == 0:
                        st.markdown('#### Plan de internet · De internet al router y viceversa')
                        cols = st.columns(2)
                    elif index == 2:
                        st.markdown('#### Wi-Fi de la casa · Entre el router y los equipos')
                        st.write('El router reparte los datos por 2,4 GHz y 5 GHz. Los equipos que usan la misma banda '
                                 'comparten su capacidad para enviar y recibir datos.')
                        cols = st.columns(2)
                    icon, label = STATES[item['state']]
                    with cols[index % 2]:
                        with st.container(border=True, key=f"family_card_{index}_{item['state']}"):
                            st.markdown(f"#### {item['title']}")
                            st.markdown(f'**{icon} {label}**')
                            if item['key'] == 'download' and known:
                                st.write(f"Los equipos necesitan recibir **{summary['down']:g} Mbps**. "
                                         f"La referencia de descarga es **{capacity:g} Mbps**.")
                            elif item['key'] == 'upload':
                                if upload is None:
                                    st.write(f"Tus equipos necesitan **{summary['up']:g} Mbps de subida**.")
                                    st.caption('En la primera pantalla, marca «Conozco mi velocidad de subida» '
                                               'e ingresa el valor, o usa el test de velocidad.')
                                else:
                                    reference = 'del ejemplo' if classroom_demo else 'de referencia'
                                    st.write(f"Necesitas **{summary['up']:g} Mbps** de los **{upload:g} Mbps** de subida "
                                             f"{reference} (**{summary['up_usage']:.1f}%**).")
                            elif item['key'] in BANDS[:2]:
                                band = summary['bands'][item['key']]
                                st.write(f"Los equipos de esta banda necesitan mover **{band['traffic']:g} Mbps** "
                                         f"entre lo que envían y reciben. Con la señal del ejemplo, "
                                         f"esta banda puede mover **{band['capacity']:g} Mbps**.")
                            if item['state'] in ('tight', 'over'):
                                st.caption(item['tip'])
                if incomplete_bands:
                    st.caption('Asigna las bandas pendientes para completar la comparación Wi-Fi.')

        with st.expander('🔢 Quiero ver los números'):
            st.caption('El 100% significa que se necesita toda la capacidad. Si el uso estimado supera el 100%, '
                       'las actividades juntas necesitan más capacidad de la que hay.')
            st.markdown('#### Plan de internet')
            a, b, c = st.columns(3)
            a.metric('Descarga que necesitan los equipos', f"{summary['down']:g} Mbps")
            b.metric('Velocidad de descarga de referencia', f'{capacity:g} Mbps')
            c.metric('Uso estimado de descarga', f"{summary['down_usage']:.1f}%")
            if known:
                st.caption('Descarga es lo que llega de internet a tu casa, como una serie o un juego.')
            else:
                st.caption('La descarga de referencia es hipotética. Sirve para probar el escenario.')
            st.write(f"**Subida.** Tus equipos necesitan enviar **{summary['up']:g} Mbps** a internet, "
                     "por ejemplo para videollamadas o cámaras.")
            if upload is not None:
                label = 'Subida del ejemplo' if classroom_demo else 'Subida de referencia'
                st.write(f"{label}: **{upload:g} Mbps** · uso estimado: **{summary['up_usage']:.1f}%**.")
            else:
                st.write('Subida de referencia: pendiente. Falta ese dato para saber si alcanza.')
            if model_wifi:
                st.markdown('#### Wi-Fi de la casa')
                st.caption('Cada banda comparte su capacidad entre los equipos que la usan. '
                           'Aquí se suma lo que esos equipos envían y reciben por Wi-Fi.')
                for band in BANDS[:2]:
                    data = summary['bands'][band]
                    st.write(f"**{band}.** Los equipos necesitan **{data['traffic']:g} Mbps** y la banda tiene "
                             f"**{data['capacity']:g} Mbps** en la simulación. "
                             f"Eso equivale al **{data['usage']:.1f}%** de su capacidad.")

        if page_key == 'result':
            with st.container(border=True, key='final_download'):
                st.subheader('Guarda tu simulación')
                st.caption('Descarga una imagen con el escenario, las acciones probadas y el antes y después.')
                actions = [
                    label for selected, label in (
                        (pause, 'Dejar las descargas para después'),
                        (lower, 'Cambiar de 4K a HD'),
                        (band_proposal, 'Repartir los equipos entre bandas'),
                    ) if selected
                ]
                report_changes = [
                    f'Grupo {i} · {device.split(" ", 1)[1]}: {old_band} a {new_band}'
                    for i, device, old_band, new_band in changes
                ]
                connection = f'{capacity:g} Mbps de {download_note} · {upload_note}'
                image = simulation_png(st.session_state.preset, total_equipment, connection, actions,
                                       comparison_values(baseline, improved, known, compare_wifi), report_changes)
                st.download_button('Descargar resumen como imagen', image, 'smartnet-resumen.png',
                                   'image/png', type='primary', on_click='ignore')

with st.container(border=True, key='bottom_nav'):
    back, forward = st.columns(2)
    back.button('← Volver a la pantalla anterior', key='bottom_back', disabled=presentation_step == 0,
                on_click=set_presentation_step, args=(max(0, presentation_step - 1),))
    if presentation_step < len(PRESENTATION_PAGES) - 1:
        label = 'Siguiente pantalla →' if page_key == 'connection' else 'Siguiente · Ver resultado →'
        forward.button(label, key='bottom_next', type='primary',
                       on_click=set_presentation_step, args=(presentation_step + 1,))
    else:
        forward.button('Volver al inicio', key='bottom_restart', on_click=set_presentation_step, args=(0,))

st.caption('SmartNet · Funciones y Matrices · Analista Programador · INACAP')
