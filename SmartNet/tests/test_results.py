import unittest
from household import network_summary, ACTIVITIES, DEVICES, BANDS
from results import checks, verdict, state

class FamilyResultsTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual([state(x) for x in [None,0,79.9,80,100,100.1]],
                         ['unknown','good','good','tight','tight','over'])

    def test_unknown_upload_cannot_give_all_clear(self):
        summary=network_summary([],300,None,{})
        items=checks(summary,True,False)
        self.assertEqual(verdict(items,True)[0],'unknown')
        self.assertEqual(verdict(items,False)[0],'empty')

    def test_camera_bottleneck_survives_familiar_summary(self):
        rows=[dict(device=DEVICES[4],activity=ACTIVITIES[6],count=4,band=BANDS[0])]
        summary=network_summary(rows,300,5,{BANDS[0]:80,BANDS[1]:300})
        items=checks(summary,True,True)
        self.assertEqual(items[0]['state'],'good')
        self.assertEqual(items[1]['state'],'over')
        self.assertEqual(verdict(items,True)[0],'over')

    def test_unknown_band_cannot_give_all_clear(self):
        summary=network_summary([],300,20,{BANDS[0]:80,BANDS[1]:300})
        items=checks(summary,True,True)
        self.assertEqual(verdict(items,True,True)[0],'unknown')
        self.assertEqual(verdict(items,True,False)[0],'good')
