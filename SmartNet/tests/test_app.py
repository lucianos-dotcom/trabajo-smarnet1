import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)

    def test_scenario_and_capacity(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertNotIn('Ejemplo de la asignatura', app.selectbox(key='preset').options)
        app.selectbox(key='preset').select('Una tarde en casa').run()
        app.selectbox(key='plan').select('Ingresar otra velocidad').run()
        self.assertEqual(app.metric[0].value, '10.5 Mbps')
        self.assertEqual(app.metric[2].value, '52.5%')
        app.number_input(key='custom_capacity').set_value(10).run()
        self.assertEqual(app.metric[2].value, '105.0%')
        self.assertTrue(any('No alcanza en este ejemplo' in m.value for m in app.markdown))
        self.assertFalse(app.exception)

    def test_solutions_and_rows(self):
        app = self.app()
        app.selectbox(key='preset').select('Descargas y clases online').run()
        app.checkbox(key='pause').check().run()
        self.assertEqual(app.metric[3].value, '8 Mbps')
        app.button(key='add').click().run()
        self.assertEqual(len(app.session_state['rows']), 4)
        next(button for button in app.button if button.label == 'Quitar este grupo').click().run()
        self.assertEqual(len(app.session_state['rows']), 3)
        self.assertFalse(app.exception)
        app.selectbox(key='preset').select('Empezar desde cero').run()
        self.assertEqual(app.metric[0].value, '0 Mbps')
        app.button(key='add').click().run()
        app.selectbox(key='plan').select('No sé mi velocidad').run()
        self.assertIn('⚪ Falta un dato', [m.value.strip('*') for m in app.markdown])
        app.checkbox(key='use_test').check().run()
        self.assertTrue(app.checkbox(key='use_test').value)
        self.assertFalse(app.exception)

    def test_bands_and_camera_preset(self):
        app=self.app()
        app.selectbox(key='preset').select('Casa con cámaras y dispositivos inteligentes').run()
        self.assertTrue(any('Subida de referencia: pendiente' in m.value for m in app.markdown))
        app.checkbox(key='know_upload').check().run()
        app.number_input(key='upload_capacity').set_value(5).run()
        self.assertTrue(any('165.0%' in m.value and 'de subida' in m.value for m in app.markdown))
        self.assertTrue(any('No alcanza en este ejemplo' in m.value for m in app.markdown))
        original = app.session_state['rows']
        app.button(key='try_bands').click().run()
        self.assertEqual(app.session_state['rows'], original)
        self.assertTrue(any('→ 2,4 GHz' in m.value for m in app.markdown))
        self.assertTrue(any('→ 5 GHz' in m.value for m in app.markdown))
        self.assertFalse(app.latex)
        self.assertFalse(app.exception)

    def test_classroom_plans(self):
        app = self.app()
        app.selectbox(key='plan').select('500 Mbps').run()
        for plan, upload, usage in [
            ('Wi-Fi saturado · Plan simétrico 300/300 Mbps', 300, '2.1%'),
            ('Wi-Fi saturado · Plan asimétrico 300/10 Mbps', 10, '64.0%'),
        ]:
            app.selectbox(key='preset').select(plan).run()
            self.assertEqual(app.metric[1].value, '300 Mbps')
            text = [item.value for item in app.markdown]
            self.assertIn(f'Subida del ejemplo: **{upload} Mbps** · uso estimado: **{usage}**.', text)
            self.assertTrue(any(line.startswith('**2,4 GHz.**') and '**112.5%**' in line for line in text))
            self.assertTrue(any(line.startswith('**5 GHz.**') and '**108.0%**' in line for line in text))
            self.assertTrue(any('El plan alcanza para enviar y recibir' in line for line in text))
            self.assertTrue(any('**22.5 Mbps**' in line and '**20 Mbps**' in line for line in text))
            self.assertTrue(any('**75.6 Mbps**' in line and '**70 Mbps**' in line for line in text))
            self.assertFalse(app.exception)
        app.selectbox(key='preset').select('Una tarde en casa').run()
        self.assertEqual(app.selectbox(key='plan').value, '500 Mbps')

    def test_classroom_combines_improvements(self):
        app = self.app()
        app.selectbox(key='preset').select('Wi-Fi saturado · Plan asimétrico 300/10 Mbps').run()
        original = app.session_state['rows']
        app.button(key='try_bands').click().run()
        self.assertTrue(any('134.1%' in item.value for item in app.markdown))
        self.assertTrue(app.warning)
        app.checkbox(key='pause').check().run()
        self.assertTrue(any('62.0%' in item.value for item in app.markdown))
        self.assertTrue(any('las dos bandas tienen capacidad' in item.value for item in app.success))
        self.assertEqual(app.session_state['rows'], original)

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
