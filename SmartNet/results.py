"""Plain-language presentation of model results; never diagnoses a real network."""
from household import BANDS

STATES = {
    'unknown': ('⚪', 'Falta un dato'),
    'good': ('🟢', 'Hay espacio'),
    'tight': ('🟡', 'Está justito'),
    'over': ('🔴', 'No alcanza en este ejemplo'),
}

def state(usage):
    if usage is None:
        return 'unknown'
    return 'over' if usage > 100 else 'tight' if usage >= 80 else 'good'

def checks(summary, known, model_wifi):
    result = [
        dict(key='download', title='📺 Ver series y navegar',
             explanation='Lo que llega a tu casa: videos, páginas y descargas.',
             usage=summary['down_usage'] if known else None,
             tip='Prueba dejar las descargas grandes para más tarde.'),
        dict(key='upload', title='📷 Enviar videos y hacer llamadas',
             explanation='Lo que sale de tu casa: cámaras, videollamadas y respaldos.',
             usage=summary['up_usage'],
             tip='Revisa si tus cámaras y respaldos están enviando archivos al mismo tiempo.'),
    ]
    if model_wifi:
        for band in BANDS[:2]:
            result.append(dict(key=band, title=f'📶 Equipos en {band}',
                               explanation='Comparación con la capacidad Wi-Fi que supusiste.',
                               usage=summary['bands'][band]['usage'],
                               tip='Prueba repartir equipos compatibles entre bandas y revisa la señal.'))
    for item in result:
        item['state'] = state(item['usage'])
    return result

def verdict(items, active, incomplete_bands=False):
    if not active:
        return 'empty', '🏠 Tu casa está por armar', 'Agrega equipos en uso y te mostraremos cómo se reparten la conexión.'
    if any(i['state']=='over' for i in items):
        return 'over', '🏠 Algunas actividades podrían quedarse esperando', 'En este escenario hay más demanda que espacio disponible. Abajo puedes probar cómo aliviarla.'
    if any(i['state']=='tight' for i in items):
        return 'tight', '🏠 Tu conexión está quedando justita', 'Lo que agregaste deja poco margen. Una actividad más podría hacer que compitan por internet.'
    if incomplete_bands or any(i['state']=='unknown' for i in items):
        return 'unknown', '🏠 Vamos bien, pero falta una pista', 'Lo que pudimos calcular tiene margen. Completa los datos pendientes para revisar el resto.'
    return 'good', '🏠 Hay espacio para lo que está haciendo tu familia', 'La demanda que ingresaste cabe en las referencias elegidas. Si igual está lento, revisemos la señal y el lugar del router.'
