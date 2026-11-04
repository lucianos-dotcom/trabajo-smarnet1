# SmartNet · Internet en casa

Aplicación educativa para hogares en Chile: medición orientativa desde el navegador, escenarios domésticos y matrices para Funciones y Matrices (Analista Programador, INACAP).

## Windows

Instala **Python 3.12 de 64 bits**. Extrae el ZIP y abre **Iniciar_SmartNet.bat**. El script crea el entorno virtual si falta, instala las dependencias y abre Streamlit. Mantén la ventana abierta. Este lanzador se entrega para Windows; no se ha ejecutado en una máquina Windows durante el desarrollo.

Alternativa desde `cmd` dentro de esta carpeta:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

Para actualizar, detén la app (Ctrl+C) y reemplaza los archivos de SmartNet con los del nuevo ZIP, incluyendo **speed_component**, **speed_test.py** y **household.py**. Conserva tu carpeta `.venv`.

## Linux / cloud

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.headless true
```

## Flujo familiar

1. Haz el test aquí, o ingresa manualmente una velocidad. Si no la conoces, el escenario de internet es hipotético. Confirma los megas del plan en tu boleta; GB de una bolsa no son Mbps. Las velocidades seleccionables son ejemplos, no ofertas verificadas de operadores.
2. Si quieres, activa comparación de 2,4/5 GHz y edita sus capacidades **supuestas** y escenarios de señal.
3. Agrega grupos de equipos con actividad y banda comunes. Cuenta cada equipo una vez. Seleccionar una cámara propone transmisión a la nube; ajústala si no transmite constantemente. No se modela grabación exclusivamente local.
4. Revisa descarga de internet, subida y bandas por separado. Verde <80%, amarillo 80–100%, rojo >100%. 80% es un margen preventivo didáctico, no estándar técnico.
5. Compara pausar descargas, bajar 4K a HD o mover equipos compatibles entre bandas. El cambio de banda no reduce el consumo total de internet.

Incluye celulares, PC, TV, consolas, cámaras, tablets, TV Box, parlantes, ampolletas/enchufes, impresoras y aspiradoras robot. El tipo organiza la matriz; es la **actividad elegida** la que determina la demanda.

## Test en el navegador

El componente local `speed_component` no usa scripts JavaScript externos. Desde el navegador del visitante hace GET a `https://speed.cloudflare.com/__down` y POST a `https://speed.cloudflare.com/__up`. No prueba la conexión del servidor Python. No requiere claves, ejecutables ni privilegios de administrador.

Solo comienza al pulsar el botón. Prueba breve secuencial adaptativa, con calentamiento, cinco respuestas HTTP y transferencias acotadas; máximo nominal menor de 45 MB por intento, límites de 15 segundos por petición y 75 segundos en total. Puede consumir una bolsa de datos. La subida usa bytes aleatorios, no archivos del usuario. Cloudflare recibe la IP y metadatos habituales de conexión; no recibe el escenario. Consulta su política de privacidad desde la interfaz. Se puede cancelar; un fallo no crea una medición nueva ni borra la anterior, que sigue identificada como última prueba.

La velocidad usa bytes transferidos × 8 / segundos / 1.000.000. Se calcula la mediana de transferencias de al menos 150 ms o, si todas fueron más breves, la última muestra. La descarga incluye recepción del cuerpo; la subida incluye respuesta del servicio. La latencia es mediana de respuestas HTTP, no ping ICMP. La variación mostrada es máximo menos mínimo de esas respuestas, no jitter de paquetes RTP. No se mide pérdida de paquetes ni velocidad máxima certificada. Conexiones muy rápidas pueden subestimarse por el tamaño acotado y las transferencias secuenciales.

Pulsa “Usar esta medición” para copiar descarga y subida al simulador. El historial conserva cinco pruebas en la sesión, etiquetadas según el lugar elegido al iniciar. Repite cerca/lejos/con cable: una diferencia sugiere revisar cobertura o interferencia, pero no prueba una causa única. Una medición mientras otros usan internet refleja capacidad disponible en ese momento, no capacidad total de toda la casa; usarla como referencia es una aproximación.

**Requisito de red:** el navegador debe poder acceder a `speed.cloudflare.com` por HTTPS con CORS. Si el servicio o la red lo impiden, la app muestra error y permite ingresar resultados manualmente. No se deshabilita TLS ni se intenta eludir restricciones.

## Modelo de descarga, subida y bandas

A tiene filas por tipo de equipo y columnas por actividad. Vectores ilustrativos por equipo activo, en Mbps (descarga/subida):

| Actividad | Descarga | Subida |
| --- | ---: | ---: |
| Navegar | 0,5 | 0,1 |
| HD | 5 | 0,1 |
| Videollamada | 1,5 | 1,5 |
| 4K | 25 | 0,1 |
| Juego online | 3 | 0,5 |
| Descargar archivos | 50 | 0,5 |
| Cámara a la nube | 0,1 | 2 |
| IoT en espera | 0,02 | 0,02 |
| Música | 0,3 | 0,05 |
| Respaldo a la nube | 0,5 | 10 |
| Conectado sin uso | 0,01 | 0,01 |

Son supuestos didácticos, no estándares universales ni mediciones. Descargas reales pueden ocupar toda la capacidad disponible; compresión/calidad alteran los consumos de cámaras y video.

D = suma(A · b_descarga), T = suma(A · b_subida). U_descarga = 100D/B_descarga, U_subida = 100T/B_subida. Sin capacidad de subida conocida no se calcula su porcentaje, aunque la descarga esté verde.

A_2,4 y A_5 separan equipos por banda. Su demanda local aproximada es suma(A_banda · (b_descarga + b_subida)), comparada con una capacidad compartida **hipotética**. Las referencias iniciales 80 y 300 Mbps no son velocidades universales. Los factores 100%, 50% y 25% representan escenarios educativos de señal y se aplican al grupo completo de cada banda. No hay medición de RSSI, ocupación del canal, retransmisiones ni ancho de canal. Las capacidades son independientes de la referencia de internet: ambas bandas y los equipos por cable comparten ese cuello de botella de internet.

“No sé la banda” se incluye en internet pero no se asigna arbitrariamente a una banda; se advierte que la comparación está incompleta. Cable no consume el Wi-Fi supuesto. Mover dispositivos entre bandas conserva demanda total. 5 GHz suele ofrecer más capacidad cerca del router, pero puede rendir peor con distancia/paredes. Ninguna banda garantiza mejor rendimiento.

La sección académica muestra A, ambos vectores, submatrices por banda y las funciones. S(n) = 100 n c / C es el caso de consumos idénticos: 10 equipos × 10 Mbps dan 125% frente a 80 Mbps y 33,3% frente a 300 Mbps.

Para el ejemplo original, elige “Ejemplo de la asignatura”, descarga personalizada 20 Mbps y desmarca usar medición: D = 14,5 Mbps y 72,5%. `model.py` conserva el modelo original. Los resultados OMNeT++/INET siguen pendientes de recibir los archivos originales.

## Validación

Desde esta carpeta con el entorno activo:

```bash
python -m unittest discover -s tests -v
```

Incluye ejemplo original, límites, cámaras saturando subida, bandas separadas, internet compartido, grupos sin banda/cable, traslado entre bandas, edición de filas e importación de mediciones.

Con Playwright, Chromium y servidor local iniciado:

```bash
node browser_tests/speed.cjs
```

Variables opcionales: `PLAYWRIGHT_MODULE` (ruta al módulo), `CHROMIUM_PATH` (ejecutable). Prueba de navegador **con respuestas controladas**: transferencias, límite de datos, envío a Streamlit, aplicación al modelo, error y cancelación. No presenta los datos controlados como velocidad real. En este entorno cloud la petición externa a Cloudflare devolvió HTTP 403; no se ha validado aquí una medición real con ese servicio. El dominio se añadió al borrador de red para revisión; guardarlo no aplica ni publica la política.

## Resultados para toda la familia

La vista principal muestra un resumen de la casa y tarjetas: recibir datos (series/navegación), enviar datos (cámaras/llamadas) y, si se activa, cada banda. Usa colores e indicaciones escritas: hay espacio, está justito, no alcanza en el ejemplo o falta un dato. No presenta un estado global verde si faltan subida o bandas necesarias; un problema conocido se muestra aunque falten otros datos.

Los porcentajes y tablas están plegados en “Quiero ver los números”. Las ideas de mejora son tarjetas con comparación “Antes / Con tus cambios”. Si la idea no afecta las actividades ingresadas, lo indica en vez de anunciar una mejora. “Qué se lleva la mayor parte” muestra porciones entre actividades (no porcentaje del plan). Las matrices siguen en la sección académica.

Comprobación de la vista familiar en navegador, con servidor iniciado:

```bash
node browser_tests/family.cjs
```

Comprueba resumen, datos desconocidos, números plegados, idea sin efecto y anchura de pantalla móvil. No requiere contactar el servicio de velocidad.
