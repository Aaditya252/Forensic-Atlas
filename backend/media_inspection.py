"""Local byte integrity and bounded ffprobe metadata; no authenticity inference."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def inspect_file(path: Path, expected_sha256: str, *, allowed_root: Path, output_dir: Path) -> dict:
    path, allowed_root = path.resolve(), allowed_root.resolve()
    if not path.is_relative_to(allowed_root) or not path.is_file():
        raise ValueError("Stored media bytes are unavailable or outside the evidence directory.")
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as source:
        header = source.read(32)
        source.seek(0)
        for chunk in iter(lambda: source.read(1024*1024), b''):
            size += len(chunk)
            if size > 512*1024*1024:
                raise ValueError("Media inspection is limited to 512 MB.")
            digest.update(chunk)
    actual = digest.hexdigest()
    result = {"status":"integrity_checked", "sha256":actual, "registeredSha256":expected_sha256,
              "integrityMatch":actual==expected_sha256, "byteSize":size, "streams":[], "format":None,
              "durationSeconds":None, "detectorRun":False,
              "limitations":["Metadata and byte integrity do not establish media authenticity.",
                             "No deepfake model, face identification, transcription, or examiner decision is performed."]}
    if not result['integrityMatch']:
        return {**result, "status":"blocked", "error":{"code":"INTEGRITY_MISMATCH", "message":"Stored bytes differ from the registered digest. Metadata parsing was not run."}}
    # Signature-selected demuxers exclude playlists and URL-based input formats.
    demuxer = ('wav' if header[:4]==b'RIFF' and header[8:12]==b'WAVE' else
               'mov' if header[4:8]==b'ftyp' else 'matroska' if header[:4]==b'\x1aE\xdf\xa3' else
               'png_pipe' if header[:8]==b'\x89PNG\r\n\x1a\n' else 'jpeg_pipe' if header[:3]==b'\xff\xd8\xff' else None)
    if demuxer is None:
        return {**result,"status":"unsupported", "error":{"code":"UNSUPPORTED_MEDIA_SIGNATURE", "message":"This slice supports WAV, MP4/MOV with ftyp, Matroska/WebM, PNG, and JPEG signatures."}}
    executable = shutil.which('ffprobe')
    if not executable:
        return {**result,"status":"dependency_unavailable", "error":{"code":"FFPROBE_NOT_AVAILABLE", "message":"ffprobe is not installed on the API's PATH."}}
    output_dir.mkdir(parents=True,exist_ok=True)
    args = [executable,'-v','error','-protocol_whitelist','file','-format_whitelist',demuxer,'-f',demuxer,
            '-probesize','5242880','-analyzeduration','2000000','-show_entries',
            'format=format_name,duration:stream=index,codec_type,codec_name,width,height,sample_rate,channels,duration',
            '-of','json',str(path)]
    try:
        # Disk-backed output avoids an unbounded subprocess PIPE allocation.
        with tempfile.TemporaryFile(dir=output_dir) as output:
            process = subprocess.run(args, stdout=output, stderr=subprocess.DEVNULL, timeout=12,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), check=False)
            output.seek(0)
            raw = output.read(128*1024+1)
        if process.returncode or len(raw)>128*1024:
            raise ValueError('Probe failed or output exceeded limit')
        metadata = json.loads(raw)
        # Detect byte changes between the initial hash and parser completion.
        after = hashlib.sha256()
        after_size = 0
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024*1024), b''):
                after_size += len(chunk)
                if after_size > 512*1024*1024:
                    raise ValueError('File grew beyond inspection limit')
                after.update(chunk)
        if after.hexdigest() != actual:
            return {**result,"status":"blocked","integrityMatch":False,"error":{"code":"MEDIA_CHANGED_DURING_INSPECTION","message":"The file changed during inspection. Parsed metadata was discarded."}}
        streams = metadata.get('streams',[])
        if not isinstance(streams,list):
            raise ValueError('Invalid stream list')
        result.update(status='completed', format=metadata.get('format',{}).get('format_name'),
                      durationSeconds=metadata.get('format',{}).get('duration'),
                      streams=[{key:value for key,value in row.items() if key in {'index','codec_type','codec_name','width','height','sample_rate','channels','duration'}} for row in streams[:16] if isinstance(row,dict)],
                      parser={"name":"ffprobe","demuxer":demuxer,"timeoutSeconds":12,"maxStreamsReturned":16})
        return result
    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError):
        return {**result,"status":"failed", "error":{"code":"MEDIA_PROBE_FAILED", "message":"The bounded metadata parser could not inspect this file. No metadata was substituted."}}
