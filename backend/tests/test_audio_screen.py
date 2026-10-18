import unittest
from backend.audio_screen import classify_level


class AudioScreenLevelTests(unittest.TestCase):
    def test_short_high_score_stays_uncertain(self):
        self.assertEqual(classify_level(.999,1,.1),'uncertain')

    def test_quiet_window_is_unassessed(self):
        self.assertEqual(classify_level(.99,4,.0001),'unassessed')

    def test_low_is_a_lower_cue(self):
        self.assertEqual(classify_level(.2,4,.1),'lower')

    def test_middle_is_uncertain(self):
        self.assertEqual(classify_level(.5,4,.1),'uncertain')

    def test_high_is_elevated(self):
        self.assertEqual(classify_level(.8,4,.1),'elevated')
