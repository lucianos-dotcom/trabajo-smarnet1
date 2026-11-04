import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)

    def test_academic_example_and_capacity(self):
        app = self.app()
        self.assertFalse(app.exception)
        app.selectbox(key='preset').select('Ejemplo de la asignatura').run()
        app.selectbox(key='plan').select('Ingresar otra velocidad').run()
        self.assertEqual(app.metric[0].value, '14.5 Mbps')
        self.assertEqual(app.metric[2].value, '72.5%')
        app.number_input(key='custom_capacity').set_value(10).run()
        self.assertEqual(app.metric[2].value, '145.0%')
        self.assertTrue(app.error)
        self.assertFalse(app.exception)

    def test_solutions_and_rows(self):
        app = self.app()
        app.selectbox(key='preset').select('Descargas y clases online').run()
        app.checkbox(key='pause').check().run()
        self.assertEqual(app.metric[3].value, '8 Mbps')
        app.button(key='add').click().run()
        self.assertEqual(len(app.session_state['rows']), 4)
        app.button(key='remove_0').click().run()
        self.assertEqual(len(app.session_state['rows']), 3)
        self.assertFalse(app.exception)
        app.selectbox(key='preset').select('Empezar desde cero').run()
        self.assertEqual(app.metric[0].value, '0 Mbps')
        app.selectbox(key='plan').select('No sé mi velocidad').run()
        self.assertTrue(app.warning)
        app.checkbox(key='use_test').check().run()
        self.assertFalse(any('Velocidad desconocida' in w.value for w in app.warning))
        self.assertFalse(app.exception)

    def test_bands_and_camera_preset(self):
        app=self.app()
        app.selectbox(key='preset').select('Casa con cámaras y dispositivos inteligentes').run()
        app.checkbox(key='know_upload').check().run()
        app.number_input(key='upload_capacity').set_value(5).run()
        self.assertTrue(any('Subida de internet' in e.value for e in app.error))
        app.checkbox(key='model_wifi').check().run()
        app.selectbox(key='band_0').select('2,4 GHz').run()
        app.checkbox(key='move').check().run()
        self.assertFalse(app.exception)

    def test_import_speed_result(self):
        app=self.app()
        app.session_state['last_speed']=dict(download=42.0, upload=7.0, latency=20.0, jitter=2.0, id='sample', timestamp='2026-11-04T00:00:00Z')
        app.session_state['speed_history']=[]
        app.run()
        app.button(key='apply_speed').click().run()
        self.assertEqual(app.number_input(key='measured').value,42)
        self.assertEqual(app.number_input(key='upload_capacity').value,7)
        self.assertTrue(app.checkbox(key='use_test').value)
        self.assertFalse(app.exception)
