import hashlib
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import backend.app as api
from backend.waveform import extract_waveform,WaveformError


class WaveformTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=api.ROOT)
        self.root=Path(self.temp.name)
        self.path=self.root/'test.wav'

    def tearDown(self):self.temp.cleanup()

    def write(self,samples,width=2):
        with wave.open(str(self.path),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(width);audio.setframerate(16000)
            audio.writeframes(b''.join(struct.pack('<h',s) for s in samples) if width==2 else bytes(samples))
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_exact_signed_pcm_measurements(self):
        samples=[0,16384,-16384,32767,-32768]
        digest=self.write(samples)
        result=extract_waveform(self.path,digest,self.root)
        self.assertEqual(result['frameCount'],5)
        self.assertEqual(result['peakAmplitude'],1)
        self.assertEqual(result['fullScaleSampleCount'],2)
        self.assertAlmostEqual(result['rmsAmplitude'],math.sqrt(sum(s*s for s in samples)/5)/32768)
        self.assertEqual(result['bins'][2]['min'],-.5)
        self.assertFalse(result['detectorRun'])

    def test_unsigned_pcm_silence_is_zero(self):
        digest=self.write([128]*500,width=1)
        result=extract_waveform(self.path,digest,self.root)
        self.assertEqual(result['peakAmplitude'],0)
        self.assertEqual(result['rmsAmplitude'],0)
        self.assertEqual(len(result['bins']),256)

    def test_digest_mismatch_rejected(self):
        self.write([0]*20)
        with self.assertRaises(WaveformError) as caught:extract_waveform(self.path,'0'*64,self.root)
        self.assertEqual(caught.exception.status,409)

    def test_case_directory_enforced(self):
        digest=self.write([0]*20)
        with self.assertRaises(WaveformError):extract_waveform(self.path,digest,self.root/'other')

    def test_non_wav_is_explicitly_unsupported(self):
        self.path.write_bytes(b'not a wav file')
        digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(WaveformError) as caught:extract_waveform(self.path,digest,self.root)
        self.assertEqual(caught.exception.code,'UNSUPPORTED_WAV')
