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
        self.assertFalse(app.warning)
        self.assertFalse(app.exception)
