"""Experimental, windowed AASIST-L audio screening; not visual or forensic validation."""
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .media_inspection import inspect_file

ROOT = Path(__file__).resolve().parents[1]
_model = None


def load_model():
    global _model
    if _model is not None:
        return _model
    import torch
    folder = ROOT/'models/aasist-l'
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        if hashlib.sha256((folder/item['file']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Research model file checksum mismatch')
    spec = importlib.util.spec_from_file_location('atlas_pinned_aasist',folder/'architecture.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads((folder/'config.json').read_text())['model_config']
    torch.set_num_threads(4)
    model = module.Model(config).cpu()
    model.load_state_dict(torch.load(folder/'weights.pth',map_location='cpu',weights_only=True))
    model.eval()
    _model = model, manifest
    return _model


def classify_level(score, duration, rms):
    if rms < .002:
        return 'unassessed'
    if duration < 3:
        return 'uncertain'
    return 'elevated' if score >= .75 else 'lower' if score < .35 else 'uncertain'


def screen_audio(path, digest, allowed_root):
    import numpy as np
    import torch
    start = time.monotonic()
    inspection = inspect_file(path,digest,allowed_root=allowed_root,output_dir=ROOT/'output')
    if inspection['status'] != 'completed':
        raise ValueError('Media inspection failed: '+inspection['status'])
    if not any(s.get('codec_type') == 'audio' for s in inspection['streams']):
        raise ValueError('This video has no audio track. Audio screening cannot detect visual manipulation. Choose a speech recording or a video with audio.')
    duration = float(inspection.get('durationSeconds') or 0)
    if not 0 < duration <= 120:
        raise ValueError('Choose a nonempty clip up to 120 seconds for this research screen.')
    executable = shutil.which('ffmpeg')
    if not executable:
        raise ValueError('ffmpeg is unavailable')
    demuxer = inspection['parser']['demuxer']
    with tempfile.TemporaryDirectory(dir=ROOT/'output') as temp:
        output = Path(temp)/'mono.f32'
        command = [executable,'-nostdin','-v','error','-protocol_whitelist','file','-format_whitelist',demuxer,
                   '-f',demuxer,'-i',str(path),'-map','0:a:0','-vn','-t','120.1','-ac','1','-ar','16000',
                   '-c:a','pcm_f32le','-f','f32le',str(output)]
        subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=25,
                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if output.stat().st_size > 120*16000*4:
            raise ValueError('Decoded audio exceeds 120 seconds')
        samples = np.fromfile(output,dtype='<f4')
    if samples.size < 1600 or not np.isfinite(samples).all():
        raise ValueError('Audio is empty, too short or contains nonfinite samples')
    after = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            after.update(chunk)
    if after.hexdigest() != digest:
        raise ValueError('Source bytes changed while decoding; no result retained')
    # Raw, measured min/max/RMS bins. Never use classifier scores as signal amplitudes.
    bins = []
    for part in np.array_split(samples,min(720,len(samples))):
        bins.append({'min':float(part.min()),'max':float(part.max()),'rms':float(np.sqrt(np.mean(part**2)))})
    model, manifest = load_model()
    window, hop = 64600, 32300
    starts = list(range(0,max(1,len(samples)-window+1),hop))
    if len(samples) > window and starts[-1] != len(samples)-window:
        starts.append(len(samples)-window)
    segments = []
    with torch.inference_mode():
        for index in starts:
            if time.monotonic()-start > 90:
                raise ValueError('Screen exceeded its processing budget; use a shorter clip')
            part = samples[index:index+window]
            length = len(part)/16000
            rms = float(np.sqrt(np.mean(part**2)))
            score = None
            if rms >= .002:
                padded = np.tile(part,math.ceil(window/len(part)))[:window].copy()
                _, logits = model(torch.from_numpy(padded).unsqueeze(0))
                score = float(torch.softmax(logits,dim=-1)[0,0])
                if not math.isfinite(score):
                    raise ValueError('Model returned a nonfinite score')
            segments.append({'startSeconds':index/16000,'endSeconds':(index+len(part))/16000,
                             'score':score,'level':classify_level(score or 0,length,rms),'rms':rms,
                             'shortInputRepeated':len(part)<window})
    return {'status':'completed','scope':'experimental-audio-only','visualAnalysis':False,'validated':False,
            'sha256':digest,'durationSeconds':len(samples)/16000,'sampleRate':16000,'bins':bins,'segments':segments,
            'model':{'name':'AASIST-L','revision':manifest['revision'],
                     'weightsSha256':next(f['sha256'] for f in manifest['files'] if f['file']=='weights.pth')},
            'windowSeconds':window/16000,'hopSeconds':hop/16000,'elapsedSeconds':round(time.monotonic()-start,3),
            'scoreMeaning':'Uncalibrated softmax spoof-class model output, not probability that media is fake.',
            'localValidationWarning':'Initial local smoke test over-flagged known natural Yesno speech. Do not use this baseline for authenticity decisions.',
            'thresholds':{'lowerBelow':.35,'elevatedAtLeast':.75,'calibrated':False},
            'limitations':['Audio only: no face, image or visual-video manipulation analysis.',
                'Pretrained on ASVspoof2019 LA; no local or cross-domain accuracy validation.',
                'Sliding clip-classifier windows are coarse screening, not validated edit-boundary localization.',
                'Green means lower model signal, not verified real. Red is a review cue, not proof of synthesis.',
                'Shorter than three seconds is amber regardless of score; quiet windows are gray and unassessed.',
                'Music, noise, language, codecs and unseen generators can cause false positives and missed detections.']}
