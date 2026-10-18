"""Measured amplitude envelope for bounded uncompressed PCM WAV files."""
import array
import hashlib
import math
import sys
import wave
from pathlib import Path


class WaveformError(ValueError):
    def __init__(self,code,message,status=422):
        super().__init__(message)
        self.code,self.status=code,status


def extract_waveform(path: Path, expected_sha256: str, allowed_root: Path) -> dict:
    path=path.resolve()
    if not path.is_relative_to(allowed_root.resolve()) or not path.is_file():
        raise WaveformError('WAVEFORM_BYTES_UNAVAILABLE','Stored bytes are unavailable for this case.',404)
    if path.stat().st_size>64*1024*1024:
        raise WaveformError('WAVEFORM_TOO_LARGE','This waveform slice supports files up to 64 MB.',413)
    with path.open('rb') as source:
        digest=hashlib.sha256()
        total=0
        for chunk in iter(lambda:source.read(1024*1024),b''):
            total+=len(chunk)
            if total>64*1024*1024:
                raise WaveformError('WAVEFORM_TOO_LARGE','File exceeded the 64 MB waveform limit.',413)
            digest.update(chunk)
        if digest.hexdigest()!=expected_sha256:
            raise WaveformError('INTEGRITY_MISMATCH','Stored bytes differ from the registered digest. No waveform was produced.',409)
        source.seek(0)
        try:
            with wave.open(source,'rb') as audio:
                channels,width,rate,frames=audio.getnchannels(),audio.getsampwidth(),audio.getframerate(),audio.getnframes()
                if audio.getcomptype()!='NONE' or width not in (1,2) or not 1<=channels<=8 or not 1<=rate<=384000 or frames<1:
                    raise WaveformError('UNSUPPORTED_WAVEFORM','Choose nonempty 8-bit or 16-bit PCM WAV audio with up to eight channels.')
                if frames*channels*width>64*1024*1024:
                    raise WaveformError('WAVEFORM_TOO_LARGE','Declared PCM data exceeds the 64 MB limit.',413)
                bins=min(256,frames)
                envelope=[]
                scale=128 if width==1 else 32768
                sample_count,clipped,energy,peak=0,0,0,0
                for index in range(bins):
                    start=index*frames//bins
                    end=(index+1)*frames//bins
                    raw=audio.readframes(end-start)
                    if len(raw)!=(end-start)*channels*width:
                        raise WaveformError('TRUNCATED_WAV','The WAV data is shorter than its declared frame count.')
                    if width==1:
                        samples=[value-128 for value in raw]
                    else:
                        samples=array.array('h',raw)
                        if sys.byteorder!='little':samples.byteswap()
                    low,high=min(samples),max(samples)
                    squared=sum(value*value for value in samples)
                    count=len(samples)
                    clipped+=sum(value<=-scale or value>=scale-1 for value in samples)
                    sample_count+=count;energy+=squared;peak=max(peak,abs(low)/scale,abs(high)/scale)
                    envelope.append({'startSeconds':start/rate,'endSeconds':end/rate,'min':low/scale,'max':high/scale,'rms':math.sqrt(squared/count)/scale})
            source.seek(0)
            after=hashlib.sha256()
            remaining=64*1024*1024+1
            while remaining>0:
                chunk=source.read(min(1024*1024,remaining))
                if not chunk:break
                after.update(chunk);remaining-=len(chunk)
            if after.hexdigest()!=expected_sha256:
                raise WaveformError('MEDIA_CHANGED','Stored bytes changed during waveform extraction.',409)
        except (wave.Error,EOFError) as exc:
            raise WaveformError('UNSUPPORTED_WAV','The stored file is not a readable PCM WAV file.') from exc
    return {'method':'pcm-min-max-rms-envelope','sha256':expected_sha256,'durationSeconds':frames/rate,
            'sampleRate':rate,'channels':channels,'bitsPerSample':width*8,'frameCount':frames,'bins':envelope,
            'peakAmplitude':peak,'rmsAmplitude':math.sqrt(energy/sample_count)/scale,'fullScaleSampleCount':clipped,
            'detectorRun':False,'limits':['Amplitude bins combine all channels.','Full-scale samples and amplitude patterns do not establish manipulation or authenticity.']}
