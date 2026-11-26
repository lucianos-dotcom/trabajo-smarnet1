from functools import partial
from importlib import reload
from math import isclose
from pathlib import Path

import pandas as pd
import streamlit as st
import household

# Streamlit Cloud may keep the previous catalog loaded after updating the app.
if not hasattr(household, 'CLASSROOM_RATES'):
    reload(household)
from household import (ACTIVITIES, DEVICES, PRESETS, BANDS, SHORT_VIDEO_ACTIVITY,
                       CLASSROOM_RATES, CLASSROOM_UPLOAD_RATES,
                       network_summary, improve, suggest_bands)
from report_image import simulation_png
from speed_test import render_speed_test, valid_result
from results import STATES, checks, state, verdict

st.set_page_config(page_title='SmartNet · Internet en casa', page_icon='📶', layout='wide')
styles = Path(__file__).with_name('styles.css').read_text(encoding='utf-8')
st.markdown(f'<style>{styles}</style>', unsafe_allow_html=True)
st.session_state.setdefault('row_revision', 0)
DEFAULT_WIFI_CAPS = dict(zip(BANDS[:2], (80.0, 300.0)))
CLASSROOM_SPEED = 100.0
CLASSROOM_PRESET = f'Casa de {CLASSROOM_SPEED:g} Mbps · Caso de clase'
CLASSROOM_GROUPS = [(4, 6, 7), (0, 11, 2), (2, 1, 4), (6, 3, 3)]
CLASSROOM_BANDS = [BANDS[0], BANDS[0], BANDS[1], BANDS[1]]
# Streamlit can retain the previous household module across a code update.
SCENARIOS = {
    name: groups for name, groups in PRESETS.items()
    if name not in ('Ejemplo de la asignatura', 'Demostración de clase: ambas bandas saturadas',
                    'Casa con Wi-Fi saturado')
}
SOCIAL_PRESET = 'Solo uso el celular para redes sociales'
SOCIAL_MESSAGES = 'Redes sociales, WhatsApp y navegación'
ACTIVITY_OPTIONS = [ACTIVITIES[0], SHORT_VIDEO_ACTIVITY] + [
    activity for activity in ACTIVITIES[1:] if activity != SHORT_VIDEO_ACTIVITY
]
SCENARIOS = {CLASSROOM_PRESET: CLASSROOM_GROUPS, SOCIAL_PRESET: [(0, 0, 1)], **SCENARIOS}
CLASSROOM_WIFI_CAPS = dict(zip(BANDS[:2], (40.0, 100.0)))

def activity_label(activity, classroom_demo):
    label = SOCIAL_MESSAGES if activity == ACTIVITIES[0] else activity
    if classroom_demo:
        return f'{label} · {CLASSROOM_RATES[ACTIVITIES.index(activity)]:g} Mbps por equipo'
    return label

def row_key(field, i):
    return f'{field}_{st.session_state.row_revision}_{i}'

def replace_rows(rows):
    # Reused positions must start with the new rows' values in the browser.
    st.session_state.rows = rows
    st.session_state.row_revision += 1

def load_preset():
    st.session_state.show_band_proposal = False
    st.session_state.pause = False
    st.session_state.lower = False
    st.session_state.still_slow = False
    preset = st.session_state.preset
    groups = SCENARIOS[preset]
    bands = CLASSROOM_BANDS if preset == CLASSROOM_PRESET else [BANDS[3]] * len(groups)
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


def comparison_values(initial, final, known, compare_wifi, labels):
    unknown_initial = bool(initial['bands'][BANDS[3]]['matrix'].sum())
    unknown_final = bool(final['bands'][BANDS[3]]['matrix'].sum())
    result = []
    for before, after in zip(checks(initial, known, compare_wifi), checks(final, known, compare_wifi)):
        part = before['key']
        is_band = part in BANDS[:2]
        title = labels.get(part, part)
        before_usage = None if is_band and unknown_initial else before['usage']
        after_usage = None if is_band and unknown_final else after['usage']
        result.append((title, before_usage, after_usage))
    return result


def wifi_usage(report):
    if report['bands'][BANDS[3]]['matrix'].sum():
        return {}
    return {band: report['bands'][band]['usage'] for band in BANDS[:2]}


def recommend_wifi_step(rows, current, summarize, caps, pause, lower, move):
    overloaded = [band for band in BANDS[:2] if (current['bands'][band]['usage'] or 0) > 100]
    if not overloaded:
        return None, None

    if len(overloaded) == 2:
        practical = 'Conecta por cable un equipo fijo si puedes y reparte las actividades más pesadas en distintos horarios.'
    elif overloaded[0] == BANDS[0]:
        practical = 'Si hay poca señal, acerca el equipo al router. Si admite 5 GHz, prueba esa banda cuando tenga espacio.'
    else:
        practical = 'Si el equipo está lejos o detrás de paredes, acércalo al router. Para un equipo fijo, prueba un cable de red.'

    usage = wifi_usage(current)
    if not usage:
        return None, practical

    def rank(load):
        return sum(value > 100 for value in load.values()), max(load.values())

    alternatives = [
        ('pause', 'Deja la descarga para después', True, lower, move, not pause),
        ('hd', 'Cambia los videos de 4K a HD', pause, True, move, not lower),
        ('bands', 'Prueba cambiar equipos de banda', pause, lower, True, not move),
    ]
    best = rank(usage)
    recommendation = None
    for action_key, action, try_pause, try_hd, try_move, available in alternatives:
        if not available:
            continue
        candidate = improve(rows, try_pause, try_hd)
        if try_move:
            candidate = suggest_bands(candidate)
        result = wifi_usage(summarize(candidate, band_capacities=caps))
        if result and rank(result) < best:
            best = rank(result)
            recommendation = action_key, action, result

    if recommendation:
        action_key, action, result = recommendation
        if any(value > 100 for value in result.values()):
            return action_key, f'{action}. Aliviaría el Wi-Fi y todavía quedaría una banda por revisar.'
        return action_key, f'{action}. Con esa acción, las bandas tendrían capacidad para las actividades elegidas.'
    return None, practical


def show_result_bars(items, incomplete_bands, labels):
    readings = [
        (labels.get(item['key'], item['key']),
         None if incomplete_bands and item['key'] in BANDS[:2] else item['usage'])
        for item in items
    ]
    scale = max(100.0, *(value or 0 for _, value in readings)) * 1.06
    bars = []
    for label, value in readings:
        reading = 'Faltan datos' if value is None else f'{value:.1f}%'.replace('.', ',')
        _, status = STATES[state(value)]
        description = reading if value is None else f'{reading}, {status}'
        bars.append(
            f'<div class="smartnet-result-bar" role="img" aria-label="{label}: {description}">'
            f'<div class="smartnet-bar-label"><strong>{label}</strong><span>{reading}</span></div>'
            f'{usage_bar(value, scale)}</div>'
        )
    st.markdown(f'<div class="smartnet-result-bars">{"".join(bars)}</div>', unsafe_allow_html=True)
    if any(value is not None for _, value in readings):
        st.caption('Uso estimado. Si la barra pasa la marca del 100%, falta capacidad.')


def changed_readings(comparisons, baseline, improved):
    result = []
    for index, (title, before, after) in enumerate(comparisons):
        unit = '%'
        if index < 2 and before is None and after is None:
            key = ('down', 'up')[index]
            before, after, unit = baseline[key], improved[key], ' Mbps'
        if before != after and (before is None or after is None or not isclose(before, after)):
            result.append((title, before, after, unit))
    return result


def detail_value(value, unit):
    if value is None:
        return '—'
    text = f'{value:.1f}' if unit == '%' else f'{value:g}'
    return text.replace('.', ',') + unit


def show_connection_steps(plan_limits, wifi_limited, social_only):
    with st.container(border=True, key='connection_steps'):
        st.markdown('#### Qué hacer si anda lento' if not plan_limits else '#### Qué hacer si falta capacidad')
        if not plan_limits and not wifi_limited and social_only:
            st.markdown('1. **Prueba otra app en el mismo lugar.** Si solo falla una, revisa esa app o prueba de nuevo más tarde.')
            st.markdown('2. **Compara la señal.** Repite el test donde notas lentitud y luego cerca del router. '
                        'Si mejora al acercarte, prueba usar el celular donde la señal llegue mejor.')
        else:
            st.markdown('1. **Compara la señal.** Repite el test donde notas lentitud y luego cerca del router. Usa cable si tienes un equipo compatible.')
            if wifi_limited:
                st.markdown('2. **Si mejora cerca del router, revisa la cobertura.** Acerca el equipo o conecta por cable los equipos fijos que puedas.')
            elif plan_limits:
                st.markdown('2. **Reduce el uso simultáneo.** Deja las descargas o respaldos grandes para otro momento y vuelve a probar.')
        st.markdown('**Cuándo llamar a tu compañía.** Si la lentitud sigue en varias apps cerca del router o por cable, comparte los resultados con soporte.')
        if plan_limits:
            directions = ' y '.join(plan_limits)
            st.markdown(f'**Cuándo evaluar otro plan.** Si recibes la velocidad contratada y en tu uso habitual '
                        f'todavía falta {directions}, consulta por un plan con más capacidad en ese sentido.')
        st.button('Volver al test de velocidad', key='support_back_to_test',
                  on_click=set_presentation_step, args=(0,))


PRESENTATION_PAGES = (
    ('connection', '¿Con qué velocidad cuenta la casa?'),
    ('equipment', '¿Qué equipos usan la conexión?'),
    ('result', '¿Qué mejorarías en esta casa?'),
)


def set_presentation_step(step):
    st.session_state.presentation_step = step


if 'rows' not in st.session_state or st.session_state.get('preset') not in SCENARIOS:
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
if page_key != 'connection':
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
        classroom_demo = st.session_state.preset == CLASSROOM_PRESET
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
                capacity, upload, known = CLASSROOM_SPEED, None, True
                reference_source = 'Plan y consumos del ejemplo de clase'
                st.write(f"Capacidad del plan del ejemplo: **{capacity:g} Mbps**.")
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
                st.write('Siete cámaras, dos celulares, cuatro Smart TV y tres TV Box.')
            if st.session_state.preset == SOCIAL_PRESET:
                st.caption('El celular ya está agregado. Si ves Reels o TikTok, elige «Videos cortos en redes» como actividad.')
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
                    activity = b.selectbox(f'Actividad {i+1}', ACTIVITY_OPTIONS, index=ACTIVITY_OPTIONS.index(row['activity']), key=row_key('activity', i),
                                           format_func=lambda value: activity_label(value, classroom_demo))
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
        summarize = partial(network_summary, download=capacity, upload=upload)
        if classroom_demo:
            summarize = partial(summarize, download_rates=CLASSROOM_RATES, upload_rates=CLASSROOM_UPLOAD_RATES)
        summary = summarize(rows, band_capacities=band_caps)
        items = checks(summary, known, model_wifi)
        incomplete_bands = bool(model_wifi and summary['bands'][BANDS[3]]['matrix'].sum())
        active = bool(summary['matrix'].sum())
        _, headline, explanation = verdict(items, active, incomplete_bands)

        total_equipment = sum(row['count'] for row in rows)
        download_note = 'descarga' if known else 'descarga hipotética'
        upload_note = f'{upload:g} Mbps de subida' if upload is not None else 'subida por confirmar'
        parts = {'download': 'el plan de internet' if classroom_demo else 'descarga del plan', 'upload': 'subida del plan'}
        labels = {'download': 'Uso del plan' if classroom_demo else 'Descarga del plan', 'upload': 'Subida del plan'}
        connection = (f'{capacity:g} Mbps de capacidad' if classroom_demo
                      else f'{capacity:g} Mbps de {download_note} · {upload_note}')
        overdemand = [parts.get(item['key'], item['key']) for item in items if item['state'] == 'over']
        active_rows = [row for row in rows if row['count']]
        social_only = active and all(
            row['device'] == DEVICES[0] and row['activity'] in (ACTIVITIES[0], SHORT_VIDEO_ACTIVITY)
            for row in active_rows
        )

        st.subheader('Resultado de la prueba')
        with st.container(border=True, key='family_summary'):
            diagnosis, illustration = st.columns([2, 1], vertical_alignment='center')
            with diagnosis:
                if active and all(item['state'] == 'unknown' for item in items):
                    st.markdown('### 🏠 Falta una referencia de velocidad')
                    if social_only:
                        st.write('Haz el test para saber si tu velocidad alcanza para el uso de redes que elegiste.')
                    else:
                        st.write('Haz el test o ingresa los datos de tu plan para saber si alcanza.')
                elif social_only and known and not overdemand:
                    usage = ('ver videos cortos' if any(row['activity'] == SHORT_VIDEO_ACTIVITY for row in active_rows)
                             else 'leer mensajes y revisar publicaciones')
                    if upload is None:
                        st.markdown('### La descarga alcanza para tus redes')
                        st.write(f'Hay capacidad para {usage}. Falta conocer la subida para evaluar el envío de contenido.')
                    else:
                        st.markdown('### La velocidad alcanza para tus redes')
                        st.write(f'Hay capacidad para {usage} según la referencia que estás usando.')
                elif classroom_demo and items[0]['state'] == 'over':
                    st.markdown('### El plan de internet se queda corto')
                    st.write(f"La casa necesita **{summary['down']:g} Mbps** y el plan ofrece **{capacity:g} Mbps**.")
                elif any(item['state'] == 'over' for item in items[2:]) and all(
                    item['state'] in ('good', 'tight') for item in items[:2]
                ):
                    st.markdown('### El Wi-Fi se queda corto')
                    st.write('El plan alcanza para enviar y recibir los datos.')
                else:
                    st.markdown(f'### {headline}')
                    st.write(explanation)
                if active and not all(item['state'] == 'unknown' for item in items):
                    readings = [item for item in items if not classroom_demo or item['key'] != 'upload']
                    show_result_bars(readings, incomplete_bands, labels)
                if overdemand:
                    st.caption('Necesitan atención: ' + ' · '.join(overdemand))

            with illustration.container(key='result_art'):
                st.image(str(Path(__file__).with_name('assets') / 'result-router.webp'), width='stretch')

        with st.container(border=True, key='improvements'):
            has_download = any(row['activity'] == ACTIVITIES[5] for row in active_rows)
            has_4k = any(row['activity'] == ACTIVITIES[3] for row in active_rows)
            wireless = [row for row in active_rows if row['band'] != BANDS[2]]
            can_suggest = bool(wireless) and (len(wireless) > 1 or model_wifi) and suggest_bands(wireless) != wireless
            actions_available = [
                key for key, available in (('pause', has_download), ('hd', has_4k), ('bands', can_suggest))
                if available
            ]
            st.subheader('Prueba una mejora' if actions_available else 'Qué hacer ahora')
            still_slow = active and st.checkbox('Igual me anda lento', key='still_slow')
            recommendation_slot = st.empty()
            pause = lower = False
            band_proposal = can_suggest and st.session_state.get('show_band_proposal', False)
            for col, option in zip(st.columns(len(actions_available)) if actions_available else [], actions_available):
                with col.container(key=f'option_{option}'):
                    if option == 'pause':
                        pause = st.checkbox('Dejar las descargas para después', key='pause')
                    elif option == 'hd':
                        lower = st.checkbox('Cambiar de 4K a HD', key='lower')
                    else:
                        button_label = 'Retirar cambio de bandas' if band_proposal else 'Probar cambio de bandas'
                        if st.button(button_label, key='try_bands'):
                            st.session_state.show_band_proposal = not band_proposal
                            st.rerun()

            testing = pause or lower or band_proposal
            compare_wifi = model_wifi or band_proposal
            preview_caps = default_band_caps if compare_wifi else {}
            baseline = summarize(rows, band_capacities=preview_caps) if compare_wifi and not model_wifi else summary
            proposed = improve(rows, pause, lower) if testing else rows
            if band_proposal:
                proposed = suggest_bands(proposed)
            changes = [
                (i, before['device'], before['band'], after['band'])
                for i, (before, after) in enumerate(zip(rows, proposed), start=1)
                if after['count'] and before['band'] != after['band']
            ]
            improved = summarize(proposed, band_capacities=preview_caps) if testing else baseline
            changed = [row for row in proposed if row['count']] != [row for row in rows if row['count']]
            comparisons = comparison_values(baseline, improved, known, compare_wifi, labels)
            plan_limits = [
                direction for direction, usage in (
                    ('capacidad del plan' if classroom_demo else 'descarga',
                     improved['down_usage'] if known else None),
                    ('subida', improved['up_usage'])
                ) if usage is not None and usage > 100
            ]
            wifi_limited = any((improved['bands'][band]['usage'] or 0) > 100 for band in BANDS[:2])
            changes_to_chart = changed_readings(comparisons, baseline, improved) if changed else []
            focus_wifi = band_proposal or any(item['state'] == 'over' for item in items[2:])
            visible_charts = sorted(changes_to_chart, key=lambda row: (row[0] in BANDS[:2]) != focus_wifi)[:2]
            if testing:
                if not changed:
                    st.info('Esta opción no cambia las actividades ni las bandas de tu escenario.')
                else:
                    remaining = [
                        parts.get(item['key'], item['key'])
                        for item in checks(improved, known, compare_wifi) if item['state'] == 'over'
                    ]
                    if classroom_demo and remaining == [parts['download']]:
                        st.warning('El plan de internet queda justo para este uso. '
                                   f"Los equipos necesitan {improved['down']:g} Mbps y el plan ofrece {capacity:g} Mbps.")
                    elif remaining:
                        st.warning(f"Todavía falta capacidad en {' y '.join(remaining)}.")
                    elif compare_wifi and wifi_usage(improved):
                        st.success('El Wi-Fi alcanza con estos cambios.')
                    elif any(improved[key] < baseline[key] and not isclose(improved[key], baseline[key])
                             for key in ('down', 'up')):
                        st.success('Los equipos necesitan mover menos datos.')
                    else:
                        st.info('La propuesta cambia cómo se reparte el tráfico entre las bandas.')
                    if visible_charts:
                        st.markdown('#### Antes y después')
                        if any(unit == '%' for _, _, _, unit in visible_charts):
                            st.caption('La marca del 100% indica el límite de capacidad.')
                        for col, (title, before, after, unit) in zip(st.columns(len(visible_charts)), visible_charts):
                            with col:
                                st.markdown(f'**{title}**')
                                show_change_chart(before, after, unit)
                                show_change_status(before, after, unit)

            recommended, advice = recommend_wifi_step(
                rows, improved, summarize, preview_caps, pause, lower, band_proposal,
            )
            if not advice and not testing and items[0]['state'] == 'over' and has_download:
                recommended, advice = 'pause', 'Deja las descargas grandes para después.'
            elif not advice and classroom_demo and improved['down_usage'] > 100 and has_4k and not lower:
                recommended, advice = 'hd', 'Cambia los TV Box de 4K a HD para reducir la demanda del plan.'
            elif not advice and (improved['up_usage'] or 0) > 100:
                advice = 'Deja los respaldos de archivos para después y revisa los equipos que están enviando datos.'
            with recommendation_slot.container():
                if advice:
                    st.markdown(f'**Qué probar.** {advice}')
                elif not actions_available and not still_slow and not plan_limits:
                    if not active:
                        st.caption('Agrega un equipo en la pantalla anterior para obtener una recomendación.')
                    elif not known:
                        st.caption('Mide tu conexión para que SmartNet pueda recomendar un cambio.')
                    elif overdemand:
                        st.caption('Prueba reducir los equipos en uso al mismo tiempo o repite el test cerca del router.')
                    else:
                        st.caption('Para el uso que elegiste, no hace falta cambiar nada ahora.')
                if recommended in actions_available:
                    st.markdown(
                        f'<style>.st-key-option_{recommended} {{background: rgba(13, 148, 136, .10);'
                        'border-left: 3px solid #0d9488; border-radius: 8px; padding: .45rem .65rem;}</style>',
                        unsafe_allow_html=True,
                    )

            if still_slow or plan_limits:
                show_connection_steps(plan_limits, wifi_limited, social_only)

        with st.expander('Detalle y números'):
            with st.container(key='result_details'):
                st.markdown(f"**{st.session_state.preset}**")
                source = reference_source if known else 'Descarga hipotética'
                st.caption(f'{total_equipment} equipos · {source}.')

                details = [('Plan' if classroom_demo else 'Descarga', summary['down'], capacity, summary['down_usage'])]
                if not classroom_demo:
                    details.append(('Subida', summary['up'], upload, summary['up_usage']))
                if model_wifi:
                    for band in BANDS[:2]:
                        data = summary['bands'][band]
                        details.append((band, data['traffic'], data['capacity'],
                                        None if incomplete_bands else data['usage']))
                table = pd.DataFrame(
                    [(name, detail_value(demand, ' Mbps'), detail_value(limit, ' Mbps'), detail_value(usage, '%'))
                     for name, demand, limit, usage in details],
                    columns=['Conexión', 'Demanda', 'Capacidad', 'Uso'],
                ).set_index('Conexión')
                st.table(table, border='horizontal')
                notes = []
                if model_wifi:
                    notes.append('Las capacidades de Wi-Fi son estimadas. El plan se comparte entre las bandas.')
                if incomplete_bands:
                    notes.append('El uso de Wi-Fi queda pendiente hasta asignar todas las bandas.')
                if not classroom_demo and upload is None:
                    notes.append('La capacidad de subida está por confirmar.')
                if notes:
                    st.caption(' '.join(notes))

                improvement_lines = []
                demand_changed = changed and not isclose(baseline['down'], improved['down'])
                if demand_changed:
                    demand_label = 'Demanda total' if classroom_demo else 'Demanda de descarga'
                    improvement_lines.append(f'**{demand_label}** · {detail_value(baseline["down"], " Mbps")} '
                                             f'→ **{detail_value(improved["down"], " Mbps")}**')
                for reading in changes_to_chart:
                    title, before, after, unit = reading
                    if reading not in visible_charts and not (demand_changed and title == labels['download'] and unit == ' Mbps'):
                        improvement_lines.append(f'**{title}** · {detail_value(before, unit)} → **{detail_value(after, unit)}**')
                for i, device, old_band, new_band in changes:
                    improvement_lines.append(f'Grupo {i} · {device} · {old_band} → {new_band}')
                if improvement_lines:
                    st.markdown('**Con la mejora**\n\n' + '\n'.join(f'- {line}' for line in improvement_lines))

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
            report_comparisons = [row for row in comparisons if not classroom_demo or row[0] != labels['upload']]
            image = simulation_png(st.session_state.preset, total_equipment, connection, actions,
                                   report_comparisons, report_changes)
            st.download_button('Descargar resumen como imagen', image, 'smartnet-resumen.png',
                               'image/png', on_click='ignore')

with st.container(border=True, key='bottom_nav'):
    back, forward = st.columns(2)
    back.button('← Volver a la pantalla anterior', key='bottom_back', disabled=presentation_step == 0,
                on_click=set_presentation_step, args=(max(0, presentation_step - 1),))
    if presentation_step < len(PRESENTATION_PAGES) - 1:
        label = 'Siguiente pantalla →' if page_key == 'connection' else 'Siguiente · Ver resultado →'
        forward.button(label, key='bottom_next',
                       on_click=set_presentation_step, args=(presentation_step + 1,))
    else:
        forward.button('Volver al inicio', key='bottom_restart', on_click=set_presentation_step, args=(0,))

st.caption('SmartNet · Funciones y Matrices · Analista Programador · INACAP')
