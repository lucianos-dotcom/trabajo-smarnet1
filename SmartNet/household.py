"""Referencias ilustrativas para escenarios domésticos; no mide la red."""
import numpy as np
from model import calculate

DEVICES = ['📱 Celular', '💻 Notebook o PC', '📺 Smart TV', '🎮 Consola', '📷 Cámara de seguridad', '📟 Tablet', '📺 TV Box / decodificador', '🔊 Parlante inteligente', '💡 Ampolleta o enchufe inteligente', '🖨️ Impresora Wi-Fi', '🤖 Aspiradora robot']
ACTIVITIES = ['WhatsApp y navegar', 'Ver videos o series en HD', 'Videollamada o clase online', 'Ver videos o series en 4K', 'Jugar online', 'Descargar juegos o archivos', 'Cámara transmitiendo a la nube', 'Dispositivo inteligente en espera', 'Escuchar música', 'Subir archivos o respaldo a la nube', 'Conectado sin uso']
RATES = np.array([0.5, 5, 1.5, 25, 3, 50, 0.1, 0.02, 0.3, 0.5, 0.01], dtype=float)
PRESETS = {
    'Una tarde en casa': [(0, 0, 2), (1, 2, 1), (2, 1, 1), (3, 4, 1)],
    'Todos viendo series': [(0, 1, 2), (2, 3, 2)],
    'Descargas y clases online': [(1, 2, 2), (3, 5, 2), (2, 1, 1)],
    'Ejemplo de la asignatura': [(0, 0, 2), (0, 2, 1), (1, 0, 1), (1, 2, 1), (2, 1, 2)],
    'Casa con cámaras y dispositivos inteligentes': [(4, 6, 4), (8, 7, 5), (6, 1, 1), (7, 8, 1)],
    'Empezar desde cero': [],
}

def make_matrix(rows):
    a = np.zeros((len(DEVICES), len(ACTIVITIES)), dtype=int)
    for row in rows:
        count = row['count']
        if not isinstance(count, int) or count < 0:
            raise ValueError('La cantidad debe ser un entero no negativo.')
        a[DEVICES.index(row['device']), ACTIVITIES.index(row['activity'])] += count
    return a

def evaluate(rows, capacity):
    matrix = make_matrix(rows)
    demand, total, usage, _ = calculate(matrix, capacity, RATES)
    level = 'Posible saturación' if usage > 100 else 'Al límite' if usage >= 80 else 'Con margen'
    return matrix, demand, total, usage, level

def improve(rows, pause_downloads, lower_quality):
    result = []
    for row in rows:
        row = row.copy()
        if pause_downloads and row['activity'] == ACTIVITIES[5]:
            row['count'] = 0
        if lower_quality and row['activity'] == ACTIVITIES[3]:
            row['activity'] = ACTIVITIES[1]
        result.append(row)
    return result

# Download / upload estimates per active device, in Mbps.
UPLOAD_RATES = np.array([0.1, 0.1, 1.5, 0.1, 0.5, 0.5, 2, 0.02, 0.05, 10, 0.01])
BANDS = ['2,4 GHz', '5 GHz', 'Cable de red', 'No sé la banda']
SIGNALS = {'Cerca y sin obstáculos (100%)': 1.0, 'Con paredes o distancia (50%)': 0.5, 'Lejos o con muchos obstáculos (25%)': 0.25}

def network_summary(rows, download, upload, band_capacities):
    """Separate shared Internet constraints from hypothetical local Wi-Fi capacity.

    Wi-Fi uses summed up/down traffic as a simplified shared-capacity approximation,
    not channel airtime or actual radio utilization. Unknown bands are never guessed.
    """
    if any(r.get('band', BANDS[3]) not in BANDS for r in rows):
        raise ValueError('Banda desconocida.')
    matrix = make_matrix(rows)
    _, down_total, down_usage, _ = calculate(matrix, download, RATES)
    up_total = float((matrix @ UPLOAD_RATES).sum())
    if upload is not None and (not np.isfinite(upload) or upload <= 0):
        raise ValueError('La capacidad de subida debe ser mayor que cero.')
    bands = {}
    for band in BANDS:
        subset = [r for r in rows if r.get('band', BANDS[3]) == band]
        a = make_matrix(subset)
        down = float((a @ RATES).sum())
        up = float((a @ UPLOAD_RATES).sum())
        capacity = band_capacities.get(band)
        if capacity is not None and (not np.isfinite(capacity) or capacity <= 0):
            raise ValueError('La capacidad Wi-Fi debe ser mayor que cero.')
        bands[band] = dict(matrix=a, down=down, up=up, traffic=down+up,
                           usage=(down+up)/capacity*100 if capacity is not None else None,
                           capacity=capacity)
    usages = [down_usage] + ([up_total/upload*100] if upload is not None else [])
    usages += [b['usage'] for b in bands.values() if b['usage'] is not None]
    return dict(matrix=matrix, down=down_total, up=up_total, down_usage=down_usage,
                up_usage=up_total/upload*100 if upload is not None else None,
                bands=bands, worst=max(usages))
