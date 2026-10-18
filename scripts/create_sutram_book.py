from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, Flowable,
                                KeepTogether, HRFlowable)
from reportlab.pdfgen.canvas import Canvas

OUT = Path('output/pdf/SUTRAM_Forensics_Architecture_and_Research_Design.pdf')
OUT.parent.mkdir(parents=True, exist_ok=True)
W, H = A4
NAVY = HexColor('#10243A')
INK = HexColor('#203247')
TEAL = HexColor('#087E8B')
MINT = HexColor('#D9F0EF')
PALE = HexColor('#F2F6F9')
GOLD = HexColor('#E6A23C')
MUTED = HexColor('#5C6B7A')
RED = HexColor('#B84A4A')
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='CoverTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=30, leading=34, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8))
styles.add(ParagraphStyle(name='CoverSub', parent=styles['Normal'], fontName='Helvetica', fontSize=13, leading=18, textColor=TEAL, spaceAfter=12))
styles.add(ParagraphStyle(name='PageTitleX', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=NAVY, spaceAfter=4))
styles.add(ParagraphStyle(name='Deck', parent=styles['Normal'], fontName='Helvetica', fontSize=9.2, leading=13, textColor=MUTED, spaceAfter=10))
styles.add(ParagraphStyle(name='H2x', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11.5, leading=14, textColor=TEAL, spaceBefore=6, spaceAfter=4))
styles.add(ParagraphStyle(name='BodyX', parent=styles['BodyText'], fontName='Helvetica', fontSize=8.6, leading=12, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name='SmallX', parent=styles['BodyText'], fontName='Helvetica', fontSize=7.4, leading=9.5, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name='TinyX', parent=styles['BodyText'], fontName='Helvetica', fontSize=6.6, leading=8, textColor=INK, spaceAfter=2))
styles.add(ParagraphStyle(name='CalloutX', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=8.5, leading=11.5, textColor=NAVY, spaceAfter=0))
styles.add(ParagraphStyle(name='TableHeadX', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=7.2, leading=8.5, textColor=WHITE, spaceAfter=0))
styles.add(ParagraphStyle(name='TableX', parent=styles['BodyText'], fontName='Helvetica', fontSize=7, leading=8.8, textColor=INK, spaceAfter=0))
styles.add(ParagraphStyle(name='RefX', parent=styles['BodyText'], fontName='Helvetica', fontSize=7, leading=9, textColor=INK, spaceAfter=3))

def P(txt, style='BodyX'):
    return Paragraph(txt, styles[style])

def bullets(items, small=False):
    st = 'SmallX' if small else 'BodyX'
    return [Paragraph('• ' + x, styles[st], bulletText=None) for x in items]

def box(text, bg=MINT, border=TEAL, width=175*mm, pad=7):
    t = Table([[P(text, 'CalloutX')]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),0.7,border),
        ('LEFTPADDING',(0,0),(-1,-1),pad),('RIGHTPADDING',(0,0),(-1,-1),pad),
        ('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
    ]))
    return t

class Diagram(Flowable):
    """Compact vector flow diagram. Each row contains equal-width labeled nodes."""
    def __init__(self, rows, width=175*mm, node_h=14*mm, gap=4*mm, height=None):
        super().__init__(); self.rows=rows; self.width=width; self.node_h=node_h; self.gap=gap
        self.row_gap=8*mm; self.height=height or len(rows)*node_h+(len(rows)-1)*self.row_gap
    def wrap(self, aw, ah): self.width=min(self.width,aw); return self.width,self.height
    def draw(self):
        c=self.canv; nrows=len(self.rows); total_h=self.height
        y=total_h-self.node_h
        for ri,row in enumerate(self.rows):
            n=len(row); node_w=(self.width-(n-1)*self.gap)/n
            for i,label in enumerate(row):
                x=i*(node_w+self.gap)
                c.setFillColor([PALE,MINT,HexColor('#FFF2D7')][ri%3]); c.setStrokeColor(TEAL if ri%3!=2 else GOLD)
                c.roundRect(x,y,node_w,self.node_h,4,fill=1,stroke=1)
                c.setFillColor(INK); c.setFont('Helvetica-Bold',7.2)
                words=label.split('|')
                if len(words)==1: c.drawCentredString(x+node_w/2,y+self.node_h/2-2.5,words[0])
                else:
                    c.setFont('Helvetica-Bold',6.8)
                    c.drawCentredString(x+node_w/2,y+self.node_h/2+1.5,words[0])
                    c.setFont('Helvetica',6.4); c.drawCentredString(x+node_w/2,y+self.node_h/2-5.5,words[1])
                if i<n-1:
                    c.setStrokeColor(TEAL); c.setLineWidth(1); c.line(x+node_w+1,y+self.node_h/2,x+node_w+self.gap-1,y+self.node_h/2)
                    c.line(x+node_w+self.gap-1,y+self.node_h/2,x+node_w+self.gap-3,y+self.node_h/2+2)
                    c.line(x+node_w+self.gap-1,y+self.node_h/2,x+node_w+self.gap-3,y+self.node_h/2-2)
            if ri<nrows-1:
                c.setStrokeColor(MUTED); c.setDash(2,2); c.line(self.width/2,y-1,self.width/2,y-self.row_gap+1); c.setDash()
            y-=self.node_h+self.row_gap

class BookDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=24*mm, bottomMargin=16*mm,
                         title='SUTRAM: Digital Forensics Architecture and Research Design', author='Research and Architecture Brief')
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='book',frames=frame,onPage=self.decorate)])
    def decorate(self, canvas, doc):
        canvas.saveState()
        page=doc.page
        if page>1:
            canvas.setFillColor(NAVY); canvas.rect(0,H-12*mm,W,12*mm,fill=1,stroke=0)
            canvas.setFillColor(WHITE); canvas.setFont('Helvetica-Bold',7.4); canvas.drawString(18*mm,H-7.8*mm,'SUTRAM  /  DIGITAL FORENSICS SYSTEM DESIGN')
            canvas.setFillColor(TEAL); canvas.rect(18*mm,10*mm,12*mm,1.2*mm,fill=1,stroke=0)
            canvas.setFillColor(MUTED); canvas.setFont('Helvetica',7); canvas.drawRightString(W-18*mm,10*mm,f'{page:02d}  /  15')
        canvas.restoreState()

def page(title, deck, *content):
    return [P(title,'PageTitleX'), P(deck,'Deck'), HRFlowable(width='100%',thickness=0.7,color=HexColor('#D7E1E9'),spaceAfter=8)] + list(content)

def table(headers, rows, widths, font='TableX'):
    data=[[P(h,'TableHeadX') for h in headers]]
    data += [[P(str(c),font) for c in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),0.35,HexColor('#CBD6DF')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,PALE]),
    ])); return t

pages=[]

# 1 — cover
pages.append([
    Spacer(1,17*mm), P('SUTRAM','CoverSub'),
    P('A forensic platform\narchitecture & research design','CoverTitle'),
    P('A 15-page engineering blueprint for evidence acquisition, analysis, trustworthy automation, and operational scale.','CoverSub'),
    Spacer(1,7*mm),
    Diagram([['COLLECT|preserve','PARSE|validate','CORRELATE|qualify'],['STORE|trace','ANALYZE|assist','REPORT|review']],width=175*mm,node_h=19*mm,gap=5*mm,height=50*mm),
    Spacer(1,9*mm),
    box('<b>Design premise</b>  Evidence is the source of truth. Every transformation, inference, model output, and report claim must remain traceable to source artifacts and reproducible tool versions.',bg=HexColor('#EAF3F8'),border=TEAL),
    Spacer(1,13*mm),
    P('Prepared from the Cybersecurity folder engineering matrix, blackholes brief, consolidated research map, the supplied Claude conversation, and the referenced digital-forensics literature.','SmallX'),
    P('Architecture proposal • research connections • validation roadmap • October 2026','SmallX'),
])

# 2
pages.append(page('1. Executive blueprint','A proposed system design, grounded in the supplied SUTRAM materials and linked to research where it can inform implementation.',
    P('SUTRAM should be built as an evidence-centered platform: ingest heterogeneous digital artifacts, preserve originals, produce validated normalized records, correlate them with explicit uncertainty, then help an investigator form and report testable claims. Automation accelerates triage; it does not replace evidentiary judgment.'),
    Diagram([['Evidence sources|disk • memory • cloud','Ingestion gateway|identity • limits','Acquisition jobs|async • progress'],['Original vault|immutable object','Evidence registry|PostgreSQL','Analysis services|parsers • rules • ML'],['Case workspace|timeline • graph','Investigator review|claim-level','Export package|provenance • audit']],node_h=13*mm),
    P('System invariants','H2x'),
    *bullets(['Keep original bytes immutable; record hash algorithm, digest, acquisition time, tool/version, operator or service identity, and source context. A matching hash supports integrity since capture; it does not establish that the source was authentic before capture. [1, 2]','Keep raw timestamps and raw values alongside normalized values. Record timezone assumptions, clock uncertainty, parser version, and transformation history.','Make AI outputs advisory and attributable: model/version, input artifact IDs, confidence/calibration context, explanation, limitations, and human disposition.','Separate system-of-record data from derived indexes and caches. Rebuild derived stores from durable evidence and event records.']),
    box('<b>Corrections carried forward:</b> the “120 problems” matrix sums to 124 entries (its AI/ML section has 14). The consolidated map includes BH-13–17 summarized from an external report; BH-13 and BH-17 overlap around silent or semantically incomplete parsing. Treat these as source-document accounting notes, not established novelty claims.',bg=HexColor('#FFF2D7'),border=GOLD),
    P('Scope boundary','H2x'),
    P('This blueprint proposes components and measurable gates. It does not claim that SUTRAM already implements them, nor that product comparisons, dataset scores, or latency figures have been measured. Cloud, IoT, deepfake, and tool-testing literature are used to shape requirements and evaluation—not to assert that one product solves every domain. [3–8]')
))

# 3
pages.append(page('2. Layered architecture','Define stable boundaries so acquisition, analysis, storage, and user-facing workflows can evolve independently.',
    Diagram([['1 Sources|devices • cloud','2 Edge gateway|auth • validation','3 Job control|queue • state'],['4 Acquisition|adapters • capture','5 Evidence core|vault • registry','6 Analysis|parse • correlate • ML'],['7 Case services|timeline • graph','8 Presentation|review • export','9 Governance|policy • audit']],node_h=15*mm,gap=4*mm),
    table(['Layer','Owns','Boundary / contract'],[
        ('Source adapters','Connectors and collection plans','Read scoped sources; capture source identifiers, permissions, time window, and acquisition method.'),
        ('Gateway & orchestration','Identity, quotas, job lifecycle','Accept validated requests; issue job IDs; never parse large evidence in the request thread.'),
        ('Evidence core','Original objects, registry, custody','Write once originals; append-only custody events; derived data points back to evidence IDs.'),
        ('Analysis services','Parsers, rules, ML, correlation','Versioned, isolated, retryable jobs; outputs include coverage and warnings.'),
        ('Case services','Search, timeline, graph, reports','Case-scoped access; distinguish observed facts from inferred relationships.'),
        ('Governance & operations','Policy, audit, monitoring, recovery','Authorization, privacy controls, service health, retention, restore evidence.')], [31*mm,43*mm,101*mm]),
    P('Research connection','H2x'),
    P('Cloud forensics and readiness work supports explicit source and collection boundaries: cloud evidence is distributed across tenants, providers, logs, and retention windows. IoT surveys reinforce source heterogeneity, privacy constraints, and dependence on what the device or service actually exposes. This argues for adapters with declared coverage, not a universal “collect everything” abstraction. [1, 3–5]'),
    box('<b>Interface rule:</b> every service consumes stable artifact/job IDs and emits versioned records plus an explicit status: complete, partial, failed, skipped, or unsupported. “No findings” must never silently mean “no data.”')
))

# 4
pages.append(page('3. Acquisition & evidence coverage','Capture enough context to reproduce what was collected, from where, when, how, and with what known omissions.',
    Diagram([['Authorize|case • scope','Plan|source • window','Acquire|adapter • tool'],['Preserve|original bytes','Verify|hash • metadata','Register|custody event'],['Assess coverage|expected vs found','Queue analysis|versioned job','Review gaps|investigator']],node_h=14*mm),
    P('Acquisition record minimum','H2x'),
    table(['Record group','Fields / behavior'],[
        ('Identity & authority','Case ID; requesting principal; approved source scope; legal/organizational authority reference; provider/account/device identifiers; access mode.'),
        ('Collection context','Start/end time; source timezone or UTC offset; tool and version; adapter build; query/filters; collection status; errors and provider response IDs.'),
        ('Artifact custody','Stable artifact ID; original object URI; byte length; media/format hint; SHA-256 (plus algorithm field); acquisition time; collector identity; parent/derived relation.'),
        ('Coverage declaration','Expected artifact classes; observed classes; inaccessible/expired/unsupported items; pagination/retention limits; known blind spots and completeness status.')], [36*mm,139*mm]),
    P('Operational behavior','H2x'),
    *bullets(['Use resumable, chunked, idempotent collection where source APIs support it; retain page tokens or offsets securely and record retries.','Treat live collection as an operation that can alter state. Record that risk, the collection method, and before/after observations where available. [9]','Cloud evidence often expires or changes under retention policy. Capture time-sensitive metadata early and preserve the provider’s scope and response, while making no claim about unavailable plaintext. [1, 3, 4]','Do not represent a source account or device as a person. Preserve identifiers and confidence separately; attribution requires contextual evidence and review.']),
    box('<b>Key acceptance gate:</b> for a seeded case manifest, every expected item is accounted for as acquired, inaccessible, not present, filtered by policy, or unsupported. The manifest and resulting custody events must reconcile exactly.')
))

# 5
pages.append(page('4. Storage, database & provenance','Use PostgreSQL as the durable relational system of record, object storage for original bytes, and an optional graph projection for relationship exploration.',
    Diagram([['Original vault|immutable blobs','PostgreSQL|registry • custody • cases','Derived graph|FalkorDB optional'],['Evidence IDs|content digests','Events|append-only audit','Projection|rebuildable edges']],node_h=15*mm),
    table(['Store','Role','Design decision'],[
        ('Object store / evidence vault','Original source bytes and acquired exports','Versioning or retention lock where supported; encryption at rest; object digest verification; access through case-aware service.'),
        ('PostgreSQL','Case, artifact, acquisition, parser-run, entity, claim, audit, and report registry','Source of truth. Use foreign keys, uniqueness/idempotency keys, transactions, migrations, and least-privilege roles.'),
        ('FalkorDB (optional)','Derived graph for multi-hop relationships and investigation pivots','Not a relational database. Treat as a query projection; each node/edge carries evidence IDs, observed/inferred type, source, and derivation version.'),
        ('Search/cache','Fast lookup and UI acceleration','Disposable and rebuildable. Do not make a cache or search index the sole custody record.')], [30*mm,52*mm,93*mm]),
    P('Core relational entities','H2x'),
    P('<b>Case → Acquisition → Artifact → ParserRun → Observation → Claim → Report</b>. Add Source, ToolBuild, ModelBuild, CustodyEvent, AccessEvent, and ReviewDecision. Model raw and normalized values side by side; store record-level provenance and stable references to source byte ranges or event IDs where possible.'),
    box('<b>Graph safety:</b> represent “account linked to device” separately from “person used device.” Store the evidence basis and relationship class. A chain of graph edges is a lead, not proof of causality or identity. Rebuild graph projections from PostgreSQL and original evidence metadata.'),
    P('Research connection','H2x'),
    P('Blockchain-forensics literature can inform tamper-evident event design and shared custody workflows, but a ledger cannot prove that the initial capture was true, complete, or lawfully obtained. Start with signed/append-only audit events and independently tested backup/restore. Apply a distributed ledger only when multiple parties need a shared trust model. [5]'),
    P('FalkorDB’s current public project describes a graph database and its core repository uses SSPLv1; validate license compatibility, persistence mode, crash recovery, and workload fit before adoption. Benchmark it against PostgreSQL recursive queries on SUTRAM’s real query patterns. [17]','SmallX')
))

# 6
pages.append(page('5. Parsing, normalization & failure detection','Parser correctness is an evidence-quality problem: detect silent omission and meaning changes before records reach timelines, graphs, or models.',
    Diagram([['Identify format|safe sniff','Parse|sandboxed adapter','Validate|schema • counts'],['Preserve raw|bytes • fields','Normalize|canonical schema','Compare coverage|expected • actual'],['Pass|version • warnings','Partial|review queue','Fail|retain input • reason']],node_h=14*mm),
    P('Build a canonical evidence envelope','H2x'),
    P('Every normalized observation should retain: artifact ID; source-native record ID; parser and schema version; raw field/value snapshot or byte range; normalized field/value; time value plus raw representation and timezone basis; extraction status; confidence or ambiguity; and warnings. Keep source-specific extensions rather than discarding fields that the common schema cannot represent.'),
    table(['Failure mode','Detector / response'],[
        ('Format misidentification','Magic bytes plus parser probing; reject ambiguous or unsupported formats into a visible queue.'),
        ('Silent truncation / dropped records','Compare record counts, pagination totals, byte ranges, known sentinels, and parser diagnostics against source-level expectations.'),
        ('Semantic field drift','Versioned fixtures for timezone, unit, enum, encoding, and nested-field edge cases; alert on unexplained distribution shifts.'),
        ('Malformed or hostile input','Resource limits, isolated parser process, timeouts, memory caps, recursion limits, dependency pinning, and preserved crash context.'),
        ('Partial success hidden as success','Return coverage metrics and a typed partial status; downstream services must propagate the limitation.')], [43*mm,132*mm]),
    P('Priority prototype: parser failure detector','H2x'),
    P('The Claude conversation proposed beginning here because it has clearer ground truth than broad autonomous “AI for forensics.” Build a labeled corpus of valid, malformed, truncated, version-shifted, and adversarial samples. Compare source totals and known fields with parsed outputs. Measure missed failure rate, false alarms, field-level coverage, and version-to-version regressions. Merge the overlapping BH-13/BH-17 ideas into one research question: <i>when does a parser silently omit or alter meaning, and how can the pipeline detect it?</i>'),
    box('<b>Gate:</b> a parser cannot emit “complete” when source counts, fixture assertions, or mandatory field checks fail. “Partial” preserves usable records while carrying visible coverage warnings.')
))

# 7
pages.append(page('6. Agents & orchestration','Treat agents as bounded, auditable workflow workers—not autonomous investigators with authority to alter evidence or decide guilt.',
    Diagram([['Case Orchestrator|policy • state','Acquisition Agent|scoped connector','Parser Agent|isolated • versioned'],['Validation Agent|coverage • integrity','Analysis Agent|rules • ML assist','Report Agent|citations • export']],node_h=16*mm),
    table(['Worker','Allowed responsibility','Must not do'],[
        ('Acquisition worker','Execute an approved collection plan; report source responses, errors, and coverage.','Expand scope, retry indefinitely, or overwrite original artifacts.'),
        ('Parser worker','Run a pinned adapter; emit normalized observations and warnings.','Hide malformed records or rewrite original bytes.'),
        ('Validation worker','Check hashes, record counts, schema, provenance completeness, and known test vectors.','Convert a failed check into a clean pass without a recorded exception.'),
        ('Analysis worker','Run deterministic rules or approved models; attach evidence references and calibrated limits.','Assert identity, intent, or causality from a model score alone.'),
        ('Report worker','Draft a reproducible report from reviewed claims and linked evidence.','Invent unsupported facts or omit contradictory evidence.')], [32*mm,73*mm,70*mm]),
    P('Orchestration state machine','H2x'),
    P('Use explicit states: <b>requested → authorized → queued → running → partial/complete/failed → reviewed → exported</b>. Persist transitions and the actor/service, timestamp, reason, and input/output IDs. Retries must be idempotent; cancellation must stop work safely and leave a recoverable state. Human approval is required for scope changes, high-impact inferences, and final report release.'),
    P('Research connection','H2x'),
    P('Cloud forensic readiness work supports preparation before an incident: known sources, roles, retention, collection playbooks, and auditability. The cloud log-forensics literature informs the worker model for provider logs, while ML-forensics surveys caution that automation quality depends on data, reproducibility, and validation. [3, 4, 6]'),
    box('<b>Agent policy:</b> tools receive short-lived credentials scoped to one case/job and only the necessary source. Evidence writes are append-only; model or report workers cannot mutate custody records.')
))

# 8
pages.append(page('7. Correlation, graph & timeline','Correlate events by explicit rules and preserve uncertainty, source dependence, clock quality, and alternative explanations.',
    Diagram([['Observations|source records','Normalize|entities • time','Correlate|rules • graph'],['Candidate link|basis + score','Timeline|raw + normalized','Investigator|confirm • reject']],node_h=15*mm),
    P('Correlation contract','H2x'),
    *bullets(['Each candidate relationship stores its rule/model version, matched fields, time window, source IDs, confidence/calibration context, and whether it is observed or inferred.','Model people, devices, accounts, sessions, processes, files, and network endpoints as distinct entity types. Link them only with explicit evidence-backed relations.','Retain raw timestamps, normalized UTC, source offset, precision, clock-health notes, and ordering uncertainty. Do not turn timestamp sorting into a claim of causation.','Track source dependency: multiple records copied from one upstream log are not independent corroboration. Store parent/source lineage and count independent sources cautiously.','Show missing records as a coverage question. Absence is informative only where collection completeness, retention, and expected logging behavior are established.']),
    table(['Threat to interpretation','Product control'],[
        ('Clock drift / manipulated timestamps','Surface raw and normalized time together; annotate source reliability and time uncertainty.'),
        ('False corroboration','Lineage-aware source grouping; explain shared upstream source.'),
        ('Correlation mistaken for cause','Label candidate edges and timeline sequences; require analyst rationale before causal wording.'),
        ('Identity overreach','Separate account/device/person; require multiple contextual evidence classes and human review.'),
        ('Tool disagreement','Preserve each tool’s output and version; compare against known ground truth and document adjudication.')], [54*mm,121*mm]),
    P('Research connection','H2x'),
    P('Network-forensics surveys help define packet/session metadata and analysis taxonomy; cloud-log research highlights event provenance and heterogeneous logs. Neither makes temporal proximity sufficient for attribution. Use these sources to shape schemas and validation questions. [4, 10, 11]'),
    box('<b>Graph discipline:</b> query paths should return the evidence that supports every edge. Distinguish “observed together,” “same identifier,” “probable relation,” and “human-assessed conclusion.”')
))

# 9
pages.append(page('8. ML, media & deepfake analysis','A defensible ML pipeline reports what the model saw, what it predicted, how uncertain it is, and when it should abstain.',
    Diagram([['Input media|hash • metadata','Preflight|format • quality','Model set|versioned'],['Scores|calibration • OOD','Explanation|regions • cues','Human review|context • decision']],node_h=14*mm),
    P('Pipeline and evidence record','H2x'),
    *bullets(['Preserve the original media and derive separate analysis copies. Record decode/transcode operations, frame sampling, audio extraction, resizing, and codec details.','Log model family/version, weights digest, threshold, preprocessing, runtime/hardware, dataset/version, and full input artifact linkage.','Return calibrated score ranges where supported, out-of-distribution or low-quality flags, abstention state, and competing model results. Avoid presenting a probability as courtroom certainty.','Make explanations inspectable: frame/time ranges, salient regions or cues, rationale text tied to observable features, and known failure conditions. Explanations are aids, not proof.','Evaluate across compression, edits, crops, diverse identities, sources, languages, and unseen generation methods; guard against dataset leakage and train/test contamination.']),
    table(['Research / resource','SUTRAM connection'],[
        ('FaceForensics++ [7]','Benchmark design and manipulated-media baselines; document dataset artifacts and test generalization.'),
        ('Celeb-DF [8]','Challenging face-manipulation evaluation; avoid reporting a single-dataset result as deployment reliability.'),
        ('Multimodal deepfake survey [9]','Media pipeline scope across audio, video, and cross-modal consistency; use to structure coverage.'),
        ('Explainable detection framework [10]','Human-readable rationale design; require reviewer interpretation and evidence linking.'),
        ('ML in digital forensics review [6]','Research map for automation tasks, validation gaps, and reproducible evaluation.')], [54*mm,121*mm]),
    box('<b>Decision rule:</b> show “inconclusive / abstain” when input quality, domain shift, or calibration is inadequate. Keep detection output separate from authenticity conclusions and investigator findings.',bg=HexColor('#FFF2D7'),border=GOLD),
    P('NIST AI RMF can structure governance, measurement, and monitoring; it does not certify that a particular detector is forensically valid. [15]','SmallX')
))

# 10
pages.append(page('9. High-performance gateways','Keep request handling short and predictable; move evidence transfer, parsing, and model inference into bounded background jobs.',
    Diagram([['Client|token • case','Gateway|auth • schema','Policy|scope • quota'],['Upload|stream • checksum','Queue|durable job ID','Workers|bounded pools'],['Status API|progress • retry','Evidence core|commit','Events|audit • metrics']],node_h=14*mm),
    P('Gateway design','H2x'),
    *bullets(['Use asynchronous API endpoints for job submission and status; validate metadata and authorization before accepting payloads. Stream large objects to controlled storage with size/type limits and server-side digest computation.','Apply per-tenant/case quotas, rate limits, concurrency ceilings, idempotency keys, upload timeouts, and backpressure. Return a job ID and status URL instead of waiting for parsing or inference.','Separate latency-sensitive interactive queries from bulk acquisition and CPU/GPU-heavy analysis. Use independent worker pools, queue priorities, and cancellation.','Use bounded retries with exponential backoff and dead-letter handling; preserve partial progress and make duplicate submissions safe.','Track request and end-to-end job latency separately. Define targets only after workload baselines; report p50/p95/p99, throughput, error rate, queue wait, bytes/sec, CPU/memory, and accuracy/coverage tradeoffs.']),
    table(['Path','Expected behavior','Measure'],[
        ('Interactive API','Auth + validation + durable job acceptance; no heavy evidence parsing inline.','p50/p95/p99 acceptance latency; 4xx/5xx; throttles.'),
        ('Bulk evidence','Chunked transfer, resumable where possible, checksum at commit.','Throughput; retry rate; integrity mismatch; queue depth.'),
        ('Analysis workers','Scale by task type and resource; strict per-job limits.','Records/sec; CPU/GPU; memory; timeout; completion/partial rates.'),
        ('Case search','Indexes/graph projections with bounded result sizes.','Query latency; freshness lag; source lineage returned.')], [34*mm,85*mm,56*mm]),
    P('No invented performance claims','H2x'),
    P('This design makes no throughput or latency guarantee. Set service-level objectives from representative evidence sizes, concurrency, parser mix, and deployment hardware. Benchmark the complete path—including queueing, object I/O, database commits, and result rendering—then publish the conditions with every number.'),
    box('<b>Safety meets performance:</b> input limits, sandboxing, and audit writes are part of the gateway budget. Optimize streaming, batching, and indexes; do not bypass validation or provenance to improve a benchmark.')
))

# 11
pages.append(page('10. Security, privacy & adversarial evidence','Evidence files, metadata, prompts, provider logs, and analysis outputs are all untrusted inputs until validated.',
    table(['Threat','Controls'],[
        ('Malicious file/parser exploit','Sandbox parser workers; pin dependencies; disable unnecessary network; impose CPU/memory/time/file-size limits; isolate temporary storage.'),
        ('Unauthorized collection or case access','Case-scoped RBAC/ABAC; least privilege; short-lived credentials; dual control for scope changes; access review.'),
        ('Prompt injection in evidence','Treat extracted text as data, not instructions; isolate model tools; no tool invocation from artifact text; preserve prompt/model input provenance.'),
        ('Sensitive data leakage to external ML','Default local/offline processing for sensitive cases; explicit approved egress policy; redact only on derived copies; log any export.'),
        ('Tampering, deletion, ransomware','Immutable/versioned originals; append-only audit; separated backup credentials; tested recovery; integrity verification.'),
        ('Over-retention / privacy intrusion','Purpose and scope limits; collection minimization; retention schedule; deletion/hold workflow; jurisdiction and provider constraints review.')], [51*mm,124*mm]),
    P('Investigator safeguards','H2x'),
    *bullets(['Never claim encrypted content was recovered unless the evidence actually contains recoverable plaintext; record access constraints and cryptographic state.','Record privacy/legal scope as case policy metadata and enforce it in connectors, queries, exports, and model selection. IoT and cloud collections may cross organizational or jurisdictional boundaries. [1, 3]','Separate evidence facts from analyst interpretation and generated narrative. Reports should show the provenance chain and contradictory evidence.','Treat blockchain as an integrity/audit mechanism with limits, not as a substitute for source authenticity, authorization, or secure key management. [5]']),
    P('Validation references','H2x'),
    P('Use NIST scientific-foundation and tool-testing resources to structure reliability claims, test procedures, and repeatability. Use SWGDE guidance as a living reference set for procedures and reporting expectations; confirm current document versions before operational adoption. [12, 13, 16]'),
    box('<b>Release gate:</b> no connector or model goes live until its permissions, data flow, failure modes, retention behavior, audit trail, and evidence-handling limitations are documented and reviewed.')
))

# 12
pages.append(page('11. Infrastructure & operations','Choose deployment modes that preserve evidence custody while accommodating local, offline, and controlled cloud environments.',
    Diagram([['Web/API|TLS • identity','Control plane|policy • jobs','Worker pools|parse • ML'],['PostgreSQL|durable registry','Object storage|encrypted originals','Graph/search|derived views'],['Metrics/logs|redacted','Backup vault|separate keys','Recovery|verified restore']],node_h=14*mm),
    table(['Concern','Baseline design'],[
        ('Packaging','Containerized services with pinned images and software bill of materials; separate API, orchestration, parser, ML, and reporting workers.'),
        ('Network zones','Public ingress only to gateway; private data plane for stores/workers; egress deny-by-default for evidence-processing zones.'),
        ('Secrets & encryption','KMS-backed or platform-managed encryption; short-lived secrets; rotation; no credentials in logs or job payloads.'),
        ('Observability','Correlate trace ID, case/job/artifact IDs with restricted access; redact content and secrets. Monitor queue lag, worker failures, storage integrity, and database health.'),
        ('Backup & recovery','Independent backups for database and original object store; documented recovery-point/time objectives; scheduled restore drills with hash and registry reconciliation.'),
        ('Modes','Online controlled deployment for managed integrations; offline/local mode for restricted evidence. Make external model/API access a separate, explicit capability.')], [37*mm,138*mm]),
    P('Operational status vocabulary','H2x'),
    P('The UI and API should distinguish healthy, degraded, delayed, partial, and unavailable states. Display data freshness and source-coverage limits. A successful job means the declared work completed; it does not mean the data is complete or the resulting inference is correct.'),
    P('Research connection','H2x'),
    P('Cloud forensic readiness emphasizes planning, evidence retention, access, and organizational response before an incident. Apply it to runbooks, retention discovery, permissions, and provider escalation paths. [3, 4]'),
    box('<b>Recovery proof:</b> after restore, verify original-object hashes, artifact registry references, custody event continuity, and derived-index rebuild status. Record the drill outcome and any unresolved gap.')
))

# 13
pages.append(page('12. Research-to-layer connection map','Use papers to justify requirements and design experiments. Each connection below is a research-informed application, not a claim that the paper tested SUTRAM.',
    table(['Research source','System layer','Practical use in SUTRAM'],[
        ('Cloud Forensics [1]; cloud log review [4]','Cloud connectors, evidence registry, timelines','Capture provider/source metadata, time windows, retention gaps, log lineage, and collection completeness.'),
        ('Cloud forensic readiness [3]','Policy, operations, gateway','Prepare roles, source inventories, access paths, retention playbooks, and incident-time collection procedures.'),
        ('IoT forensics survey [2]','Source adapters, privacy controls','Design heterogeneous adapters, scoped acquisition, device context, and explicit legal/privacy constraints.'),
        ('Blockchain IoT-forensics review [5]','Custody and audit','Compare append-only signed event logs with ledger-based sharing; test what integrity does and does not establish.'),
        ('ML digital-forensics SLR [6]','Analysis pipeline, validation','Select narrow ML tasks, identify reproducibility gaps, define held-out test sets and human review.'),
        ('FaceForensics++ [7]; Celeb-DF [8]','Media pipeline','Build manipulated-media benchmarks; test cross-dataset and degraded-media performance.'),
        ('Deepfake survey [9]; explainable detection [10]','ML explanation and report','Structure multimodal test coverage and human-readable rationale linked to time/frame regions.'),
        ('NIST CFTT [12]; scientific foundation review [13]','Parser/tool QA and reporting','Use documented test plans, known-answer fixtures, repeatability, tool-version records, and bounded claims.'),
        ('Packet-analysis survey [11]; network-forensics review [14]','Network ingestion/correlation','Define packet/session features, analysis taxonomy, and provenance-preserving network workflows.'),
        ('NIST AI RMF [15]; SWGDE [16]','Governance and lifecycle','Organize risk measurement, monitoring, validation, procedure review, and reporting practices.')], [47*mm,43*mm,85*mm]),
    Spacer(1,5),
    box('<b>How to apply the literature:</b> convert each relevant finding into a requirement, test fixture, threat scenario, or evaluation metric. Record dataset/tool versions and limitations. Do not cite a survey as proof that a specific implementation is accurate.'),
    P('Reference numbers resolve to the compact bibliography on page 15. Research scope spans cloud, IoT, machine learning, multimedia, network, and forensic tool validation.','SmallX')
))

# 14
pages.append(page('13. Build & validation roadmap','Prioritize work with measurable ground truth and evidence-quality impact; scale only after the core provenance loop is reliable.',
    table(['Phase','Deliverable','Exit criteria'],[
        ('0 — Foundations','Threat model; case/artifact schema; source coverage manifests; immutable object-store path; custody events.','Hash and metadata reconcile end to end; access and audit controls exercised; recovery drill passes.'),
        ('1 — Parser trust','Versioned parser adapters; canonical evidence envelope; parser-failure detector for truncation and semantic drift.','Known-answer and malformed corpus; coverage/error metrics; no silent success on failed checks.'),
        ('2 — Investigator workflow','Case search, timeline with raw/normalized time, claim review, reproducible report export.','Each displayed event links to source; partial/missing data visible; reviewer decisions recorded.'),
        ('3 — Correlation','Rule-based entity resolution; optional graph projection; source-dependency and observed/inferred labels.','Ground-truth precision/recall by relation; false-corroboration and identity-overreach checks.'),
        ('4 — ML/media','Narrowly scoped models, deepfake benchmarks, calibrated abstention, reviewer-facing explanations.','Cross-dataset evaluation; subgroup and quality analysis; human review study; traceable model outputs.'),
        ('5 — Scale & readiness','Gateway/queue tuning, cloud/IoT source playbooks, offline mode, operating procedures.','Representative p95/p99 and throughput benchmarks with stated hardware/data; retry/recovery and privacy review.')], [32*mm,70*mm,73*mm]),
    P('Scorecard to publish','H2x'),
    P('<b>Evidence:</b> hash reconciliation, custody completeness, source coverage, parser field/count coverage, reproducibility.<br/><b>Analysis:</b> false-positive/negative rates, calibration, OOD/abstention quality, error slices, analyst agreement.<br/><b>Operations:</b> acceptance latency and job p50/p95/p99, throughput, queue delay, failure/retry rate, recovery objectives.<br/><b>Governance:</b> unauthorized access tests, privacy scope adherence, audit completeness, retention compliance.'),
    box('<b>First vertical slice:</b> one source adapter → immutable artifact → custody registry → parser with coverage checks → timeline entry → reviewer confirmation → evidence-linked export. Prove this loop before adding broad autonomous agents.'),
    P('The source blackholes list is a hypothesis backlog, not a validated defect catalog. Prioritize BH-13/BH-17-style parser coverage first; later test source dependency, absent-record interpretation, prompt injection, recovery context, tool disagreement, and investigator review history with specific datasets and procedures.')
))

# 15 references
refs=[
('1','Ruan, C., Carthy, J., Kechadi, T., & Crosbie, M. “Cloud Forensics.” IFIP Advances in Information and Communication Technology, 2011.','https://opendl.ifip-tc6.org/db/conf/ifip11-9/df2011/RuanCKC11.pdf'),
('2','“A Survey on the Internet of Things (IoT) Forensics: Challenges, Approaches, and Open Issues.” IEEE Communications Surveys & Tutorials, 2020.','https://doi.org/10.1109/COMST.2019.2962586'),
('3','“A Framework for Cloud Forensic Readiness in Organizations.” 2017.','https://doi.org/10.1109/MobileCloud.2017.12'),
('4','Ghosh, S., De, S., & Majumder, K. “A Systematic Review of Log-Based Cloud Forensics.” 2021.','https://doi.org/10.1007/978-981-33-4305-4_26'),
('5','“A Systematic Literature Review of Blockchain-Based IoT Forensic Investigation Process Models.” 2022.','https://doi.org/10.1016/j.fsidi.2022.301470'),
('6','Nayerifard, R. et al. “Machine Learning in Digital Forensics: A Systematic Literature Review.” 2023.','https://arxiv.org/abs/2306.04965'),
('7','Rössler, A. et al. “FaceForensics++: Learning to Detect Manipulated Facial Images.” ICCV, 2019.','https://openaccess.thecvf.com/content_ICCV_2019/papers/Rossler_FaceForensics_Learning_to_Detect_Manipulated_Facial_Images_ICCV_2019_paper.pdf'),
('8','Li, Y. et al. “Celeb-DF: A Large-Scale Challenging Dataset for DeepFake Forensics.” CVPR, 2020.','https://openaccess.thecvf.com/content_CVPR_2020/html/Li_Celeb-DF_A_Large-Scale_Challenging_Dataset_for_DeepFake_Forensics_CVPR_2020_paper.html'),
('9','Qureshi, A. et al. “Deepfake forensics: a survey of digital forensic methods for multimodal deepfake identification on social media.” PeerJ Computer Science, 2024.','https://peerj.com/articles/cs-2037/'),
('10','Bharati, A. et al. “Explainable deepfake detection: A multi-model framework with human-interpretable rationales for legal investigation purposes.” Machine Learning with Applications, 2026.','https://doi.org/10.1016/j.mlwa.2025.100819'),
('11','Sikos, L. F. “Packet analysis for network forensics: A comprehensive survey.” Forensic Science International: Digital Investigation, 2020.','https://doi.org/10.1016/j.fsidi.2019.200892'),
('12','Lyle, J., Guttman, B., & Ayers, R. “Ten years of computer forensic tool testing.” NIST, 2011.','https://www.nist.gov/publications/ten-years-computer-forensic-tool-testing'),
('13','NIST. “Digital Investigation Techniques: A NIST Scientific Foundation Review.”','https://www.nist.gov/publications/digital-investigation-techniques-nist-scientific-foundation-review'),
('14','“Network forensics: Review, taxonomy, and open challenges.” Journal of Network and Computer Applications, 2016.','https://doi.org/10.1016/j.jnca.2016.03.005'),
('15','NIST. Artificial Intelligence Risk Management Framework.','https://www.nist.gov/itl/ai-risk-management-framework'),
('16','Scientific Working Group on Digital Evidence (SWGDE). Current guidance documents.','https://www.swgde.org/documents/current-documents/'),
('17','FalkorDB public repository and license information. Review the applicable version and deployment terms before adoption.','https://github.com/FalkorDB/FalkorDB'),
]
ref_flow=[P('14. Selected references','PageTitleX'),P('Direct links are embedded. These works inform design and evaluation questions; verify publication metadata, versions, and current operational guidance before formal citation or deployment.','Deck'),HRFlowable(width='100%',thickness=.7,color=HexColor('#D7E1E9'),spaceAfter=6)]
for n,cite,url in refs:
    ref_flow.append(P(f'<b>[{n}]</b> {cite} <link href="{url}" color="#087E8B">Open source ↗</link>','RefX'))
ref_flow += [Spacer(1,4),P('Source documents reviewed','H2x'),P('SUTRAM_2026_Digital_Forensics_120_Problems_Features_Stack.pdf (three byte-identical copies); SUTRAM_2026_Research_Blackholes.pdf; and SUTRAM_Consolidated_Features_Blackholes_GitHub_Research_Map.pdf. Their counts and overlaps are called out on page 2. The Claude conversation supplied the FalkorDB/PostgreSQL distinction, the parser-first recommendation, and the request for a 15-page architecture book.','SmallX'),P('Research connections on page 13 use the paper/resource numbering shown here. This is an engineering synthesis, not a systematic review or expert legal opinion.','SmallX')]
pages.append(ref_flow)

assert len(pages)==15, len(pages)
doc=BookDoc(OUT)
story=[]
for i,pg in enumerate(pages):
    story.extend(pg)
    if i < len(pages)-1:
        story.append(PageBreak())
doc.build(story)
print(f'Wrote {OUT.resolve()}')
