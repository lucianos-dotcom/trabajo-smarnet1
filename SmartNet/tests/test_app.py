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
        app.toggle(key='manual_reference').set_value(True).run()
        app.selectbox(key='plan').select('Ingresar otra velocidad').run()
        self.assertEqual(app.metric[0].value, '10.5 Mbps')
        self.assertEqual(app.metric[2].value, '52.5%')
        app.number_input(key='custom_capacity').set_value(10).run()
        self.assertEqual(app.metric[2].value, '105.0%')
        self.assertTrue(any('Necesitan atención' in c.value for c in app.caption))
        self.assertFalse(app.exception)

    def test_solutions_and_rows(self):
        app = self.app()
        app.selectbox(key='preset').select('Descargas y clases online').run()
        app.checkbox(key='pause').check().run()
        self.assertEqual(next(metric.value for metric in app.metric
                              if metric.label == 'Demanda de descarga con estos cambios'), '8 Mbps')
        self.assertTrue(any('Antes: 108.0 Mbps · Con la propuesta: 8.0 Mbps' in item.value
                            for item in app.markdown))
        app.button(key='add').click().run()
        self.assertEqual(len(app.session_state['rows']), 4)
        next(button for button in app.button if button.label == 'Quitar este grupo').click().run()
        self.assertEqual(len(app.session_state['rows']), 3)
        self.assertFalse(app.exception)
        app.selectbox(key='preset').select('Empezar desde cero').run()
        self.assertEqual(app.metric[0].value, '0 Mbps')
        app.button(key='add').click().run()
        app.toggle(key='manual_reference').set_value(True).run()
        app.selectbox(key='plan').select('No sé mi velocidad').run()
        self.assertIn('### 🏠 Falta una referencia de velocidad', [m.value for m in app.markdown])
        self.assertFalse(app.exception)

    def test_bands_and_camera_preset(self):
        app=self.app()
        app.selectbox(key='preset').select('Casa con cámaras y dispositivos inteligentes').run()
        self.assertTrue(any('Subida de referencia: pendiente' in m.value for m in app.markdown))
        app.toggle(key='manual_reference').set_value(True).run()
        app.checkbox(key='know_upload').check().run()
        app.number_input(key='upload_capacity').set_value(5).run()
        self.assertTrue(any('165.0%' in m.value and 'Subida de referencia' in m.value for m in app.markdown))
        self.assertTrue(any('Necesitan atención' in c.value for c in app.caption))
        original = app.session_state['rows']
        app.button(key='try_bands').click().run()
        self.assertEqual(app.session_state['rows'], original)
        self.assertTrue(any('→ 2,4 GHz' in m.value for m in app.markdown))
        self.assertTrue(any('→ 5 GHz' in m.value for m in app.markdown))
        self.assertFalse(app.latex)
        self.assertFalse(app.exception)

    def test_classroom_plans(self):
        app = self.app()
        app.toggle(key='manual_reference').set_value(True).run()
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
        self.assertTrue(any('Todavía falta capacidad en 5 GHz' in item.value for item in app.warning))
        self.assertTrue(any('Deja la descarga para después' in item.value for item in app.markdown))
        app.button(key='try_bands').click().run()
        app.checkbox(key='pause').check().run()
        self.assertTrue(any('Prueba cambiar equipos de banda' in item.value for item in app.markdown))
        app.button(key='try_bands').click().run()
        self.assertTrue(any('62.0%' in item.value for item in app.markdown))
        self.assertTrue(any('El Wi-Fi alcanza con estos cambios' in item.value for item in app.success))
        self.assertEqual(app.session_state['rows'], original)

    def test_wifi_advice_when_no_action_relieves_overload(self):
        app = self.app()
        app.selectbox(key='preset').select('Empezar desde cero').run()
        app.button(key='add').click().run()
        next(box for box in app.selectbox if box.label == 'Equipo 1').select('📷 Cámara de seguridad').run()
        next(box for box in app.selectbox if box.label == 'Conexión del grupo 1').select('2,4 GHz').run()
        next(box for box in app.number_input if box.label == 'Cantidad 1').set_value(50).run()
        self.assertTrue(any('Qué probar' in item.value and '5 GHz' in item.value for item in app.markdown))
        self.assertFalse(app.exception)

    def test_provider_guidance_when_plan_is_short(self):
        app = self.app()
        app.selectbox(key='preset').select('Descargas y clases online').run()
        app.toggle(key='manual_reference').set_value(True).run()
        app.selectbox(key='plan').select('20 Mbps').run()
        self.assertTrue(any('Cuándo evaluar otro plan' in item.value and 'falta descarga' in item.value
                            for item in app.markdown))
        app.checkbox(key='pause').check().run()
        self.assertFalse(any('Cuándo evaluar otro plan' in item.value for item in app.markdown))

    def test_social_preset_and_short_videos(self):
        app = self.app()
        app.selectbox(key='preset').select('Solo uso el celular para redes sociales').run()
        rows = app.session_state['rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['count'], rows[0]['band']), (1, 'No sé la banda'))
        self.assertTrue(any('uso de redes que elegiste' in item.value for item in app.markdown))
        app.session_state['last_speed'] = dict(download=42, upload=7, latency=20, jitter=2,
                                               id='social', timestamp='2026-11-25T00:00:00Z')
        app.session_state['speed_history'] = []
        app.run()
        self.assertTrue(any('leer mensajes y revisar publicaciones' in item.value for item in app.markdown))
        self.assertFalse(any(box.key in ('pause', 'lower') for box in app.checkbox))
        self.assertFalse(any(button.key == 'try_bands' for button in app.button))
        app.checkbox(key='still_slow').check().run()
        guidance = [item.value for item in app.markdown]
        self.assertTrue(any('Prueba otra app en el mismo lugar' in text for text in guidance))
        self.assertTrue(any('Cuándo llamar a tu compañía' in text for text in guidance))
        self.assertFalse(any('Cuándo evaluar otro plan' in text for text in guidance))
        next(box for box in app.selectbox if box.label == 'Actividad 1').select(
            'Videos cortos en redes (Reels o TikTok)').run()
        self.assertEqual(app.metric[0].value, '3 Mbps')
        self.assertTrue(any('Hay capacidad para ver videos cortos' in item.value for item in app.markdown))
        self.assertFalse(app.exception)

    def test_speed_result_is_used_automatically(self):
        app=self.app()
        app.session_state['last_speed']=dict(download=42.0, upload=7.0, latency=20.0, jitter=2.0, id='sample', timestamp='2026-11-04T00:00:00Z')
        app.session_state['speed_history']=[]
        app.run()
        self.assertEqual(app.metric[1].value, '42 Mbps')
        self.assertTrue(any('Subida de referencia: **7 Mbps**' in item.value for item in app.markdown))
        app.toggle(key='manual_reference').set_value(True).run()
        app.selectbox(key='plan').select('500 Mbps').run()
        self.assertEqual(app.metric[1].value, '500 Mbps')
        app.toggle(key='manual_reference').set_value(False).run()
        self.assertEqual(app.metric[1].value, '42 Mbps')
        app.toggle(key='manual_reference').set_value(True).run()
        self.assertEqual(app.selectbox(key='plan').value, '500 Mbps')
        self.assertFalse(app.exception)
