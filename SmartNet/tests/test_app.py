import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def test_simulate_compare_and_reset(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '14.5 Mbps')
        self.assertEqual(app.metric[1].value, '72.5%')
        app.button[0].click().run()
        app.sidebar.number_input[0].set_value(10).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, '145.0%')
        self.assertTrue(app.error)
        self.assertIn('comparison', app.session_state)
        app.sidebar.button[0].click().run()
        self.assertEqual(app.metric[1].value, '72.5%')
        self.assertFalse(app.exception)
