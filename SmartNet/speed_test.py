"""The bandwidth test runs in the browser, never on the Streamlit server."""
import math
from pathlib import Path
import streamlit.components.v1 as components

_component = components.declare_component('smartnet_speed', path=str(Path(__file__).parent / 'speed_component'))

def valid_result(value):
    if not isinstance(value, dict):
        return False
    return (all(isinstance(value.get(k), (int, float)) and not isinstance(value[k], bool)
                and math.isfinite(value[k]) and value[k] >= 0 for k in ('download', 'upload', 'latency', 'jitter'))
            and 0 < value['download'] <= 100000 and 0 < value['upload'] <= 100000
            and isinstance(value.get('id'), str) and isinstance(value.get('timestamp'), str))

def render_speed_test(location='Sin etiqueta'):
    return _component(location=location, key='browser_speed', default=None)
