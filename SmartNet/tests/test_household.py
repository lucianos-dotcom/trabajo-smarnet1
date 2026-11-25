import unittest
from household import ACTIVITIES, DEVICES, PRESETS, evaluate, improve

class HouseholdTests(unittest.TestCase):
    def rows(self, name):
        return [dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n) for d,a,n in PRESETS[name]]

    def academic_example(self):
        groups = [(0, 0, 2), (0, 2, 1), (1, 0, 1), (1, 2, 1), (2, 1, 2)]
        return [dict(device=DEVICES[d], activity=ACTIVITIES[a], count=n) for d, a, n in groups]

    def test_example_preserved(self):
        _, _, total, usage, _ = evaluate(self.academic_example(),20)
        self.assertEqual((total,usage),(14.5,72.5))

    def test_interventions(self):
        rows=self.rows('Descargas y clases online')
        self.assertEqual(evaluate(rows,100)[2],108)
        self.assertEqual(evaluate(improve(rows,True,False),100)[2],8)
        self.assertEqual(evaluate(rows,100)[2],108)
        series=self.rows('Todos viendo series')
        self.assertEqual(evaluate(improve(series,False,True),100)[2],20)

    def test_preventive_threshold(self):
        rows=self.academic_example()
        self.assertEqual(evaluate(rows,18.125)[4],'Al límite')
        self.assertEqual(evaluate([],20)[2],0)
