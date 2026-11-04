"""Referencias ilustrativas para escenarios domésticos; no mide la red."""
import numpy as np
from model import calculate

DEVICES = ['📱 Celular', '💻 Notebook o PC', '📺 Smart TV', '🎮 Consola']
ACTIVITIES = ['WhatsApp y navegar', 'Ver videos o series en HD', 'Videollamada o clase online', 'Ver videos o series en 4K', 'Jugar online', 'Descargar juegos o archivos']
RATES = np.array([0.5, 5, 1.5, 25, 3, 50], dtype=float)
PRESETS = {
    'Una tarde en casa': [(0, 0, 2), (1, 2, 1), (2, 1, 1), (3, 4, 1)],
    'Todos viendo series': [(0, 1, 2), (2, 3, 2)],
    'Descargas y clases online': [(1, 2, 2), (3, 5, 2), (2, 1, 1)],
    'Ejemplo de la asignatura': [(0, 0, 2), (0, 2, 1), (1, 0, 1), (1, 2, 1), (2, 1, 2)],
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
