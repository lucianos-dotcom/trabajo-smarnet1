from math import isclose
from pathlib import Path

import pandas as pd
import streamlit as st
from household import (ACTIVITIES, DEVICES, PRESETS, BANDS,
                       network_summary, improve, suggest_bands)
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
CLASSROOM_WIFI_CAPS = dict(zip(BANDS[:2], (20.0, 70.0)))

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

def show_speed_result(result):
    download, upload = result['download'], result['upload']
    scale = max(download, upload)
    speeds = []
    rows = []
    for direction, value, detail in (
        ('Descarga', download, 'Recibir datos, como al ver un video.'),
        ('Subida', upload, 'Enviar datos, como al compartir un archivo.'),
    ):
        speed = (f'{value:.1f}' if value >= 0.1 else f'{value:.3g}').replace('.', ',')
        speeds.append(f'{direction}: {speed} Mbps')
        rows.append(
            f'<div><div class="smartnet-bar-label"><strong>{direction}</strong>'
            f'<strong>{speed} Mbps</strong></div><div class="smartnet-speed-detail">{detail}</div>'
            f'<span class="smartnet-bar-track" aria-hidden="true"><span class="smartnet-bar-fill '
            f'{direction.lower()}" style="width:{value / scale * 100:.2f}%"></span></span></div>'
        )

    st.markdown('##### Tu última medición')
    st.markdown(
        f'<div class="smartnet-bars smartnet-speed-bars" role="img" aria-label="{" · ".join(speeds)}">'
        f'{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )
    st.caption('Las barras usan la misma escala. Una barra más larga significa más datos por segundo.')
    st.markdown(f"**Tiempo de respuesta: {result['latency']:.0f} ms**")
    st.caption('Es la demora en recibir una respuesta del servidor de la prueba. Cuanto menor, más rápida la respuesta.')


def usage_bar(value, scale):
    if value is None:
        return ''
    return (
        '<span class="smartnet-bar-track" aria-hidden="true">'
        f'<span class="smartnet-bar-fill {state(value)}" style="width:{value / scale * 100:.2f}%"></span>'
        f'<span class="smartnet-bar-limit" style="left:{100 / scale * 100:.2f}%"></span></span>'
    )


def show_change_chart(before, after, unit='%'):
    capacity_chart = unit == '%'
    scale = max(100.0 if capacity_chart else 1.0, before or 0, after or 0) * 1.06
    bars = []
    values = []
    for label, value in (('Antes', before), ('Con la propuesta', after)):
        text = 'faltan datos' if value is None else f'{value:.1f}{unit}'
        values.append(text)
        if capacity_chart:
            track = usage_bar(value, scale)
        else:
            track = (
                '<span class="smartnet-bar-track" aria-hidden="true">'
                f'<span class="smartnet-bar-fill comparison-demand" style="width:{value / scale * 100:.2f}%"></span>'
                '</span>'
            )
        reading = text.replace('.', ',')
        bars.append(
            f'<div class="smartnet-change-reading"><span>{label}</span>'
            f'<strong>{reading}</strong>{track}</div>'
        )

    previous, current = values
    st.markdown(
        f'<div class="smartnet-change-chart" role="img" '
        f'aria-label="Antes: {previous} · Con la propuesta: {current}">'
        f'{bars[0]}<span class="smartnet-change-arrow" aria-hidden="true">→</span>{bars[1]}</div>',
        unsafe_allow_html=True,
    )


def show_change_status(before, after, unit):
    status = 'comparison-neutral'
    if before is None:
        label = 'Ya se puede estimar la carga' if after is not None else 'Faltan datos para comparar'
    elif after is None:
        label = 'Faltan datos para comparar'
    elif unit != '%':
        label = 'Baja la demanda estimada'
        status = 'comparison-better'
    elif after > 100:
        label = 'Sigue saturada' if before > 100 else 'Se satura con este cambio'
        status = 'comparison-worse'
    elif before > 100:
        label = 'Sale de la saturación'
        status = 'comparison-better'
    elif not isclose(before, after):
        label = 'Gana espacio' if after < before else 'Recibe más carga'
        status = 'comparison-better' if after < before else 'comparison-warning'
    else:
        label = 'Queda igual'

    st.markdown(f'<span class="smartnet-change-tag {status}">{label}</span>', unsafe_allow_html=True)


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
    overloaded = [band for band in BANDS[:2] if (current['bands'][band]['usage'] or 0) > 100]
    if not overloaded:
        return

    if len(overloaded) == 2:
        practical = 'Conecta por cable un equipo fijo si puedes y reparte las actividades más pesadas en distintos horarios.'
    elif overloaded[0] == BANDS[0]:
        practical = 'Si hay poca señal, acerca el equipo al router. Si admite 5 GHz, prueba esa banda cuando tenga espacio.'
    else:
        practical = 'Si el equipo está lejos o detrás de paredes, acércalo al router. Para un equipo fijo, prueba un cable de red.'

    usage = wifi_usage(current)
    if not usage:
        return practical

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
        if any(value > 100 for value in result.values()):
            return f'{action}. Aliviaría el Wi-Fi y todavía quedaría una banda por revisar.'
        return f'{action}. Con esa acción, las bandas tendrían capacidad para las actividades elegidas.'
    return practical


def show_result_status(label, items, incomplete=False):
    states = {item['state'] for item in items}
    if 'over' in states:
        result, tone = 'Se queda corto', 'comparison-worse'
    elif 'tight' in states:
        result, tone = 'Poco margen', 'comparison-warning'
    elif incomplete or 'unknown' in states:
        result, tone = 'Faltan datos', 'comparison-neutral'
    else:
        result, tone = 'Tiene margen', 'comparison-better'
    st.markdown(
        f'<div class="smartnet-result-row"><strong>{label}</strong>'
        f'<span class="smartnet-change-tag {tone}">{result}</span></div>',
        unsafe_allow_html=True,
    )


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

presentation_step = min(st.session_state.get('presentation_step', 0), len(PRESENTATION_PAGES) - 1)
page_key, question = PRESENTATION_PAGES[presentation_step]
with st.container(key='hero'):
    st.title('SmartNet · ¿Alcanza tu internet para todos?')
    st.write('Descubre qué parte de la conexión se queda corta y prueba cómo darle más espacio.')
    st.markdown(
        '<div class="smartnet-route" role="img" aria-label="Internet se comunica con el router, que se comunica con los equipos">'
        '<span>Internet</span> ⇄ <span>Router</span> ⇄ <span>Equipos de casa</span></div>',
        unsafe_allow_html=True,
    )

hidden_pages = ', '.join(f'.st-key-page_{key}' for key, _ in PRESENTATION_PAGES if key != page_key)
if page_key == 'result':
    hidden_pages += ', .st-key-hero'
st.markdown(f'<style>{hidden_pages} {{display: none !important;}}</style>', unsafe_allow_html=True)
with st.container(border=True, key='presentation_nav'):
    st.progress((presentation_step + 1) / len(PRESENTATION_PAGES),
                text=f'Pantalla {presentation_step + 1} de {len(PRESENTATION_PAGES)}')
    if page_key == 'result':
        st.markdown('**SmartNet**')
    else:
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
            speed_overview = st.container(key='speed_overview')
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
                with speed_overview:
                    show_speed_result(result)
                if result['latency'] >= 150:
                    st.info('La respuesta HTTP fue alta en esta prueba. Puede influir en actividades interactivas; repite cerca del router o con cable. No permite atribuir el problema al Wi-Fi por sí sola.')
                with st.expander('Detalles de la medición'):
                    st.caption(f"Fecha UTC: {result['timestamp']}. Variación entre respuestas HTTP: "
                               f"{result['jitter']:.0f} ms. La prueba mide tiempos de respuesta HTTP.")
                    if len(st.session_state.speed_history) > 1:
                        st.dataframe(pd.DataFrame(st.session_state.speed_history)[
                            ['timestamp', 'lugar', 'download', 'upload', 'latency']
                        ].rename(columns={
                            'download': 'Descarga Mbps', 'upload': 'Subida Mbps', 'latency': 'Respuesta HTTP ms',
                        }), hide_index=True)
            st.caption('Mide la conexión de este navegador mediante Cloudflare y guarda el resultado durante la sesión.')

        manual_reference = False
        manual_keys = ('plan', 'trial_capacity', 'custom_capacity', 'know_upload', 'upload_capacity')
        if classroom_demo:
            manual_keys += ('manual_reference',)
        else:
            manual_reference = st.toggle('Usar datos de mi plan o ingresarlos a mano', key='manual_reference')
            if manual_reference:
                plan = st.selectbox('¿Cuántos megas tiene tu plan?', [
                    'No sé mi velocidad', 'Ingresar otra velocidad', '20 Mbps', '100 Mbps', '300 Mbps',
                    '500 Mbps', '600 Mbps', '800 Mbps', '940 Mbps', '1000 Mbps',
                ], index=4, key='plan')
                known = plan != 'No sé mi velocidad'
                if not known:
                    capacity = st.number_input('Velocidad hipotética para probar (Mbps)', min_value=0.1,
                                               value=100.0, key='trial_capacity')
                elif plan == 'Ingresar otra velocidad':
                    capacity = st.number_input('Descarga de referencia (Mbps)', min_value=0.1,
                                               value=20.0, key='custom_capacity')
                else:
                    capacity = float(plan.split()[0])
                know_upload = st.checkbox('Conozco mi velocidad de subida', key='know_upload')
                upload = st.number_input('Subida de referencia (Mbps)', min_value=0.001, value=20.0,
                                         format='%.2f', key='upload_capacity') if know_upload else None

        if not manual_reference:
            # Preserve entered values while the corresponding controls are hidden.
            for key in manual_keys:
                if key in st.session_state:
                    st.session_state[key] = st.session_state[key]
            measured = st.session_state.get('last_speed')
            if classroom_demo:
                capacity, upload, known = 300.0, CLASSROOM_UPLOADS[st.session_state.preset], True
                reference_source = 'Plan del ejemplo'
                st.write(f"Plan del ejemplo: **{capacity:g} Mbps de descarga** y **{upload:g} Mbps de subida**.")
            elif valid_result(measured):
                capacity, upload, known = float(measured['download']), float(measured['upload']), True
                reference_source = 'Medición del test de SmartNet'
                with speed_overview:
                    st.success('Esta medición se usa automáticamente en la prueba.')
            else:
                capacity, upload, known = 300.0, None, False
                reference_source = 'Descarga hipotética'
                st.caption('Si sigues sin medir, usaremos 300 Mbps de descarga como ejemplo. La subida quedará pendiente.')
        else:
            reference_source = 'Datos ingresados a mano'
            st.caption('Prueba con datos ingresados a mano.')

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
            with st.container(key='band_help'):
                with st.popover('? Banda'):
                    st.markdown('**Revisa el equipo o la lista de conectados de tu router.**')
                    st.write('**Windows.** Ve a Configuración → Red e Internet → Wi-Fi. Abre las propiedades '
                             'de la red conectada y busca «Banda de red».')
                    st.write('**Android.** Abre los detalles de tu red Wi-Fi. Si aparece la frecuencia, '
                             'un valor cercano a 2400 MHz indica 2,4 GHz y uno cercano a 5000 MHz indica 5 GHz.')
                    st.write('**iPhone u otros equipos.** Busca el dispositivo en la app o el panel del router. '
                             'Algunos modelos muestran si está en 2,4 GHz o 5 GHz.')
                    st.caption('Si el equipo está conectado por Ethernet, elige «Cable de red». '
                               'Si no puedes comprobar su banda, elige «No sé la banda».')
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
        model_wifi = any(row['count'] and row['band'] in BANDS[:2] for row in rows)
        band_caps = default_band_caps if model_wifi else {}

    with st.container(key='page_result'):
        summary = network_summary(rows, capacity, upload, band_caps)
        items = checks(summary, known, model_wifi)
        incomplete_bands = bool(model_wifi and summary['bands'][BANDS[3]]['matrix'].sum())
        active = bool(summary['matrix'].sum())
        _, headline, explanation = verdict(items, active, incomplete_bands)

        total_equipment = sum(row['count'] for row in rows)
        download_note = 'descarga' if known else 'descarga hipotética'
        upload_note = f'{upload:g} Mbps de subida' if upload is not None else 'subida por confirmar'
        parts = {'download': 'descarga del plan', 'upload': 'subida del plan'}
        overdemand = [parts.get(item['key'], item['key']) for item in items if item['state'] == 'over']

        st.subheader('Resultado de la prueba')
        with st.container(border=True, key='family_summary'):
            if active and all(item['state'] == 'unknown' for item in items):
                st.markdown('### 🏠 Falta una referencia de velocidad')
                st.write('Haz el test o ingresa los datos de tu plan para saber si alcanza.')
            elif any(item['state'] == 'over' for item in items[2:]) and all(
                item['state'] in ('good', 'tight') for item in items[:2]
            ):
                st.markdown('### El Wi-Fi se queda corto')
                st.write('El plan alcanza para enviar y recibir los datos.')
            else:
                st.markdown(f'### {headline}')
                st.write(explanation)
            if active and not all(item['state'] == 'unknown' for item in items):
                show_result_status('Plan de internet', items[:2])
                if model_wifi:
                    show_result_status('Wi-Fi de la casa', items[2:], incomplete_bands)
            if overdemand:
                st.caption('Necesitan atención: ' + ' · '.join(overdemand))

        with st.container(border=True, key='improvements'):
            st.subheader('Prueba una mejora')
            downloads, video, wifi = st.columns(3)
            pause = downloads.checkbox('Dejar las descargas para después', key='pause')
            lower = video.checkbox('Cambiar de 4K a HD', key='lower')
            can_suggest = any(row['count'] and row['band'] != BANDS[2] for row in rows)
            band_proposal = can_suggest and st.session_state.get('show_band_proposal', False)
            button_label = 'Retirar cambio de bandas' if band_proposal else 'Probar cambio de bandas'
            if wifi.button(button_label, key='try_bands', disabled=not can_suggest):
                st.session_state.show_band_proposal = not band_proposal
                st.rerun()

            testing = pause or lower or band_proposal
            compare_wifi = model_wifi or band_proposal
            preview_caps = default_band_caps if compare_wifi else {}
            baseline = network_summary(rows, capacity, upload, preview_caps) if compare_wifi and not model_wifi else summary
            proposed = improve(rows, pause, lower) if testing else rows
            if band_proposal:
                proposed = suggest_bands(proposed)
            changes = [
                (i, before['device'], before['band'], after['band'])
                for i, (before, after) in enumerate(zip(rows, proposed), start=1)
                if after['count'] and before['band'] != after['band']
            ]
            improved = network_summary(proposed, capacity, upload, preview_caps) if testing else baseline
            changed = [row for row in proposed if row['count']] != [row for row in rows if row['count']]
            comparisons = comparison_values(baseline, improved, known, compare_wifi)
            if testing:
                if not changed:
                    st.info('Esta opción no cambia las actividades ni las bandas de tu escenario.')
                else:
                    remaining = [
                        parts.get(item['key'], item['key'])
                        for item in checks(improved, known, compare_wifi) if item['state'] == 'over'
                    ]
                    if remaining:
                        st.warning(f"Todavía falta capacidad en {' y '.join(remaining)}.")
                    elif compare_wifi and wifi_usage(improved):
                        st.success('El Wi-Fi alcanza con estos cambios.')
                    elif any(improved[key] < baseline[key] and not isclose(improved[key], baseline[key])
                             for key in ('down', 'up')):
                        st.success('Los equipos necesitan mover menos datos.')
                    else:
                        st.info('La propuesta cambia cómo se reparte el tráfico entre las bandas.')

            advice = recommend_wifi_step(rows, improved, capacity, upload, preview_caps, pause, lower, band_proposal)
            if advice:
                st.caption(f'**Qué probar.** {advice}')
            elif not testing and items[0]['state'] == 'over' and any(
                row['count'] and row['activity'] == ACTIVITIES[5] for row in rows
            ):
                st.caption('**Qué probar.** Deja las descargas grandes para después.')
            elif (improved['up_usage'] or 0) > 100:
                st.caption('**Qué probar.** Deja los respaldos de archivos para después y revisa los equipos que están enviando datos.')

        with st.expander('Detalle y números'):
            with st.container(key='slide_context'):
                st.markdown(f"**{st.session_state.preset}**")
                st.caption(f'{total_equipment} equipos · {capacity:g} Mbps de {download_note} · {upload_note}')
                st.caption(f'Referencia: {reference_source}.')

            st.caption('Por encima del 100%, las actividades juntas necesitan más capacidad de la disponible.')
            st.markdown('#### Plan de internet')
            a, b, c = st.columns(3)
            a.metric('Descarga que necesitan los equipos', f"{summary['down']:g} Mbps")
            b.metric('Velocidad de descarga de referencia', f'{capacity:g} Mbps')
            c.metric('Uso estimado de descarga', f"{summary['down_usage']:.1f}%")
            if not known:
                st.caption('La descarga de referencia es hipotética. Sirve para probar el escenario.')
            st.write(f"**Subida.** Tus equipos necesitan enviar **{summary['up']:g} Mbps** a internet.")
            if upload is not None:
                label = 'Subida del ejemplo' if classroom_demo else 'Subida de referencia'
                st.write(f"{label}: **{upload:g} Mbps** · uso estimado: **{summary['up_usage']:.1f}%**.")
            else:
                st.write('Subida de referencia: pendiente. Falta ese dato para saber si alcanza.')
            if model_wifi:
                st.markdown('#### Wi-Fi de la casa')
                st.caption('Se suma lo que los equipos envían y reciben en cada banda. '
                           'Las capacidades de las bandas son valores de referencia.')
                for band in BANDS[:2]:
                    data = summary['bands'][band]
                    st.write(f"**{band}.** Los equipos necesitan **{data['traffic']:g} Mbps** y la banda tiene "
                             f"**{data['capacity']:g} Mbps** en este ejemplo. "
                             f"Eso equivale al **{data['usage']:.1f}%** de su capacidad.")

            if changed:
                st.markdown('#### Antes y después')
                st.caption('En los porcentajes, la marca vertical indica el límite del 100%.')
                if not isclose(baseline['down'], improved['down']):
                    st.metric('Demanda de descarga con estos cambios', f"{improved['down']:g} Mbps",
                              delta=f"{improved['down'] - baseline['down']:g} Mbps", delta_color='inverse')
                for index, (title, before, after) in enumerate(comparisons):
                    unit = '%'
                    if index < 2 and before is None and after is None:
                        key = ('down', 'up')[index]
                        before, after, unit = baseline[key], improved[key], ' Mbps'
                    if before == after or (before is not None and after is not None and isclose(before, after)):
                        continue
                    st.markdown(f'**{title}**')
                    show_change_chart(before, after, unit)
                    show_change_status(before, after, unit)

            if changes:
                st.markdown('#### Equipos que cambiarían de banda')
                for i, device, old_band, new_band in changes:
                    st.write(f'Grupo {i} · {device}: {old_band} → {new_band}')
                st.caption('Antes de mover un equipo, revisa que admita la banda y tenga buena señal.')

        if page_key == 'result':
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
                                   comparisons, report_changes)
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
