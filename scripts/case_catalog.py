"""Write the local case launcher and documented workflow coverage."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    {'id': 'DF-24-017', 'title': 'Northstar fictional investigation', 'folder': 'storage', 'coverage': 'Seeded graph relationships, review, timeline, agent memory, reports and synthetic tone.'},
    {'id': 'PUBLIC-NITROBA-2008', 'title': 'Nitroba forensic training case', 'folder': 'public/nitroba-2008', 'coverage': 'Scenario, PCAP intake, screenshots, hashes and image metadata. Packet interpretation is not implemented.'},
    {'id': 'PUBLIC-MEDIA-TESTS', 'title': 'Video, image and natural speech', 'folder': 'public/media-functional-pack', 'coverage': 'Four MP4/WebM videos, JPEG, six speech WAVs, codec inspection, audio playback and measured waveform.'},
    {'id': 'PUBLIC-DEEPFAKE-AUDIO', 'title': 'Published generated speech', 'folder': 'public/deepfake-audio', 'coverage': 'Three publisher-labeled MelGAN originals plus three PCM derivatives: intake, hashes, metadata, waveform, agents and cited reports. No local authenticity verdict.'},
]


def main():
    (ROOT / 'cases/index.json').write_text(json.dumps({'cases': CASES}, indent=2), encoding='utf-8')
    cards = ''.join(f'<article><h2>{html.escape(c["title"])}</h2><code>{c["id"]}</code><p>{html.escape(c["coverage"])}</p><a href="http://127.0.0.1:8100/?case={c["id"]}#evidence">Open evidence →</a> · <a href="http://127.0.0.1:8100/?case={c["id"]}#media">Media →</a> · <a href="http://127.0.0.1:8100/?case={c["id"]}#agents">Agents →</a></article>' for c in CASES)
    (ROOT / 'ui-prototype/cases.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forensic Atlas · Case library</title><style>body{margin:0;background:#e9edf0;color:#263448;font:16px system-ui;padding:clamp(20px,6vw,80px)}main{max-width:1050px;margin:auto}h1{font-size:40px;margin:10px 0}header p{max-width:750px;line-height:1.7;color:#526174}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin:30px 0}article{background:#f9fafb;border:1px solid #cad3db;border-radius:16px;padding:25px;box-shadow:0 8px 25px #24334908}h2{font-size:21px}p{line-height:1.7}a{color:#176c68;font-weight:600}a:focus-visible{outline:3px solid #179c91}code{font-size:12px;color:#64748b}aside{border-left:4px solid #c08a36;padding:5px 20px;background:#fff8e9}</style><main><header><small>FORENSIC ATLAS / LOCAL CASE LIBRARY</small><h1>Choose a test case</h1><p>Preserved sources, separate case records, and explicit expectations. Start the application, then choose a collection below. All samples are educational or research material.</p></header><section class="grid">''' + cards + '''</section><aside><strong>Coverage limits</strong><p>The installed model provides source-linked extractive summaries. Deepfake authenticity detection, speech transcription, PCAP interpretation and cloud acquisition are not implemented. A detector request must fail closed, never invent a score. Generated-speech labels come from the publisher; they are not analysis results.</p><p>Restricted deepfake video benchmarks require publisher access approval. The included animation videos test media workflows, not deepfake accuracy.</p></aside></main></html>''', encoding='utf-8')


if __name__ == '__main__':
    main()
