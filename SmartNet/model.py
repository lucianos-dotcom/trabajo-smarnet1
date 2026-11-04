import numpy as np

TYPES = ['Celulares', 'Computadores', 'Smart TV', 'Consolas', 'Cámaras']
ACTIVITIES = ['Navegación', 'Video HD', 'Videollamada']
RATES = np.array([0.5, 5.0, 1.5])
BASE = np.array([[2, 0, 1], [1, 0, 1], [0, 2, 0], [0, 0, 0], [0, 0, 0]])

def calculate(matrix, capacity, rates=RATES):
    a, b = np.asarray(matrix, dtype=float), np.asarray(rates, dtype=float)
    if a.ndim != 2 or b.ndim != 1 or a.shape[1] != b.size:
        raise ValueError('Dimensiones incompatibles de A y b.')
    if not np.all(np.isfinite(a)) or np.any(a < 0) or np.any(a != np.floor(a)):
        raise ValueError('Las cantidades deben ser enteros no negativos.')
    if not np.all(np.isfinite(b)) or np.any(b < 0):
        raise ValueError('Los consumos deben ser finitos y no negativos.')
    if not np.isfinite(capacity) or capacity <= 0:
        raise ValueError('La capacidad debe ser mayor que cero.')
    demand = a @ b
    total = float(demand.sum())
    usage = total / capacity * 100
    status = 'Posible saturación' if usage > 100 else 'Al límite' if usage == 100 else 'Bajo la capacidad'
    return demand, total, usage, status
