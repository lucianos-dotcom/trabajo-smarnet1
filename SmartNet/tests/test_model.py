import unittest
import numpy as np
from model import BASE, calculate

class ModelTests(unittest.TestCase):
    def test_reference(self):
        demand, total, usage, status = calculate(BASE, 20)
        np.testing.assert_allclose(demand, [2.5, 2, 10, 0, 0])
        self.assertEqual((total, usage, status), (14.5, 72.5, 'Bajo la capacidad'))

    def test_boundaries(self):
        self.assertEqual(calculate(BASE, 14.5)[3], 'Al límite')
        self.assertEqual(calculate(BASE, 10)[3], 'Posible saturación')
        self.assertEqual(calculate(np.zeros_like(BASE), 20)[1:3], (0, 0))

    def test_invalid(self):
        for a,b in [(BASE,0), (BASE,float('nan')), ([[-1,0,0]],20), ([[0.5,0,0]],20), ([[1,2]],20)]:
            with self.assertRaises(ValueError):
                calculate(a,b)

if __name__ == '__main__':
    unittest.main()
