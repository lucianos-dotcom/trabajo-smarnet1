import unittest
from household import ACTIVITIES, DEVICES, PRESETS, evaluate, improve

class HouseholdTests(unittest.TestCase):
    def rows(self, name):
        return [dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n) for d,a,n in PRESETS[name]]

    def test_example_preserved(self):
        _, _, total, usage, _ = evaluate(self.rows('Ejemplo de la asignatura'),20)
        self.assertEqual((total,usage),(14.5,72.5))

    def test_interventions(self):
        rows=self.rows('Descargas y clases online')
        self.assertEqual(evaluate(rows,100)[2],108)
        self.assertEqual(evaluate(improve(rows,True,False),100)[2],8)
        self.assertEqual(evaluate(rows,100)[2],108)
        series=self.rows('Todos viendo series')
        self.assertEqual(evaluate(improve(series,False,True),100)[2],20)

    def test_preventive_threshold(self):
        rows=self.rows('Ejemplo de la asignatura')
        self.assertEqual(evaluate(rows,18.125)[4],'Al límite')
        self.assertEqual(evaluate([],20)[2],0)
