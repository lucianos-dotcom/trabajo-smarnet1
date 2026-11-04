import unittest
import numpy as np
from household import (ACTIVITIES, DEVICES, BANDS, network_summary, improve)
from speed_test import valid_result

class NetworkTests(unittest.TestCase):
    def row(self, activity, count=1, band=BANDS[0]):
        return dict(device=DEVICES[0],activity=ACTIVITIES[activity],count=count,band=band)

    def test_cameras_can_saturate_upload_with_free_download(self):
        s=network_summary([self.row(6,4)],300,5,{BANDS[0]:80,BANDS[1]:300})
        self.assertAlmostEqual(s['down'],0.4)
        self.assertEqual(s['up'],8)
        self.assertEqual(s['up_usage'],160)
        self.assertLess(s['down_usage'],1)

    def test_dual_band_and_common_internet_bottleneck(self):
        rows=[self.row(5,2,BANDS[0]),self.row(3,2,BANDS[1])]
        s=network_summary(rows,100,20,{BANDS[0]:80,BANDS[1]:300})
        self.assertEqual(s['down_usage'],150)
        self.assertGreater(s['bands'][BANDS[0]]['usage'],100)
        self.assertLess(s['bands'][BANDS[1]]['usage'],100)
        moved=[dict(r,band=BANDS[1]) for r in rows]
        m=network_summary(moved,100,20,{BANDS[0]:80,BANDS[1]:300})
        self.assertEqual(m['down'],s['down'])
        self.assertEqual(m['bands'][BANDS[0]]['usage'],0)

    def test_unknown_and_cable_not_assigned_to_wifi(self):
        rows=[self.row(5,1,BANDS[2]),self.row(5,1,BANDS[3])]
        s=network_summary(rows,100,None,{BANDS[0]:80})
        self.assertEqual(s['down'],100)
        self.assertIsNone(s['up_usage'])
        self.assertEqual(s['bands'][BANDS[0]]['usage'],0)
        self.assertEqual(s['bands'][BANDS[3]]['down'],50)
        np.testing.assert_array_equal(sum((s['bands'][b]['matrix'] for b in BANDS)),s['matrix'])

    def test_invalid_capacities(self):
        for down,up,caps in [(0,20,{}),(100,0,{}),(100,20,{BANDS[0]:float('nan')})]:
            with self.assertRaises(ValueError):
                network_summary([],down,up,caps)

    def test_speed_result_validation(self):
        result=dict(download=123,upload=45,latency=20,jitter=2,id='test',timestamp='2026-11-04T00:00:00Z')
        self.assertTrue(valid_result(result))
        for extra in [dict(upload=0),dict(download=float('inf')),dict(latency=-1),dict(download=True),dict(id=None)]:
            self.assertFalse(valid_result(dict(result,**extra)))
