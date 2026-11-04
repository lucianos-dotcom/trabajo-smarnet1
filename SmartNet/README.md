# SmartNet · Internet en casa

Simulador educativo para hogares en Chile, proyecto de Funciones y Matrices (Analista Programador, INACAP). No escanea Wi-Fi ni mide tráfico real.

## Windows: abrir la aplicación

Instala Python **3.12 de 64 bits** (las dependencias fijadas no están preparadas para Python 3.14). Abre `cmd` en esta carpeta y ejecuta cada línea:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

Después de la primera instalación, basta el último comando. Mantén la terminal abierta durante el uso. Ctrl+C detiene el servidor.

## Otros sistemas / entorno cloud

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.headless true
```

## Uso para una familia

1. Elige los megas del plan o ingresa la descarga obtenida con un test de velocidad en tu equipo. Si no conoces la velocidad, prueba un escenario hipotético.
2. Selecciona un ejemplo o agrega los equipos y su actividad principal simultánea. No cuentes un equipo dos veces.
3. Revisa el resultado: verde bajo 80%, amarillo desde 80% hasta 100%, rojo sobre 100%. El 80% es un margen preventivo didáctico, no un estándar técnico.
4. Prueba pausar descargas o cambiar 4K a HD y compara el porcentaje antes/después sin modificar el escenario original.

Las opciones de velocidades son ejemplos orientativos en Mbps, no un catálogo comercial verificado. Consulta tu boleta o proveedor para conocer el plan, disponibilidad y tecnología. Los GB de una bolsa de datos no son Mbps. Una conexión con margen de descarga puede seguir teniendo problemas de cobertura, latencia o subida; la app ofrece consejos diferenciados y no recomienda automáticamente contratar más velocidad.

## Modelo académico

`household.py` organiza la matriz A por tipo de equipo y actividad. b contiene supuestos ilustrativos por equipo activo: navegación 0,5; HD 5; videollamada 1,5; 4K 25; jugar 3; descarga 50 Mbps. No son mediciones ni estándares universales. La descarga real puede ocupar gran parte de la conexión; el valor fijo permite comparar escenarios. No se modelan cámaras de seguridad ni saturación de subida.

A × b entrega demanda por equipo. C es su suma; U(C) = C/B × 100, con B > 0. La sección académica está plegada para no dificultar el uso cotidiano. Conserva el ejemplo original de `model.py`: selecciona “Ejemplo de la asignatura” y B = 20 Mbps para obtener [2,5; 2; 10; 0] Mbps, C = 14,5 Mbps y U = 72,5%.

La comparación usa el mismo B y aplica cambios únicamente a las actividades elegidas. El CSV exporta matriz y demanda por equipo. No incluye interferencia, cobertura, sobrecarga de protocolos, tráfico variable ni capacidad de subida. Resultados OMNeT++/INET pendientes de recibir los archivos originales.

## Pruebas

Desde esta carpeta, con el entorno virtual activo:

```bash
python -m unittest discover -s tests -v
```

Incluye cálculos originales, fronteras, escenarios domésticos, medidas de reducción, formularios, capacidad desconocida y agregar/quitar equipos.
