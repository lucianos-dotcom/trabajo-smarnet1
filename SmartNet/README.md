# SmartNet

Simulador educativo de demanda y posible saturación Wi-Fi. Proyecto de Funciones y Matrices, Analista Programador, INACAP. No mide tráfico real.

## Inicio

Python 3.12:

```bash
cd SmartNet
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.headless true
```

## Modelo y validación

A organiza cantidades por tipo de equipo y actividad. Cada dispositivo cuenta una vez según su actividad principal simultánea. b contiene referencias ilustrativas editables de 0,5 Mbps (navegación), 5 Mbps (video HD) y 1,5 Mbps (videollamada). No son mediciones ni estándares universales. Las actividades son categorías genéricas; no todos los equipos necesitan usar todas ellas.

A × b entrega la demanda por equipo. C es su suma; U(C) = C/B × 100, con B > 0. Menos de 100% indica demanda bajo la referencia; 100%, al límite; más de 100%, posible saturación. No se consideran interferencias, cobertura, protocolos ni diferencias entre subida y bajada.

Ejemplo inicial: [2,5; 2; 10; 0; 0] Mbps. Total: 14,5 Mbps. Para B = 20 Mbps: 72,5%.

```bash
python -m unittest discover -s tests -v
```

La interfaz permite editar cantidades y consumos, visualizar matrices y funciones, guardar un escenario durante la sesión y exportar cantidades y demanda por equipo en CSV. Los resultados OMNeT++/INET no están incorporados: se necesitan los archivos originales para añadirlos como evidencia.
