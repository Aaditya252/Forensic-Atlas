"""Generate the SUTRAM product and research encyclopedia PDF."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, PageBreak, Flowable, HRFlowable, KeepTogether)

OUT=Path('output/pdf/SUTRAM_Product_Architecture_Research_Encyclopedia.pdf')
OUT.parent.mkdir(parents=True,exist_ok=True)
W,H=A4
NAVY=HexColor('#10243A'); INK=HexColor('#26384B'); TEAL=HexColor('#087E8B')
CYAN=HexColor('#57C7D4'); GOLD=HexColor('#E6A23C'); MUTED=HexColor('#657687')
PALE=HexColor('#F2F6F9'); MINT=HexColor('#DDF2EF'); WARM=HexColor('#FFF2D7')
RED=HexColor('#B84A4A'); WHITE=colors.white; LINE=HexColor('#D4DEE6')

ss=getSampleStyleSheet()
ss.add(ParagraphStyle(name='CoverKicker',fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=TEAL,spaceAfter=12))
ss.add(ParagraphStyle(name='CoverTitleX',fontName='Helvetica-Bold',fontSize=30,leading=34,textColor=NAVY,spaceAfter=12))
ss.add(ParagraphStyle(name='CoverDeckX',fontName='Helvetica',fontSize=13,leading=18,textColor=MUTED,spaceAfter=12))
ss.add(ParagraphStyle(name='T1',fontName='Helvetica-Bold',fontSize=19,leading=23,textColor=NAVY,spaceAfter=4))
ss.add(ParagraphStyle(name='DeckX',fontName='Helvetica',fontSize=8.8,leading=12,textColor=MUTED,spaceAfter=8))
ss.add(ParagraphStyle(name='H2x',fontName='Helvetica-Bold',fontSize=10.7,leading=13,textColor=TEAL,spaceBefore=5,spaceAfter=3))
ss.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=8,leading=10.8,textColor=INK,spaceAfter=4))
ss.add(ParagraphStyle(name='BodyLead',fontName='Helvetica',fontSize=8.5,leading=11.3,textColor=INK,spaceAfter=5))
ss.add(ParagraphStyle(name='SmallX',fontName='Helvetica',fontSize=7.2,leading=9,textColor=INK,spaceAfter=2))
ss.add(ParagraphStyle(name='TinyX',fontName='Helvetica',fontSize=6.7,leading=8.2,textColor=INK,spaceAfter=1))
ss.add(ParagraphStyle(name='CalloutX',fontName='Helvetica-Bold',fontSize=8,leading=10.5,textColor=NAVY,spaceAfter=0))
ss.add(ParagraphStyle(name='TH',fontName='Helvetica-Bold',fontSize=7,leading=8.2,textColor=WHITE,spaceAfter=0))
ss.add(ParagraphStyle(name='TD',fontName='Helvetica',fontSize=6.7,leading=8.4,textColor=INK,spaceAfter=0))
ss.add(ParagraphStyle(name='TDS',fontName='Helvetica',fontSize=7.4,leading=9.3,textColor=INK,spaceAfter=0))
ss.add(ParagraphStyle(name='Ref',fontName='Helvetica',fontSize=7,leading=9,textColor=INK,spaceAfter=3))

def P(t,style='BodyX'):
    # Use built-in Helvetica glyphs for dependable PDF rendering across viewers.
    t=t.replace('•','-').replace('→',' to ').replace('↗','>')
    return Paragraph(t,ss[style])
def bullets(xs,style='BodyX'):
    return [Paragraph('- '+x,ss[style]) for x in xs]
def callout(t,tone='mint'):
    bg,edge={'mint':(MINT,TEAL),'warm':(WARM,GOLD),'red':(HexColor('#FCE9E8'),RED),'blue':(HexColor('#EAF3F8'),TEAL)}[tone]
    q=Table([[P(t,'CalloutX')]],colWidths=[174*mm])
    q.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),.7,edge),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); return q

class FlowDiagram(Flowable):
    def __init__(self,rows,width=174*mm,node_h=12*mm,gap=4*mm,rowgap=7*mm):
        super().__init__(); self.rows=rows; self.width=width; self.node_h=node_h; self.gap=gap; self.rowgap=rowgap
        self.height=len(rows)*node_h+(len(rows)-1)*rowgap
    def wrap(self,aw,ah): self.width=min(self.width,aw); return self.width,self.height
    def draw(self):
        c=self.canv; y=self.height-self.node_h
        for ri,row in enumerate(self.rows):
            n=len(row); nw=(self.width-(n-1)*self.gap)/n
            for i,label in enumerate(row):
                x=i*(nw+self.gap); c.setFillColor([PALE,MINT,WARM][ri%3]); c.setStrokeColor([TEAL,TEAL,GOLD][ri%3]); c.setLineWidth(.8); c.roundRect(x,y,nw,self.node_h,4,fill=1,stroke=1)
                parts=label.split('|'); c.setFillColor(NAVY); c.setFont('Helvetica-Bold',6.7)
                if len(parts)==1: c.drawCentredString(x+nw/2,y+self.node_h/2-2.5,parts[0])
                else:
                    c.drawCentredString(x+nw/2,y+self.node_h/2+1.2,parts[0]); c.setFont('Helvetica',6.1); c.drawCentredString(x+nw/2,y+self.node_h/2-5.8,parts[1])
                if i<n-1:
                    c.setStrokeColor(TEAL); c.line(x+nw+1,y+self.node_h/2,x+nw+self.gap-1,y+self.node_h/2)
                    c.line(x+nw+self.gap-1,y+self.node_h/2,x+nw+self.gap-3,y+self.node_h/2+2); c.line(x+nw+self.gap-1,y+self.node_h/2,x+nw+self.gap-3,y+self.node_h/2-2)
            if ri<len(self.rows)-1:
                c.setStrokeColor(MUTED); c.setDash(2,2); c.line(self.width/2,y-1,self.width/2,y-self.rowgap+1); c.setDash()
            y-=self.node_h+self.rowgap

def tab(head,rows,widths,small=False):
    sty='TDS' if small else 'TD'; d=[[P(x,'TH') for x in head]]+[[P(str(x),sty) for x in row] for row in rows]
    t=Table(d,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.35,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3.5),('BOTTOMPADDING',(0,0),(-1,-1),3.5),('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,PALE])]))
    return t

class BookDoc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=23*mm,bottomMargin=16*mm,
                         title='SUTRAM: Product Architecture, Features, Agents, Data, and Research Encyclopedia',author='SUTRAM design brief')
        f=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='f',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='p',frames=f,onPage=self.decorate)])
    def decorate(self,c,doc):
        c.saveState()
        if doc.page>1:
            c.setFillColor(NAVY); c.rect(0,H-11*mm,W,11*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont('Helvetica-Bold',7.1); c.drawString(18*mm,H-7.3*mm,'SUTRAM  /  PRODUCT & RESEARCH ENCYCLOPEDIA')
            c.setFillColor(TEAL); c.rect(18*mm,9.7*mm,12*mm,1.2*mm,fill=1,stroke=0)
            c.setFillColor(MUTED); c.setFont('Helvetica',7); c.drawRightString(W-18*mm,9.7*mm,f'{doc.page:02d}')
        c.restoreState()

def pg(title,deck,*blocks):
    return [P(title,'T1'),P(deck,'DeckX'),HRFlowable(width='100%',thickness=.7,color=LINE,spaceAfter=7),*blocks]

pages=[]

# Cover
pages.append([Spacer(1,14*mm),P('THE SUTRAM BLUEPRINT','CoverKicker'),P('Digital forensics\nproduct encyclopedia','CoverTitleX'),P('A front-to-back guide to the investigator dashboard, evidence lifecycle, data architecture, agents, machine learning, research use, and the 124-feature engineering catalog.','CoverDeckX'),Spacer(1,6*mm),FlowDiagram([
    ['SCOPE|case + authority','COLLECT|sources + adapters','PRESERVE|original + custody'],
    ['UNDERSTAND|parse + coverage','CONNECT|timeline + graph','ASSESS|rules + ML'],
    ['REVIEW|human decisions','EXPLAIN|evidence links','EXPORT|reproducible report']],node_h=17*mm,gap=5*mm,rowgap=9*mm),Spacer(1,9*mm),callout('<b>Reading promise:</b> technical concepts are introduced in plain language, then tied to dashboard screens, data records, software components, evaluation, and the research that informs them.','blue'),Spacer(1,12*mm),P('Architecture proposal for a future software product. The supplied workspace contains a personal portfolio, not an implemented SUTRAM forensic platform. This book separates planned capabilities from features that exist today.','SmallX'),P('Prepared from the three unique Cybersecurity-folder PDFs, the available Claude conversation details, and the digital-forensics research list. October 2026.','SmallX')])

# 1
pages.append(pg('How to read this book','A guided route from the investigator’s problem to a testable software design.',
    P('<b>Start with the user journey.</b> The opening chapters describe what an investigator sees and the sequence a case follows. Next come the system boundaries, data model, agent roles, AI/ML lifecycle, network/cloud/media workflows, and operational controls. The final sections connect research papers to product decisions and list every row from the supplied engineering matrix.' ,'BodyLead'),
    FlowDiagram([['PART I|product + workflow','PART II|architecture + data','PART III|analysis + operations'],['PART IV|research integration','PART V|complete 124-row catalog','APPENDIX|sources + glossary']],node_h=14*mm),
    tab(['Part','What you will learn'],[('I. Product and dashboard','Case workspace, investigation lifecycle, pages, roles, and the investigator’s mental model.'),('II. Architecture and data','Trust boundaries, databases, schema, storage, indexes, graph projection, APIs, and gateway.'),('III. Analysis services','Acquisition, parsing, timelines, agents, evidence-grounded AI, ML training, media, network, cloud, IoT.'),('IV. Validation and research','Paper-to-layer map, hypotheses, baselines, metrics, experiments, and implementation sequence.'),('V. 124-feature catalog','All source checklist IDs and their product behaviors across domains A–L.')],[39*mm,136*mm],small=True),
    P('Chapter map','H2x'),
    tab(['Pages','Topics'],[('3–10','Product promise, dashboard, case lifecycle, architecture, roles, source coverage, acquisition.'),('11–18','Integrity, parsers, canonical schema, PostgreSQL, object storage, graph, timeline, correlation.'),('19–35','Agents, AI/ML, multimedia, cloud/network/IoT, gateway, infrastructure, security, reports, research, roadmap.'),('36–47','All 124 feature rows across domains A–L.'),('48–50','Research hypotheses, selected references, and glossary.')],[24*mm,151*mm],small=True),
    callout('<b>How to interpret wording:</b> “must” states a forensic trust requirement; “proposed” is a design recommendation; “optional” is a component to adopt only after workload and legal review. No accuracy or speed number is claimed without a benchmark.','warm'),
    P('Contents: product blueprint • dashboard specification • end-to-end case • architecture • acquisition • chain of custody • parsers • databases • graph • timeline • agents • AI/ML training • deepfake • network/cloud/IoT • gateway • infrastructure • security • reporting • test strategy • research map • roadmap • complete feature register.','SmallX')))

# 2
pages.append(pg('A clear product statement','SUTRAM is planned as a case-centered digital evidence platform: it organizes authorized evidence, makes coverage and transformations visible, and helps investigators test explanations.',
    P('The platform is not a universal “crime detector.” It is a controlled workspace where each record, relationship, model score, and report claim has a source, a processing history, a quality state, and a reviewer decision. The investigator remains responsible for interpretation and conclusions.','BodyLead'),
    tab(['Product promise','What the product does','What it cannot promise'],[
        ('One case view','Connect evidence from files, devices, provider exports, logs, packets, and media in a single case workspace.','That every source is accessible, retained, complete, or lawfully collectible.'),
        ('Visible provenance','Trace every derived observation to the source artifact, parser/model version, and transformation.','That hashing alone proves the original source was truthful or untampered before collection.'),
        ('Assisted investigation','Find patterns, gaps, contradictions, and candidate links; show supporting evidence and uncertainty.','That temporal proximity, a model score, or a graph path establishes causality or person identity.'),
        ('Reproducible reporting','Export reviewed claims with exact evidence references, tool versions, limitations, and custody history.','That software output guarantees admissibility or replaces legal advice/examiner expertise.')],[33*mm,71*mm,71*mm],small=True),
    P('From screens to proof','H2x'),
    P('A dashboard is only trustworthy if its visible status corresponds to durable records. “Collected” needs an acquisition event; “verified” needs a recorded digest comparison; “parsed” needs parser/version and coverage; “AI-assisted” needs model and input lineage; “reviewed” needs a named decision. The UI should reveal those records on demand rather than turning them into decorative badges.'),
    callout('<b>Evidence-first rule:</b> database rows and charts are views of evidence records. They must never silently become replacement evidence or erase the source’s raw form.')))

# 3 dashboard overview
pages.append(pg('The investigator dashboard: one case, many lenses','The home screen should answer four questions quickly: What is in scope? What has been collected? What is incomplete or uncertain? What needs human review?',
    FlowDiagram([['Case header|authority • status','Coverage map|found • missing','Job queue|running • blocked'],['Evidence integrity|checkpoints','Timeline|events • gaps','Findings|support • conflict'],['Review inbox|AI • parser • access','Report builder|claims • citations','Audit view|who • what • when']],node_h=14*mm),
    tab(['Screen / workspace','Core widgets and actions','Primary records read'],[
        ('Case overview','Scope badge; source coverage; acquisition progress; integrity exceptions; analysis queue; review tasks; recent audit events.','Case, SourcePlan, AcquisitionJob, Artifact, Alert, ReviewTask, AuditEvent.'),
        ('Evidence library','Filter by source/type/status/hash/date; original vs derived; custody chain; download under permission.','Artifact, ObjectVersion, CustodyEvent, AccessEvent.'),
        ('Acquisition center','Connector status; authorized source scope; retention deadline; live job controls; partial-result warnings.','Source, Authorization, AcquisitionJob, CoverageItem.'),
        ('Analysis workspace','Parser run comparison; field coverage; duplicate/conflict indicators; timeline and entity graph.','ParserRun, Observation, Entity, Relation, TimelineIndex.'),
        ('AI/review inbox','Claim cards; source excerpts; confidence limitations; contradiction and abstention; approve/reject/edit rationale.','ModelRun, Claim, ClaimEvidence, ReviewDecision.'),
        ('Reports and audit','Report templates; exports; chain-of-custody appendix; reproducibility manifest; access history.','Report, ReportClaim, AuditEvent, RunManifest.')],[32*mm,78*mm,65*mm],small=True),
    P('Design principle','H2x'),P('Every summary card should drill to the records behind its number. A “92% coverage” badge without a defined expected-source denominator is misleading. Display “7 of 9 expected source classes available; 2 unavailable” and show why.')),)

# 4 full journey
pages.append(pg('The end-to-end investigation lifecycle','A case moves through explicit gates. Each gate records both the work performed and the limitations that remain.',
    FlowDiagram([['1 Scope|authority + questions','2 Plan|sources + retention','3 Collect|jobs + adapters'],['4 Preserve|hash + custody','5 Parse|safe + versioned','6 Validate|coverage + counts'],['7 Analyze|search + timeline','8 Review|claims + alternatives','9 Report|citations + manifest']],node_h=15*mm),
    tab(['Gate','Investigator decision','System evidence'],[
        ('Scope','What question is authorized? Which accounts/devices/date range may be examined?','Scope version, authority record, exclusions, approver, policy checks.'),
        ('Plan','Which sources can answer the question, and which expire soon?','Source plan, coverage denominator, retention deadlines, connector requirements.'),
        ('Collect','Is the method approved and does it risk changing live state?','Acquisition method, tool build, source response, times, side effects, errors.'),
        ('Preserve & parse','Are the original bytes and transformations traceable?','Hash events, immutable object versions, parser versions, counts, field coverage.'),
        ('Analyze & review','What is observed, inferred, disputed, or unknown?','Observation links, rules/models, alternatives, reviewer decisions, audit events.'),
        ('Report & close','Can another examiner replay the relevant computation?','Claim-evidence links, run manifest, export digest, retention/hold state.')],[28*mm,75*mm,72*mm],small=True),
    callout('<b>Partial is a valid outcome.</b> If provider access is denied, a device is locked, data has expired, a parser supports only part of the format, or a model abstains, preserve that state. Do not convert it into a clean empty result.')))

# 5 architecture
pages.append(pg('System architecture and trust boundaries','Separate user experience, control plane, evidence plane, analysis plane, and durable records.',
    FlowDiagram([['Browser UI|React • case views','API gateway|identity • schema','Case services|policy • workflow'],['Job broker|durable state','Workers|adapters • parsers • ML','Evidence vault|immutable originals'],['PostgreSQL|system of record','Search/graph|derived projections','Audit/metrics|restricted access']],node_h=14*mm),
    tab(['Plane','Services','Trust boundary'],[
        ('Presentation','Dashboard, search, timeline, review, report builder.','Browser is untrusted; authorization is enforced server-side for every object and action.'),
        ('Control','API, case authorization, job orchestration, scheduler, approval workflow.','Only approved scope can create source jobs or expose sensitive fields.'),
        ('Evidence','Upload/connector, object vault, custody registry, forensic exports.','Original bytes are write-once; reads and exports are access-logged.'),
        ('Analysis','Parser sandboxes, rule engine, ML inference, graph/search indexing.','Workers get minimal input and capabilities; outputs are derived and versioned.'),
        ('Operations','Monitoring, backups, keys, deployment, policy, incident response.','Ops access is separated from case content; logs are content-minimized.')],[26*mm,62*mm,87*mm],small=True),
    P('Recommended service decomposition','H2x'),P('<b>Web app:</b> React + TypeScript, Tailwind, component library. <b>API:</b> Python FastAPI + Pydantic. <b>Jobs:</b> Celery workers with Redis or a durable broker selected after failure testing. <b>Registry:</b> PostgreSQL. <b>Objects:</b> S3-compatible encrypted storage (or controlled local object store for offline labs). Optional graph, full-text, and vector services remain derived.'),
    callout('<b>Do not make a microservice for every noun.</b> Begin as a modular application plus isolated worker processes. Split services only when scale, security boundary, or release cadence makes the boundary useful.','blue')))

# 6 dashboard specification
pages.append(pg('Dashboard pages: complete planned navigation','This is the product surface to implement—not a claim that the current portfolio contains these screens.',
    tab(['Navigation','Detailed planned capability'],[
        ('1. Home / workload','My assigned cases, recent work, blocked jobs, urgent retention deadlines, review tasks, service status.'),
        ('2. Cases','Create case; set purpose, authority, jurisdiction, scope, retention/hold; add team and roles; case activity feed.'),
        ('3. Sources & coverage','Source inventory; source type and custodian; expected vs available; authorization/access state; expiry and gaps.'),
        ('4. Acquisition jobs','Plan connector run; submit/resume/cancel; inspect progress, page tokens, source responses, side effects, warnings.'),
        ('5. Evidence library','Original and derived items; hash; metadata; custody; parser status; parent/child links; authorized export.'),
        ('6. Integrity & custody','Checkpoint comparison; transfer/access history; tamper alerts; custody report; signer identity.'),
        ('7. Parser coverage','Supported format/version/fields; expected vs parsed counts; skipped structures; tool comparison; regression diffs.'),
        ('8. Search & timeline','Cross-source search; filters; raw and normalized time; event/log/ingest timestamps; uncertainty and coverage gaps.'),
        ('9. Entities & graph','Person/device/account/session kept distinct; evidence-backed edges; source dependence; alternative hypotheses.'),
        ('10. Media analysis','Image/audio/video metadata, frame sampling, compression history, detector results, sync analysis, caveats.'),
        ('11. AI review inbox','Evidence-grounded draft claims; exact source spans; contradictions; abstention; reviewer disposition and rationale.'),
        ('12. Reports','Template, claim selection, evidence appendix, method/version manifest, limitations, export and digest.'),
        ('13. Admin & operations','Users/roles, connectors, parser registry, model versions, retention policies, queues, audit, backup/restore status.')],[36*mm,139*mm],small=True),
    callout('<b>Navigation rule:</b> investigator-facing screens should use case language (“Evidence coverage”, “Review finding”), while implementation names and model jargon remain in technical detail panels.')))

# 7 case and roles
pages.append(pg('Cases, identity, permissions, and workflow','A digital case is the security and provenance boundary. Case IDs scope every artifact, query, job, graph edge, and export.',
    tab(['Role','Default capabilities','Approval boundary'],[
        ('Case lead / examiner','Set scope within authority, plan sources, review findings, prepare report.','Second-person approval for scope expansion or sensitive export if policy requires.'),
        ('Evidence custodian','Manage intake, transfers, sealed originals, access and custody records.','Cannot alter analysis conclusions; may attest to handling events.'),
        ('Analyst / specialist','Run permitted analyses, annotate artifacts, create candidate hypotheses.','Cannot sign another examiner’s final conclusions.'),
        ('Reviewer / supervisor','Review evidence links, contradictions, methods, limitations and final package.','Approves or returns report; decision and rationale are recorded.'),
        ('Platform operator','Maintain services, backups, connector health, deployment, security controls.','No standing case-content access; elevated access is time-limited and audited.'),
        ('Auditor / read-only','Review authorized process, manifest, custody and access history.','Cannot modify source evidence or analytical records.')],[31*mm,74*mm,70*mm],small=True),
    P('Permission design','H2x'),P('Use least privilege with case-level role grants and object-level checks. The API must verify case membership before returning an artifact, thumbnail, snippet, vector result, graph neighborhood, or export. Apply field-level restrictions for especially sensitive data. Every permission change and privileged read emits an AuditEvent.'),
    P('Case lifecycle states','H2x'),P('<b>Draft → Authorized → Active → Review → Reported → Closed → Retained/Disposed.</b> State transitions require reasons and permitted actors. A legal hold prevents scheduled deletion; closure does not erase audit or custody history.'),
    callout('<b>Identity precision:</b> a login account, device, active session, and human person are separate entities. The UI should show “account observed on device” before it ever presents “person performed action.”')))

# 8 ingestion
pages.append(pg('Source coverage and acquisition adapters','Acquisition begins with a question and an authorized scope; connectors then make their limits explicit.',
    FlowDiagram([['Source inventory|device • cloud • log','Authority check|case scope','Adapter plan|format + window'],['Collect|read-only if possible','Record state|complete • partial • fail','Coverage map|found • missing • unknown']],node_h=15*mm),
    tab(['Connector family','Inputs / considerations','Coverage evidence'],[
        ('File and disk','Images, archives, file-system metadata; large uploads require streaming and resumability.','Manifest, byte size, source path/image ID, acquisition tool, expected artifact classes.'),
        ('Mobile / application exports','Vendor exports, app databases, chat backups, media; version-specific schemas.','Device/app/OS versions, export method, supported field/structure matrix.'),
        ('Endpoint / memory','Live response, snapshots, volatile state; collection itself may affect state.','Host identity, acquisition start/stop, processes, response error, side-effect statement.'),
        ('Cloud / SaaS','Audit logs, identity events, object versions, mail, collaboration history; provider permissions and retention.','Tenant/account, API version, request IDs, time window, page totals, denied/expired items.'),
        ('Network','PCAP, Zeek logs, firewall/DNS/VPN exports; encryption limits payload visibility.','Capture points, clock context, interface/filter, dropped packets and parser status.'),
        ('IoT / embedded','Device exports, sensor data, gateway records, proprietary formats.','Model/firmware, schema documentation confidence, privacy and legal basis.')],[28*mm,77*mm,70*mm],small=True),
    P('Research use','H2x'),P('Cloud-forensics, readiness, log-review, and IoT-forensics papers inform source inventories, retention-aware planning, access constraints, and heterogeneous adapters. They do not imply every provider exposes the same data or that missing content can be reconstructed. [1–4]'),
    callout('<b>Coverage state set:</b> expected / available / acquired / inaccessible / expired / filtered by scope / unsupported / not applicable / unknown. Store the reason and timestamp for every non-acquired state.')))

# 9 acquisition protocol
pages.append(pg('Acquisition jobs: request, stream, checkpoint, verify','The gateway creates a controlled job. A worker performs collection and returns a result manifest; the request thread never parses or stores a multi-gigabyte file synchronously.',
    FlowDiagram([['API|authorize + validate','Job record|idempotency key','Queue|priority + limits'],['Connector|scoped credential','Stream|chunk + digest','Vault|commit object'],['Manifest|source result','Coverage|expected vs actual','Review|partial gaps']],node_h=14*mm),
    P('Job contract','H2x'),P('An AcquisitionJob includes case ID, approved scope version, source adapter and build, time range, filters, requester, authorization reference, credential reference (never the secret itself), idempotency key, retry budget, status, progress, source request IDs, timestamps, result artifact IDs, and a structured error/coverage report.'),
    P('Operational controls','H2x'),*bullets(['Stream to quarantined object storage; validate declared size/type and compute server-side digest while receiving. Finalize only after complete chunk verification.','Use resumable transfer when supported; persist encrypted continuation tokens and avoid replaying destructive or state-changing actions blindly.','Make retries bounded and visible. Differentiate transient provider errors, access denial, expiration, malformed response, and actual empty source.','Capture live-state collection risks and changes. A repeated snapshot difference may be normal background activity, tool effect, or source inconsistency; preserve all runs. [3, 9]','Apply per-case quotas, source rate limits, and worker pools. A job can be paused/cancelled without losing already acquired immutable chunks or audit events.']),
    callout('<b>Jobs are asynchronous:</b> accept quickly with a stable job ID, then expose progress, warning counts, and a terminal state. Do not report “success” without an artifact manifest and coverage state.')))

# 10 evidence and custody
pages.append(pg('Integrity, authenticity, and chain of custody','Three different questions must remain separate: are these bytes unchanged since capture, where did they come from, and were they authentic before capture?',
    tab(['Question','Evidence SUTRAM should record','Interpretation limit'],[
        ('Integrity after capture','Digest algorithm/value, object version, checkpoints, verification time, verifier, and pass/fail.','A digest cannot prove the pre-capture truth or completeness of content.'),
        ('Provenance','Source, collector, method/tool, authority, time, acquisition parameters, provider response, parent artifact.','A provenance record can itself be incomplete; corroborate source independently.'),
        ('Custody','Every transfer, access, transformation, export, seal/reopen, actor, purpose, timestamp and signature.','A broken record must be disclosed and investigated; do not silently recreate history.'),
        ('Authenticity assessment','Source trust, provenance support, independent corroboration, conflicting indicators, reviewer rationale.','An authenticity assessment is a conclusion with uncertainty, not a hash result.')],[34*mm,83*mm,58*mm],small=True),
    FlowDiagram([['Acquire|original digest','Store|immutable version','Verify|checkpoint digest'],['Transform|new child artifact','Link|parent + operation','Export|manifest + digest']],node_h=14*mm),
    P('Blockchain and tamper evidence','H2x'),P('Blockchain literature may be relevant when independent organizations need a shared, append-only custody log. For a single organization, signed append-only events, protected keys, independent backups, access controls, and restore drills may be simpler. A ledger cannot make a false initial assertion true. [5]'),
    callout('<b>Recommended default:</b> SHA-256 for integrity checks; preserve original bytes; record every transformation as a new derived object with a parent link, tool build, parameters, timestamp, and output digest.')))

# 11 parsers
pages.append(pg('Parser pipeline and format coverage','A parser is a measurement instrument: its version, supported fields, failure behavior, and known gaps belong in the case record.',
    FlowDiagram([['Quarantine|untrusted object','Identify|type • signature','Sandbox|resource limits'],['Parse|adapter version','Validate|schema • sentinels','Compare|expected • observed'],['Complete|evidence-linked','Partial|visible warning','Failed|reason + preserve']],node_h=14*mm),
    tab(['Parser registry field','Why it matters'],[
        ('Format / producer versions','A chat export, cloud response, or binary format may change without changing the filename.'),
        ('Supported field/structure matrix','A parser can produce records while silently skipping attachments, nested fields, deleted context, or new message types.'),
        ('Known-answer fixtures','Expected counts and field values reveal truncation, omission, timezone drift, and semantic changes.'),
        ('Execution conditions','Library versions, configuration, platform, limits, locale, timezone, and dependency digests enable replay.'),
        ('Partial/error semantics','Separate unsupported, malformed, skipped, recovered, and complete output. Keep warnings attached downstream.'),
        ('Safe execution','Run in isolated workers with bounded memory, CPU, wall time, recursion, and no default outbound network.')],[42*mm,133*mm],small=True),
    P('Silent parser failure experiment','H2x'),P('Start with generated or legally authorized samples containing known record counts, edge-case encodings, truncated data, and version variants. Compare actual and expected items; run two parser builds; capture field coverage and diffs. Score artifact recall, false extraction, coverage detection, false alerts, runtime, and memory. The consolidated research map recommends this first because it has clearer ground truth and does not require a large language model.'),
    callout('<b>Product status model:</b> Complete means declared supported scope passed checks. Partial means useful output exists with named gaps. “Process exited 0” is not a completeness measure.')))

# 12 canonical schema
pages.append(pg('Canonical data model: preserve raw and derived meaning','Normalize enough to search across sources, but do not erase source-specific fields, source wording, raw timestamps, or extraction context.',
    tab(['Entity','Core fields','Links'],[
        ('Case','id, purpose, authority_ref, jurisdiction, scope_version, retention_policy, status','has members, source plans, artifacts, jobs, reports'),
        ('Source','id, kind, provider/device, account/tenant, version, access_state, expected_classes','used by acquisition; referenced by observations'),
        ('Artifact','id, case_id, parent_id, object_uri, media_type, size, hash_alg, digest, acquired_at','has custody, parser runs, transformations'),
        ('Observation','id, artifact_id, source_record_id, raw_payload_ref, normalized_fields, event_time_raw, event_time_utc, timezone, parser_run_id','supports entities, relations, claims'),
        ('Entity / Relation','typed entity; identifiers; relation type; observed/inferred; confidence; validity interval','each relationship links to one or more supporting observations'),
        ('Run / Claim / Review','tool/model/prompt version; params; status; input IDs; output; cited spans; reviewer decision','links analysis to evidence and report')],[34*mm,91*mm,50*mm],small=True),
    Spacer(1,4),FlowDiagram([['Case|authority + scope','Acquisition|source + job','Artifact|immutable + derived'],['ParserRun|build + coverage','Observation|raw + normalized','Claim|citations + review']],node_h=12*mm,gap=4*mm,rowgap=5*mm),
    P('Observation envelope example','H2x'),
    callout('<b>Example:</b> raw event_time = “2026-04-01 09:15” from source offset “+05:30”; normalized = 2026-04-01T03:45:00Z; time precision = minute; clock confidence = unknown; source record = cloud audit row 442; parser build = audit-v3.2; status = parsed; interpretation = user session start (observed).','blue'),
    P('Schema discipline','H2x'),P('Use stable IDs, foreign keys, explicit enum versions, JSONB for source-specific extensions, and typed columns for common searchable fields. Store raw payloads in the object vault when large or sensitive. Keep ingestion time separate from event time and log-record time. Never overwrite a source value with its normalized form.'),
    callout('<b>Interoperability:</b> preserve a source-native identifier and schema version for every record. A canonical layer should add meaning and searchability, not flatten away evidence.')))

# 13 PostgreSQL
pages.append(pg('Databases: relational system of record','PostgreSQL should hold durable case metadata, evidence registry, acquisition/parsing runs, normalized observations, review decisions, and append-only application audit events.',
    tab(['Table family','Example tables','Key constraints / indexes'],[
        ('Identity & policy','users, roles, case_members, authority_records, scope_versions','case_id on every protected row; composite policy checks; immutable scope history.'),
        ('Acquisition','sources, source_plans, acquisition_jobs, coverage_items','idempotency_key unique per case; status/time indexes; JSONB provider metadata.'),
        ('Evidence','artifacts, object_versions, custody_events, access_events','digest + byte length; parent_artifact_id; append-only custody; object URI uniqueness.'),
        ('Analysis','parser_builds, parser_runs, observations, entities, relations','case/artifact/time indexes; source_record_id; GIN for selected JSONB/search fields.'),
        ('AI / reporting','model_builds, inference_runs, claims, claim_evidence, review_decisions, reports','model and prompt digests; claim evidence foreign keys; reviewer and disposition history.'),
        ('Governance','audit_events, retention_actions, holds, export_manifests','restricted append-only writes; export checksum; hold overrides deletion schedule.')],[33*mm,67*mm,75*mm],small=True),
    P('PostgreSQL implementation notes','H2x'),*bullets(['Use transactions for registry and custody events; a completed object upload and registry commit need a recoverable two-phase workflow or reconciler.','Partition very large observation/audit tables by case/time only after measuring query patterns and operational complexity. Keep migrations versioned.','Apply row-level security as defense in depth where practical, while still enforcing application authorization. Avoid broad admin credentials in workers.','Start with PostgreSQL full-text and B-tree/GIN indexes; adopt OpenSearch only when query scale, faceting, or distributed ingestion justifies another data plane.','Back up database metadata and evidence objects independently; restore tests must reconcile both directions and verify object hashes.']),
    callout('<b>System-of-record rule:</b> search indexes, caches, model stores, and graph DBs can be rebuilt. PostgreSQL registry + immutable original objects + custody/audit log must remain authoritative.')))

# 14 storage and lifecycle
pages.append(pg('Object storage, retention, and derived data','Large evidence bytes should live outside relational rows. The database stores stable object references and verifiable metadata.',
    FlowDiagram([['Upload stream|size + digest','Quarantine|malware/safe parse','Evidence vault|versioned object'],['PostgreSQL|artifact registry','Derived store|transforms + reports','Reconcile|digest + orphan scan']],node_h=14*mm),
    tab(['Object class','Lifecycle'],[
        ('Original acquired object','Store immutable version; encrypt; verify digest; never modify in place; access through authorization service.'),
        ('Derived extraction','Create new object with parent artifact ID, operation, parser/model build, configuration digest, and output digest.'),
        ('Temporary workspace','Short-lived, isolated, encrypted; scoped cleanup; crash recovery must not accidentally remove originals.'),
        ('Report/export','Record report version, claim set, run manifest, recipient, reason, signer/reviewer, and export digest.'),
        ('Backup replica','Separate credentials and failure domain; retention lock where supported; test restore and integrity periodically.')],[36*mm,139*mm],small=True),
    P('Retention and disposal','H2x'),P('Retention rules are case- and jurisdiction-dependent. Model policy, expiry, legal hold, and deletion approval explicitly. On approved disposal, remove controlled copies and derived indexes according to policy while retaining the permitted audit proof of disposal. Do not rely on a periodic delete job with no review record.'),
    P('Integrity reconciliation','H2x'),P('A scheduled reconciler compares database artifact rows to object versions, checks digest/length, identifies orphaned objects and missing references, and emits incidents. Rebuild derived indexes from the registry and run manifests; never infer a missing original from a derived extract.'),
    callout('<b>Offline mode:</b> local S3-compatible object storage or an encrypted evidence volume can support isolated labs; define key custody, backup transfer, software updates, and outbound network denial explicitly.')))

# 15 graph database
pages.append(pg('Graph analytics: useful projection, not second truth','Graph queries help investigators explore multi-hop links. They can also make weak relationships look persuasive unless every edge carries its evidence and uncertainty.',
    FlowDiagram([['PostgreSQL|authoritative rows','Projection job|versioned build','FalkorDB optional|graph queries'],['Evidence-linked nodes','Typed observed/inferred edges','Reviewable candidate paths']],node_h=14*mm),
    tab(['Option','Strength','Trade-off / rule'],[
        ('PostgreSQL relational joins','Transactional truth, constraints, reporting, custody-linked foreign keys.','Recursive graph traversals can be less convenient at deeper/many-hop query scale.'),
        ('PostgreSQL recursive CTE / NetworkX','Simple baseline for small or bounded graphs; reproducible offline computation.','Memory/runtime limits and query ergonomics must be measured.'),
        ('FalkorDB projection','Graph-native path exploration; optional specialized query performance.','Not relational; adds operational dependency, synchronization, licensing, durability, and recovery review.'),
        ('Vector search / pgvector','Semantic retrieval over approved text spans with evidence IDs.','Approximate retrieval can miss/over-rank records; results must return exact source spans and permissions.')],[37*mm,63*mm,75*mm],small=True),
    P('Edge model','H2x'),P('Each edge needs: relation type; observed vs inferred; supporting artifact/observation IDs; rule/model version; match fields; time interval; confidence or rationale; reviewer status; and source-dependency group. A path across five inferred edges is not an observed fact.'),
    P('FalkorDB decision','H2x'),P('Claude’s discussion correctly distinguished graph from relational storage. Treat FalkorDB as an optional derived view; benchmark its real query set against PostgreSQL recursive queries and NetworkX. Review the core repository’s SSPLv1 licensing, persistence mode, crash recovery, platform support, and export/rebuild path before adopting. [16]'),
    callout('<b>Build gate:</b> first ship entity and relationship tables in PostgreSQL. Add a graph engine only after recorded query workloads show a clear, reproducible benefit and the operations/licensing review passes.','warm')))

# 16 search and timeline
pages.append(pg('Search, timeline, and event-time reasoning','An event timeline is a user interface over observations—not a canonical story of what happened.',
    tab(['Time field','Meaning','Keep visible because'],[
        ('Event time','When the source says the underlying event happened.','May be inaccurate, rounded, timezone-ambiguous, or manipulated.'),
        ('Record/log time','When a system wrote or received the event record.','Can lag the action or be generated by a different clock.'),
        ('Ingestion time','When SUTRAM acquired the record.','Supports collection order, replay, and later-arriving evidence.'),
        ('Normalized UTC','A conversion used for cross-source querying.','Must retain raw value, zone/offset, conversion rule, and uncertainty.')],[33*mm,55*mm,87*mm],small=True),
    FlowDiagram([['Raw time|verbatim + zone','Normalize|zoneinfo + rules','Order|intervals + uncertainty'],['Coverage|sources present','Compare|contradictions','Timeline|link to original']],node_h=14*mm),
    P('Useful dashboard behaviors','H2x'),*bullets(['Timeline filters by source, entity, event type, confidence, and coverage state; clicking an event opens the exact source record and parser run.','Allow side-by-side contradictory observations; show clock-quality notes and precision. Avoid forcing a total order when intervals overlap.','Annotate gaps in expected logging and collection coverage. “No event returned” is different from “the event did not occur.”','Allow analysts to save alternate timelines and hypotheses; record author, revision, evidence links, and reviewer disagreement. [10, 14]']),
    P('Research connection','H2x'),P('Timesketch provides a useful reference for collaborative timelines, annotations, tags, and analyst context. Cloud-log and network-forensics literature inform source-specific event models. The product’s research contribution should be measured around coverage, source dependence, time uncertainty, and false causal attribution—not timeline aesthetics. [4, 11, 14]')))

# 17 correlation
pages.append(pg('Correlation, source dependence, and attribution','The platform should help investigators ask “what connects these records?” while making the basis and alternative explanations easy to inspect.',
    tab(['Relationship class','Example','UI wording'],[
        ('Direct observation','Log row records account A authenticated to device D.','“Observed: account A authenticated on device D at source time …”'),
        ('Identifier match','Same file digest occurs in endpoint and cloud export.','“Matching digest observed in two records.”'),
        ('Candidate relation','Two sessions share a rare token within a defined window.','“Candidate link; basis shown; needs review.”'),
        ('Human conclusion','Reviewer assesses records support a stated proposition.','“Examiner interpretation; rationale and counterevidence attached.”')],[34*mm,67*mm,74*mm],small=True),
    P('Entity resolution workflow','H2x'),P('Generate candidates from exact identifiers first; then cautiously use fuzzy features such as time proximity, naming similarity, device context, and network observations. Keep feature contributions and the threshold visible. Require reviewer confirmation for person identity, account ownership, or high-impact attribution.'),
    P('Source-dependency graph','H2x'),P('If three reports derive from one upstream log, they are three documents but one evidentiary origin. Maintain parent sources and transformations so analysts can identify dependent corroboration. Measure dependency detection against controlled cases with duplicated and independent sources. [16]'),
    P('Contradiction and alternatives','H2x'),P('Represent claims as propositions with supporting, contradicting, and context evidence. The UI should show competing explanations, unresolved facts, and what additional source could discriminate between them. Do not rank a single narrative solely because it has more duplicated records.'),
    callout('<b>Attribution boundary:</b> an IP address, account, device, and person are distinct. Shared networks, VPNs, session reuse, delegated accounts, and background sync can create plausible but wrong identity chains.')))

# 18 agent architecture
pages.append(pg('Agents and workers: roles, tools, and limits','Use “agent” for a bounded service role. Deterministic workers do most evidence processing; language models are optional assistants with restricted capabilities.',
    tab(['Agent / worker','Inputs → outputs','Permission and safety limit'],[
        ('Case orchestrator','Approved workflow → job DAG, status, retries, audit events.','Cannot broaden scope or assert findings.'),
        ('Acquisition worker','Authorized source plan → artifacts, provider response, coverage.','Short-lived scoped credential; no model access; bounded retries.'),
        ('Parser worker','Quarantined artifact → observations, warnings, coverage.','Isolated runtime; read-only input; no outbound network by default.'),
        ('Integrity/coverage validator','Manifest + objects → digest checks, count diffs, gap alerts.','Produces machine checks, not authenticity conclusions.'),
        ('Correlation/timeline worker','Observations + rules → candidate edges, chronology, contradictions.','Every result has rule version, source IDs, alternatives.'),
        ('ML specialist','Approved task-specific input → score, explanation, abstain flag.','No independent report release; model version/threshold logged.'),
        ('Evidence-grounded drafting agent','Reviewed claims + permitted passages → draft language with citations.','Read-only; no arbitrary tools; no unsupported uncited conclusion.'),
        ('Report/export worker','Approved claim set → deterministic package and manifest.','Requires reviewer sign-off; export is logged and digested.')],[36*mm,72*mm,67*mm],small=True),
    P('Orchestration state','H2x'),P('<b>Requested → authorized → queued → running → partial/complete/failed → analyst review → approved → exported.</b> Each transition records actor/service, timestamp, reason, and input/output IDs. Retries are idempotent; cancellation does not erase partial artifacts or history.'),
    callout('<b>Autonomy ceiling:</b> no agent may change source scope, modify original bytes, make a final person-attribution claim, suppress contradictory evidence, or export a report without a human-controlled approval gate.')))

# 19 AI assistant
pages.append(pg('Evidence-grounded AI: retrieval, claims, abstention','A language model should help navigate and draft from a bounded evidence set. It should not be treated as a source of forensic facts.',
    FlowDiagram([['Approved question|case policy','Retrieve|permitted evidence IDs','Draft claim|structured schema'],['Verify citations|span exists','Check support|entails • conflicts • weak','Review|approve • revise • reject']],node_h=14*mm),
    P('Answer pipeline','H2x'),*bullets(['Authorize query and filter the corpus by case scope, row-level policy, sensitivity, and evidence-quality status before retrieval.','Retrieve exact passages/observations with source IDs and offsets; semantic similarity alone is not proof that a record supports a claim.','Ask for structured output: claim text, evidence IDs/spans, support type (supports/contradicts/insufficient), uncertainty, and limitations.','Validate every citation mechanically: the artifact is accessible, the span exists, the quoted text matches, and the cited observation belongs to this case.','Run semantic checks for negation, speaker identity, modality, time, and qualifiers. Surface contradictions and require abstention when support is weak.','Preserve model/provider, model version, prompt/template digest, retrieval set, parameters, tool access, and reviewer disposition.']),
    P('Why this matters','H2x'),P('The blackhole materials identify meaning shifts such as turning “I saw the files were deleted” into “I deleted the files.” A claim verifier should measure unsupported-claim rate, source-link precision, contradiction recall, speaker/negation preservation, semantic distortion, and abstention quality. [6, 15]'),
    callout('<b>Prompt injection defense:</b> artifact text is data. It cannot rewrite system instructions, trigger privileged tools, expand retrieval permissions, or cause a finding. Test attacks in emails, OCR, PDFs, transcripts, and filenames.')))

# 20 ML training
pages.append(pg('ML pipeline: training is a separate governed product','Training and inference use different data, permissions, and controls. Case evidence must not become training material by default.',
    FlowDiagram([['Research question|task + harm','Dataset|authority + labels','Split|case/device/source grouped'],['Train|versioned code','Evaluate|held-out + slices','Register|weights + metrics'],['Deploy|approved route','Monitor|drift + errors','Review|retrain gate']],node_h=14*mm),
    tab(['Stage','Engineering requirement'],[
        ('Task definition','Narrow output (e.g., parser anomaly alert or media manipulation triage); define what users may infer and what they may not.'),
        ('Dataset governance','Document source authority, provenance, license, consent/retention, labels, demographics, device/source mix, and exclusions.'),
        ('Leakage control','Split by case, person, device, source, and time as appropriate; prevent near-duplicate frames/files across train and test.'),
        ('Training run','Record code commit, dependencies, seed, compute, config, data manifest digest, preprocessing, weights, and checkpoints.'),
        ('Evaluation','Use task-appropriate metrics, confidence intervals, subgroup slices, calibration, false-positive/negative analysis, and external tests.'),
        ('Deployment & drift','Version registry, release approval, rollback, input-quality/OOD flags, drift monitors, and change-control record.'),
        ('Case inference','Log model version, exact input IDs, preprocessing, threshold, output, calibrated status, explanation, and human disposition.')],[35*mm,140*mm],small=True),
    P('Tooling fit','H2x'),P('scikit-learn is appropriate for transparent tabular baselines; PyTorch for deep learning; MLflow for experiment/run/model provenance; Evidently or equivalent for data/model drift and evaluation. Use only tools that fit an auditable, offline-capable environment. A vector index can help retrieve text but is not a forensic verdict. [6, 15]'),
    callout('<b>Case-data rule:</b> never silently train on case evidence. A separate approved dataset process must handle authorization, minimization, de-identification where appropriate, labeling, retention, and the right to remove/refresh examples.')))

# 21 ML assurance
pages.append(pg('Model quality: thresholds, calibration, drift, and abstention','“Accuracy” alone hides whether a detector fails on rare but consequential cases or on unfamiliar evidence.',
    tab(['Question','Metric / view','Dashboard treatment'],[
        ('How many true events were found?','Recall, false-negative rate, per-class support.','Show evaluation scope and error ranges; avoid calling a low-recall triage model a clearance test.'),
        ('How many alerts are wrong?','Precision, false-positive rate, confusion matrix.','Allow threshold tuning only with logged policy and test basis.'),
        ('Are scores meaningful?','Calibration curve, Brier score / ECE as suitable.','Display calibrated/uncalibrated state and validated domain.'),
        ('Does it know unfamiliar input?','OOD tests, risk-coverage curve, abstention rate.','“Inconclusive” is visible; missing confidence is not converted into a green label.'),
        ('Does it shift by population/source?','Subgroup, language, device, codec, compression, source version slices.','Surface unsupported slices and distribution drift.'),
        ('Can results be repeated?','Seed stability, run replay, version/parameter comparison.','Open experiment manifest and prior run differences.')],[40*mm,62*mm,73*mm],small=True),
    P('Model governance','H2x'),P('Define accepted model uses, prohibited conclusions, release criteria, monitoring thresholds, override procedure, and retirement path. NIST AI RMF offers a risk-management structure; it does not certify the forensic validity of a detector. [15]'),
    callout('<b>Abstention is a feature.</b> If the media is heavily recompressed, outside training domain, corrupted, or too short, return an uncertainty state and the reason—not a confident authenticity label.','warm')))

# 22 media/deepfake
pages.append(pg('Multimedia and deepfake workbench','Separate preservation, media decoding, signal analysis, model outputs, and examiner interpretation.',
    FlowDiagram([['Original media|hash + metadata','Derived decode|FFmpeg version','Sampling|frames • audio spans'],['Quality checks|codec • edits','Detectors|image • video • audio','Compare|cross-signal + dataset'],['Evidence view|timecodes','Abstain|OOD • low quality','Review|human rationale']],node_h=13.5*mm),
    tab(['Workbench feature','Output / caveat'],[
        ('Media inventory','Container, codec, duration, streams, metadata presence/absence, digest; preserve all metadata as observed.'),
        ('Frame/audio exploration','Deterministic sampling plan with frame numbers/timecodes; audio chunks linked to the original.'),
        ('Manipulation screens','Detector family, weights, pre-processing, score, calibration domain, explanation, and abstention reason.'),
        ('Cross-modal checks','Audio/video synchronization, lip-motion/voice inconsistency, scene cuts, metadata conflicts; candidate anomaly only.'),
        ('Compression robustness','Run controlled transcode/compression levels; track detector degradation and calibration changes.'),
        ('Report view','State what was tested, what could not be assessed, exact artifacts, model versions, and that a detector is not definitive proof.')],[44*mm,131*mm],small=True),
    P('Research connections','H2x'),P('FaceForensics++ and Celeb-DF support benchmark construction and difficult manipulated-face evaluation; a multimodal deepfake survey broadens coverage to audio/video/social-media transformations. Explainable detection work informs reviewer-facing rationales. Evaluate cross-dataset, compression, identity/demographic, and unseen-method performance; benchmark scores are not deployment guarantees. [7–10]'),
    callout('<b>Dashboard label:</b> “Detector signals consistent with manipulation under tested conditions,” followed by evidence and limitations. Avoid “fake” or “authentic” as an unqualified single-score verdict.')))

# 23 network cloud IoT
pages.append(pg('Network, cloud, and IoT investigation layers','The same case workflow can host different source adapters, but each source family needs its own coverage model, timing semantics, and privacy boundary.',
    tab(['Domain','Workbench behavior','Research papers/tools inform'],[
        ('Cloud','Provider/API source list; tenant/account; request ID; collection window; retention; permission denial; event/log/ingest time.','Cloud forensics, cloud log-forensics, readiness; provider-specific audit schemas. [1,3,4]'),
        ('IoT','Device model/firmware; sensor/gateway logs; schema confidence; collection path; ownership/consent/jurisdiction.','IoT forensics survey and blockchain process-model review for constraints and workflow questions. [2,5]'),
        ('Network','PCAP upload; Zeek logs; DNS/TLS metadata; flow/session links; capture point and packet loss.','Network-forensics taxonomy and packet-analysis survey; Zeek/Wireshark as complementary baselines. [11,14]'),
        ('Memory / endpoint','Live collection state; memory image; process artifacts; collection side effects.','Velociraptor collection patterns, Volatility 3 memory analysis, tool validation procedures.'),
        ('Disk / file system','Image, file-system metadata, deleted fragments, recovery context.','Autopsy/TSK parsers and NIST CFTT/CFReDS test methods.')],[27*mm,78*mm,70*mm],small=True),
    P('Encrypted data boundary','H2x'),P('When communication payloads are encrypted, analyze accessible metadata and timing where lawful; do not claim to have recovered message content. Provider-controlled records may be inaccessible or expired. A missing source record is evidence about coverage only when retention and logging behavior are known.'),
    callout('<b>Tool composition:</b> Autopsy/TSK, Volatility 3, Velociraptor, Zeek, Wireshark, and Timesketch are reference tools with different jobs—not one plug-and-play product. Confirm licenses, supported formats, versions, and validation status before integrating.')))

# 24 gateway
pages.append(pg('Low-latency gateway and high-throughput pipeline','Keep interactive requests short; stream files; use bounded asynchronous workers; measure the whole path before promising performance.',
    FlowDiagram([['Client|TLS + token','Gateway|auth + validate','Policy|scope + quota'],['Stream|chunk + digest','Broker|durable job ID','Workers|separate pools'],['Status|progress + retry','Registry|commit event','Metrics|p50/p95/p99']],node_h=14*mm),
    tab(['Path','Design','Measure'],[
        ('Interactive API','Validate request, authorize, write job record, enqueue, return job ID.','Acceptance latency p50/p95/p99, auth errors, queue delay.'),
        ('Large uploads','Chunked/resumable streaming, bounded size, digest while receiving, quarantine before parsing.','MB/s, retry count, checksum mismatch, time to durable commit.'),
        ('Parser workers','Scale by file format and CPU/memory; process isolation and deadlines.','Records/sec, peak memory, partial/timeout rate, coverage overhead.'),
        ('ML workers','Separate CPU/GPU queues; low-priority batch; cache only derived results keyed by exact model/input/config.','Inference latency, batch throughput, cost per case, drift/quality.'),
        ('Search/timeline','Indexed common filters; bounded result sets; asynchronous deep analytics.','Query p95, index freshness lag, rows scanned, permission-filter cost.')],[31*mm,87*mm,57*mm],small=True),
    P('Reliability under load','H2x'),*bullets(['Apply per-case rate limits, concurrency caps, queue backpressure, cancellation, idempotency, and bounded retry/dead-letter policies.','Keep object storage, database writes, and queue transitions reconcilable after partial failure. Expose degraded status rather than hiding it.','Use OpenTelemetry-style traces with case/job IDs but do not log sensitive evidence contents. Separate acceptance latency from full processing duration.','Set service-level objectives after benchmarking realistic file sizes, parser mixes, evidence counts, and hardware. Publish workload and hardware with p95/p99.']),
    callout('<b>No speed claims yet:</b> sub-millisecond, 60 FPS, or throughput numbers from other portfolio projects do not transfer to forensic workloads. SUTRAM must establish its own measured baselines.','warm')))

# 25 infrastructure
pages.append(pg('Infrastructure, deployment, and recovery','Design for a controlled evidence lab first. Add deployment complexity only when the threat model and workload justify it.',
    tab(['Component','Initial deployment','Scale / offline considerations'],[
        ('Frontend + API','React/TypeScript UI; FastAPI service; reverse proxy/TLS.','Separate public-facing and case-data zones; offline builds need pinned assets.'),
        ('Workers','Docker-isolated parser and ML processes; separate queues.','GPU workers optional; no default outbound network from evidence parsers.'),
        ('Database','PostgreSQL primary; migrations and encrypted backups.','Replica/read pools only after measurement; restore tests verify joins to object store.'),
        ('Evidence object store','Versioned encrypted S3-compatible or controlled local storage.','Immutable retention where supported; separate backup domain and key custody.'),
        ('Broker/cache','Redis/Celery prototype or durable broker validated for recovery.','Do not make volatile queue state the only record of a forensic job.'),
        ('Observability','Metrics, traces, restricted audit, redacted logs.','Record queue lag, parser errors, storage health, integrity reconciliation, recovery state.')],[32*mm,68*mm,75*mm],small=True),
    P('Recovery plan','H2x'),P('Define acceptable recovery-point and recovery-time objectives, restore PostgreSQL and object data into an isolated environment, verify object digest/length and registry references, rebuild derived search/graph/vector projections, reconcile audit continuity, and document test results. A backup that has not been restored is an assumption.'),
    P('Deployment modes','H2x'),P('Managed cloud is appropriate only with approved data routing, access, encryption, provider terms, and jurisdictional review. Offline/local mode needs a patch/update process, model distribution control, key custody, and safe transfer procedures. Keep local model inference as a capability that must be validated, not a magic privacy guarantee.'),
    callout('<b>Small start:</b> one repository, modular API, PostgreSQL, object store, Redis/Celery workers, Docker Compose, and tested offline processing can establish the first vertical slice.')))

# 26 security
pages.append(pg('Security and privacy threat model','A forensic platform is a high-value target. Evidence content can also be malicious input designed to attack parsers, retrieval, or analyst judgment.',
    tab(['Threat','Control set'],[
        ('Malicious uploads / parser exploits','Quarantine; signature and schema checks; sandbox; CPU/memory/file recursion limits; pinned packages; dependency scanning; no network egress.'),
        ('Cross-case disclosure','Case-scoped authorization on every query/path; object-level checks; negative authorization tests; separated encryption keys where required.'),
        ('Prompt injection in evidence','Evidence is inert data; no privileged tools from model context; constrained retrieval; adversarial tests; output citation validation.'),
        ('External AI leakage','Approved model routing, explicit egress, minimization, no default case-data training, local inference only after validation.'),
        ('Tampering / ransomware','Immutable originals, independent audit, segregated backups, least privilege, hash reconciliation, tested recovery.'),
        ('Privacy overcollection','Purpose limitation, scope filters, field-level sensitivity, retention/hold workflow, cross-border review and access logging.'),
        ('Dependency compromise','Pinned/SBOM-backed images, signing, vulnerability scan, build provenance, update review and rollback.')],[43*mm,132*mm],small=True),
    P('Security and evidence are joined','H2x'),P('A breach can alter evidence or undermine confidence in chain-of-custody, while overly broad security logging can expose sensitive case content. Keep operational telemetry content-minimized; make privileged access exceptional and attributable.'),
    callout('<b>Release review:</b> test authorization denial, tenant isolation, malicious parser inputs, prompt injection, secret leakage, backup restore, retention enforcement, and audit completeness before onboarding real cases.')))

# 27 report
pages.append(pg('Investigator review, reports, and reproducibility','A final report should be a reproducible package of selected evidence and reasoning—not a screenshot of a dashboard.',
    FlowDiagram([['Finding|proposition','Evidence|support + contradiction','Method|tool + version'],['Limitations|coverage + uncertainty','Review|examiner + decision','Export|manifest + digest']],node_h=14*mm),
    tab(['Report section','Content'],[
        ('Case and scope','Case reference, question, authorization, evidence scope, exclusions, date range, jurisdiction/policy context.'),
        ('Evidence inventory','Artifact IDs, source, acquisition method, digest, custody summary, coverage gaps and inaccessible sources.'),
        ('Methods','Parser/model/tool builds, configurations, validation scope, timeline rules, search filters, transformations.'),
        ('Findings','Claim-by-claim source links; relevant exact spans/timecodes; supporting and contradictory evidence; alternative explanations.'),
        ('Limitations','Missing logs, incomplete parsing, clock uncertainty, encryption, format limits, detector domain, abstentions, known errors.'),
        ('Review and reproducibility','Reviewer identities, decisions/revisions, manifest, environment/config digests, output digest, rerun instructions.')],[39*mm,136*mm],small=True),
    P('Claim record','H2x'),P('Store claim text, claim type, exact evidence references, support/contradiction/insufficient assessment, author/agent, generation run, reviewer disposition, rationale, and final report revision. Preserve edited draft history. A citation is useful only if it points to the exact source portion and supports the wording used.'),
    callout('<b>Completeness cue:</b> the report should state what sources were expected, what was acquired, what was unavailable or unsupported, and how those gaps constrain conclusions.')))

# 28 test strategy
pages.append(pg('Validation: make every capability measurable','Use known-answer datasets, controlled manipulation, baselines, reproducible environments, and failure cases where the correct output is uncertainty.',
    tab(['Layer','Test design','Core measures'],[
        ('Acquisition','Synthetic/authorized source with known records, pagination, expiry, denied permissions, and retry behavior.','Coverage detection, duplicate jobs, missing records, side-effect reporting.'),
        ('Integrity/custody','Alter, truncate, replace, transfer, and restore objects across checkpoints.','Digest detection, custody completeness, unauthorized mutation rate.'),
        ('Parser','Known-count exports with malformed, version-shifted, multilingual, and nested records.','Artifact recall, field coverage, false extraction, false-alert, runtime/memory.'),
        ('Timeline/correlation','Clock offsets, duplicates, dependent sources, contradictory events, missing logging periods.','Order accuracy, false causal attribution, dependency precision/recall.'),
        ('AI/ML','Held-out cases, domain shifts, demographic/source slices, prompt-injection scenarios.','Unsupported claim rate, calibration, risk-coverage, attack success, human agreement.'),
        ('Operations/security','Load, queue failures, restore drills, cross-case authorization tests, retention and egress tests.','p50/p95/p99, throughput, recovery objectives, deny correctness, policy adherence.')],[31*mm,83*mm,61*mm],small=True),
    P('Forensic tool comparison','H2x'),P('NIST CFTT and CFReDS inform objective tool-testing structure: documented test procedures, criteria, known data, and reproducible outcomes. Autopsy/TSK, Volatility, Zeek, Wireshark, and other tools can provide baselines for relevant artifact classes. Record product version, edition, plugins, operating environment, and exact test corpus. [12,13]'),
    callout('<b>Comparative-study discipline:</b> compare tools on supported scope and known-answer cases. “Tool A found more rows” is not automatically better; count false extractions, context completeness, and provenance too.')))

# 29 research workflow
pages.append(pg('Research workflow: turn gaps into experiments','The source blackholes are candidate questions. Before claiming novelty, check current tools, plugins, papers, versions, editions, and evaluation procedures.',
    FlowDiagram([['Freeze hypothesis|one failure','Map prior support|papers + tools','Define ground truth'],['Baseline|existing workflow','Implement one change','Test held-out + adversarial'],['Measure|predefined metrics','Report limits + errors','Verify novelty claim']],node_h=14*mm),
    tab(['Candidate priority','Experiment outline','Primary metrics'],[
        ('A. Silent parser failure','Known-count corpus; parser version matrix; malformed/updated schema exports; compare expected vs observed records/fields.','Artifact recall, field coverage, false-alert, processing overhead.'),
        ('B. Claim-to-evidence verifier','Statements with supported, contradicted, ambiguous, negated, and speaker-shifted cases; compare model draft to human ground truth.','Unsupported-claim rate, citation precision, contradiction recall, semantic distortion, abstention.'),
        ('C. Source-dependency graph','Duplicate reports and truly independent sources; trace upstream provenance and test corroboration logic.','Dependency detection, false corroboration, alternative explanation coverage.'),
        ('D. Timeline manipulation','Known incident times with clock drift, delayed logs, missing intervals, fabricated entries.','Order accuracy, manipulation detection, false causal attribution.')],[35*mm,91*mm,49*mm],small=True),
    P('Novelty check','H2x'),P('A capability absent from a public page is not proof a product lacks it. Check product edition/plugins, workflow documentation, papers, benchmark reports, and source code where available. State whether your contribution is a method, dataset, evaluation, integration, or operational deployment improvement.'),
    callout('<b>Do one experiment well.</b> A focused parser coverage detector with strong ground truth is more defensible than a broad claim that an AI system solves digital forensics.')))

# 30 source-paper map
pages.append(pg('Research papers to product layers: evidence and acquisition','Each paper should become a design requirement, evaluation question, or boundary statement—not decoration in a bibliography.',
    tab(['Source','Layer / dashboard use','Implementation and evaluation link'],[
        ('Ruan et al., Cloud Forensics (2011) [1]','Cloud source connectors; evidence acquisition and preservation.','Track provider/source identifiers, acquisition window, response context, retention and access limits.'),
        ('Cloud forensic readiness framework (2017) [3]','Case setup, source inventory, runbooks and operational readiness.','Define ahead-of-incident roles, source plans, access paths, retention and response workflow.'),
        ('Systematic review of log-based cloud forensics (2021) [4]','Cloud audit-log ingestion, timeline and source-specific parser coverage.','Create provider-log schema/coverage tests; distinguish event time, log time and ingestion time.'),
        ('IoT forensics survey (2020) [2]','IoT connector model, privacy/access dashboard, device context.','Test heterogeneity, documentation limits, source availability, jurisdiction and acquisition method.'),
        ('Blockchain IoT forensic process review (2022) [5]','Custody/audit collaboration design.','Compare shared ledger against append-only signed event log; state integrity/authenticity limits.'),
        ('Velociraptor / Autopsy / TSK / Volatility references','Adapters and forensic baselines.','Inspect support matrix, formats, versioning, collection side effects and known-answer validation.')],[48*mm,55*mm,72*mm],small=True),
    P('What to store in a research register','H2x'),P('For each paper or tool: citation, DOI/URL, version/date accessed, claim relevant to SUTRAM, architecture decision, limitation, test case generated, and unresolved question. A citation only supports its actual scope; a survey does not validate our implementation.'),
    callout('<b>Research trace:</b> paper → requirement → screen/API/data field → test case → metric → design decision. Use this chain to train the engineering team and defend why the feature exists.')))

# 31 paper map AI/media/network
pages.append(pg('Research papers to product layers: AI, media, network','Benchmarks and surveys help define evaluation. They do not transfer their published results automatically to a new detector or dataset.',
    tab(['Source','Where it connects','How to apply'],[
        ('Nayerifard et al., ML in digital forensics SLR (2023) [6]','Model registry, training lifecycle, evaluation plan.','Select a narrow task; identify reproducibility/data limitations; document training and inference provenance.'),
        ('FaceForensics++ (ICCV 2019) [7]','Video deepfake evaluation screen and benchmark harness.','Use as one benchmark family; report dataset version and evaluate cross-dataset generalization.'),
        ('Celeb-DF (CVPR 2020) [8]','Challenging face-manipulation test set.','Include difficult examples and compression/degradation shifts; do not report this score as real-world certainty.'),
        ('Qureshi et al., multimodal deepfake survey (2024) [9]','Image, video, audio and social-media pipeline scope.','Organize media signals, metadata, synchrony checks and open challenges.'),
        ('Bharati et al., explainable deepfake detection (2026) [10]','Examiner review and visual rationale design.','Test whether cues are understandable, faithful, and linked to exact frames; explanations are not proof.'),
        ('Sikos, packet analysis survey (2020) [11]','Network analysis workbench and packet feature inventory.','Map protocol/flow summaries, capture context and packet-level verification.'),
        ('Network forensics review/taxonomy (2016) [14]','Network source schema and research taxonomy.','Structure review of methods and open challenges; do not infer attribution from IP/time alone.'),
        ('NIST AI RMF / CFTT / SWGDE [12,13,15,17]','Governance, test method, quality controls.','Use as practice and method references; verify current versions and scope before operational use.')],[48*mm,50*mm,77*mm],small=True),
    callout('<b>Version rule:</b> record the exact paper/dataset/model/tool version and date. For guidance that is periodically updated, verify the current edition before an operational procedure is approved.')))

# 32 database decision
pages.append(pg('Database blueprint: what goes where','Choose stores by responsibility and keep the authoritative path clear enough that another engineer can reconstruct it.',
    tab(['Data','Primary home','Possible secondary view','Reason'],[
        ('Cases, authority, roles','PostgreSQL','—','Transactional, relational integrity and access control.'),
        ('Artifact metadata, hashes, custody','PostgreSQL','Signed audit archive','Durable registry and auditable lineage.'),
        ('Original/derived bytes','Encrypted object store','Immutable replica','Large binary scale and versioned storage.'),
        ('Normalized observations','PostgreSQL initially','OpenSearch after measured need','Join to provenance; text search can evolve independently.'),
        ('Entity relations','PostgreSQL relations first','FalkorDB projection optional','Graph traversal convenience without dual-source truth.'),
        ('Embeddings','Optional pgvector/local vector store','Search index','Retrieval aid only; every result maps to permitted source text.'),
        ('Run manifests/models','PostgreSQL + MLflow artifact store','Model registry','Experiment reproducibility and model lifecycle.'),
        ('Operational metrics','Metrics backend','Restricted dashboards','Performance and health without storing evidence content.')],[38*mm,47*mm,42*mm,48*mm],small=True),
    P('Technology selection scorecard','H2x'),P('Evaluate auditability, offline operation, query patterns, durability/recovery, case isolation, licensing, skills, deployment cost, exportability, and ability to rebuild from authoritative records. Benchmark on representative data rather than synthetic vendor numbers.'),
    callout('<b>Recommended first version:</b> PostgreSQL + encrypted versioned object storage + asynchronous job broker. Add OpenSearch, FalkorDB, pgvector, or specialized data stores only when a measured product requirement justifies them.')))

# 33 roadmap
pages.append(pg('Implementation roadmap: from one trustworthy loop to a platform','Do not attempt to implement all 124 rows at once. Establish provenance, coverage, and review in a narrow vertical slice first.',
    tab(['Phase','Build','Exit evidence'],[
        ('0. Product foundations','Case model, authority/scope, roles, artifact registry, object vault, custody events, audit.','Case isolation tests pass; originals reconcile by digest; reviewers can inspect provenance.'),
        ('1. First source loop','One authorized file/log source, async ingest, parser registry, known-count fixture.','Expected vs observed counts and parser gaps visible; reproducible replay.'),
        ('2. Investigator dashboard','Case overview, source coverage, evidence library, search, timeline, review inbox, report export.','Each dashboard aggregate drills to records; no hidden partial statuses.'),
        ('3. Correlation and graph','Canonical entities, observed/inferred relations, source dependency, contradiction and alternative view.','Ground-truth identity/correlation tests; measure false attribution and causality.'),
        ('4. AI/media modules','Claim verifier then narrowly scoped media detectors; model registry and abstention.','Cross-domain evaluation, human study, citations, prompt-injection and privacy checks.'),
        ('5. Operational scale','Cloud/IoT/network adapters, high-throughput upload, offline deployment, recovery drills.','Representative benchmarks, restore proof, policy review, support matrix.')],[31*mm,75*mm,69*mm],small=True),
    P('First vertical slice in detail','H2x'),P('Upload a small authorized authentication log → issue case/artifact IDs → compute digest while streaming → store original → register custody and source context → parse in sandbox → compare known record count → create timeline observations with raw and normalized time → show gap/partial state → examiner reviews one finding → export evidence-linked PDF/JSON manifest → rerun from exact tool build.'),
    callout('<b>First research prototype:</b> silent parser-failure detection. Next: claim-to-evidence verification. Third: source-dependency and causality graph. Each gets its own hypothesis, baseline, ground truth, and metrics.')))

# 34 source cautions and disagreements
pages.append(pg('What the supplied materials correct—and what remains open','The PDFs are planning inputs. Their counts, candidate gaps, and proposed stack need to be handled carefully.',
    tab(['Source observation','Treatment in this book'],[
        ('Title says 120; section counts total 124.','The AI/ML domain E contains 14 rows; A–D and F–L contain ten each. This book preserves all 124 IDs.'),
        ('National research shortlist has 12 hypotheses; consolidated map contains BH-1 to BH-17.','Counts are document-specific; the consolidated document adds five ideas from an external comparison. Do not treat the totals as conflicting evidence.'),
        ('BH-13 and BH-17 overlap.','They are linked under parser completeness: silent omissions and semantically incomplete successful output. They remain distinct failure modes in tests when useful.'),
        ('Candidate gaps may already be handled by tools or workflows.','Treat every BH as a hypothesis; inspect versions, editions, plugins, papers, and reproducible behavior before claiming novelty.'),
        ('Suggested technology stack is broad.','Use it as options. Do not install every database, broker, vector engine, and graph system before measuring the need.'),
        ('Claude discussion recommended parser-first; explained FalkorDB is graph, not relational.','Adopt parser coverage as an initial experiment; keep PostgreSQL authoritative and FalkorDB optional pending benchmark/legal/ops checks.')],[61*mm,114*mm],small=True),
    P('Evidence basis of the encyclopedia','H2x'),P('The workspace project files currently describe a React portfolio and contain no SUTRAM forensics backend or dashboard implementation. The product screens, services, schema, and architecture below are therefore proposed requirements synthesized from the source PDFs and conversation—not a reverse-engineered description of existing forensic code.'),
    callout('<b>Research integrity:</b> the terms “feature,” “agent,” and “architecture” describe what is proposed to build. A published paper or public tool is not evidence that SUTRAM already implements it.','warm')))

# Catalog all feature sets. Rows preserve source IDs and paraphrase the feature column.
catalog=[
('A','Evidence collection and acquisition','The dashboard makes source scope, collection status, and missing evidence visible. The acquisition worker records methods and constraints, and it never turns inaccessible data into an empty result.','Source plans, AcquisitionJob, CoverageItem, Artifact, CustodyEvent.','Acquisition worker; coverage validator; case orchestrator.','Cloud forensics, readiness, IoT forensics; Velociraptor for endpoint collection. [1–4]',[
('A1','Incomplete evidence collection','Show source-coverage checklist and alert on missing artifact classes.'),('A2','Device incompatibility','Use pluggable, format-specific acquisition adapters with declared support.'),('A3','Locked devices','Record attempts, authorization, access state, and inaccessible sources.'),('A4','Encryption','Detect encrypted content and track authorized access status; do not imply decryption.'),('A5','Volatile evidence loss','Prioritize live-response steps and record acquisition timestamps.'),('A6','Evidence changes during acquisition','Prefer read-only methods where supported and document unavoidable changes.'),('A7','Remote deletion','Provide authorized preservation workflow and time-sensitive alerts.'),('A8','Proprietary interfaces','Use adapter/plugin framework with parser capability reporting.'),('A9','Damaged devices','Record recovery path and alternative acquisition attempts.'),('A10','Time-sensitive evidence','Track retention deadlines, urgency, and preservation reminders.')]),
('B','Evidence integrity and authenticity','The product separates byte integrity after capture from authenticity before capture. It connects hashes to source metadata, custody transfers, transformation lineage, and independent corroboration.','Artifact, ObjectVersion, DigestCheck, CustodyEvent, ParserBuild, RunManifest.','Integrity validator; custody/audit service; report exporter.','Blockchain-forensics review as a design comparison; NIST CFTT/CFReDS for tool validation. [5,12,13]',[
('B1','Undetected evidence modification','Recalculate and compare cryptographic digests at defined checkpoints.'),('B2','Weak provenance','Record source, collector, acquisition time, method, and authority context.'),('B3','Broken chain of custody','Record transfers, access, and custody changes as append-only events.'),('B4','Hash verification gaps','Automate before/after processing digest checks.'),('B5','Untrusted source data','Apply source-trust labels and corroboration checks.'),('B6','Metadata manipulation','Compare metadata against independent logs and file-system records.'),('B7','Synthetic or manipulated media','Screen media with explicit uncertainty, model/version, and limitations.'),('B8','Inadequate tool validation','Maintain parser validation fixtures and tool-version registry.'),('B9','Transformation traceability','Link every extracted or transformed item to its parent artifact.'),('B10','Unreproducible results','Version inputs, tools, parameters, and execution records.')]),
('C','Multi-source evidence correlation','The case workspace unifies search while preserving each source-native value. Candidate links are explainable; duplicate or dependent reports are not miscounted as independent corroboration.','Observation, Entity, Relation, SourceDependency, Conflict, CaseSearch.','Correlation worker; entity resolver; source-dependency analyzer.','Cloud logs, network-forensics surveys, Timesketch, Zeek, PostgreSQL/NetworkX. [4,11,14]',[
('C1','Fragmented evidence','Provide unified case search across email, browser, and other sources.'),('C2','Incompatible formats','Parse into a canonical schema while retaining source-specific values.'),('C3','Duplicate records','Detect exact and near duplicates while preserving all source references.'),('C4','Conflicting records','Surface conflicts and keep each source value unchanged.'),('C5','Entity resolution','Suggest matches with confidence and examiner review.'),('C6','Inconsistent timestamps','Normalize time but retain raw values, timezone, and clock context.'),('C7','Hidden relationships','Create evidence-linked entity/artifact relationship graph.'),('C8','Incomplete source coverage','Show source availability and explicit missing coverage.'),('C9','Synchronization ambiguity','Compare hashes, timestamps, metadata, and transfer logs.'),('C10','Correlation mistaken for causation','Label observed relationships separately from causal hypotheses.')]),
('D','Timeline and incident reconstruction','The timeline shows event, log, and ingestion times, plus timezone, precision, clock reliability, contradictions, and coverage gaps. Multiple narratives can be preserved.','TimelineEvent, ClockAssessment, SourceCoverage, Hypothesis, ReviewDecision.','Timeline normalizer; gap detector; hypothesis/contradiction reviewer.','Timesketch; cloud-log review; packet-analysis/network-forensics surveys. [4,11,14]',[
('D1','Missing events','Show timeline gaps and missing-source indicators.'),('D2','Clock drift','Estimate offsets from trusted reference events and report uncertainty.'),('D3','Time-zone errors','Convert for search while displaying raw time and zone.'),('D4','Delayed logging','Separate event, record/log, and ingestion times.'),('D5','Event-order ambiguity','Represent uncertain ordering; do not invent a total order.'),('D6','Inconsistent narratives','Compare records side by side and surface contradictions.'),('D7','False causal inference','Present hypotheses, alternatives, and exact evidence links.'),('D8','Uncertain attribution','Keep device identity separate from human identity.'),('D9','Gaps in event sequence','Visualize coverage and unresolved intervals.'),('D10','Uncertainty concealment','Expose assumptions, confidence, uncertainty, and provenance.')]),
('E','AI and machine-learning limitations','AI outputs are versioned observations with evidence references and limitations. Thresholds, calibration, drift, subgroup coverage, and human review are dashboard features.','ModelBuild, DatasetManifest, InferenceRun, ClaimEvidence, ReviewDecision.','ML evaluator; calibration/drift monitor; claim verifier; human reviewer.','ML forensics SLR; AI RMF; MLflow/Evidently; research datasets. [6,15]',[
('E1','False positives','Tune thresholds against validation data and route alerts to human review.'),('E2','False negatives','Measure recall and combine validated complementary rules.'),('E3','Biased training data','Report dataset coverage and subgroup performance.'),('E4','Poor generalization','Evaluate across datasets, devices, sources, and versions.'),('E5','Limited explainability','Provide interpretable, evidence-linked reasons and known limitations.'),('E6','Hallucinated conclusions','Ground generation in source spans; validate references and abstain.'),('E7','Automation bias','Require examiner review for consequential claims.'),('E8','Mis-calibrated confidence','Calibrate scores and show reliability, not raw confidence alone.'),('E9','Distribution shift','Monitor drift and out-of-distribution input.'),('E10','Weak evaluation','Publish precision, recall, F1, PR-AUC, confusion matrix, and slices.'),('E11','Inconsistent AI outputs','Version prompts; validate structured output; use deterministic checks.'),('E12','Poor model provenance','Track model, weights, dataset, config, and inference run.'),('E13','Unverified AI summaries','Link every material claim to exact evidence and check contradictions.'),('E14','Human-review gaps','Require approval workflow and named examiner sign-off.')]),
('F','Cybersecurity and anti-forensics','The platform detects suspicious gaps and manipulations as leads, while preserving source context. Hostile evidence is sandboxed and model-facing content is untrusted.','CoverageGap, IntegrityAlert, ParserIncident, MemoryAcquisition, AuditEvent.','Parser sandbox; anomaly/rule worker; memory/disk specialists.','Autopsy/TSK, Volatility 3, Zeek, NIST tool testing; prompt injection evaluation. [12,13]',[
('F1','Deliberate log deletion','Detect logging gaps and compare independent sources.'),('F2','Data wiping','Analyze residual artifacts and file-system metadata when available.'),('F3','Steganography','Route suspicious media to specialist steganalysis.'),('F4','Encrypted containers','Detect protected containers and record access state.'),('F5','Memory-only artifacts','Provide prioritized live-response and memory-analysis procedures.'),('F6','Timestamp manipulation','Compare timestamps with independent records.'),('F7','Log poisoning','Flag malformed entries and cross-source inconsistency.'),('F8','Tool interference','Sandbox parsers; enforce file and dependency limits.'),('F9','Evidence-store tampering','Apply access control, integrity checks, and protected audit records.'),('F10','Adversarial AI inputs','Isolate inputs; test model robustness and validate independently.')]),
('G','Multimedia forensics and deepfakes','Media analysis preserves originals and creates traceable derivatives for frame/audio analysis. Results remain quality- and domain-qualified, with an inconclusive option.','MediaArtifact, Derivative, FrameSample, DetectorRun, QualityFlag, ClaimEvidence.','Media decoder; detector workers; cross-modal checker; examiner reviewer.','FaceForensics++, Celeb-DF, multimodal deepfake survey, explainable detection. [7–10]',[
('G1','Deepfake audio','Screen synthetic-voice indicators with uncertainty reporting.'),('G2','Deepfake video','Run evaluated video manipulation detectors and retain frame-level outputs.'),('G3','Image manipulation','Screen for insertion/removal artifacts and link findings to regions.'),('G4','Metadata stripping','Preserve available metadata and flag absent fields.'),('G5','Compression artifacts','Track encoding history and test quality-aware performance.'),('G6','Synthetic speech','Use calibrated audio classification; expose thresholds and limits.'),('G7','Audio-video mismatch','Analyze synchronization as a candidate anomaly.'),('G8','Source attribution','Compare metadata, provenance, and independent corroborating records.'),('G9','Detector generalization','Evaluate across datasets and unseen generation methods.'),('G10','Authenticity overclaiming','Combine signals and explicitly avoid a definitive single-detector verdict.')]),
('H','Cloud, network, and IoT forensics','Connector-specific metadata makes distributed sources inspectable without overstating accessible content, identity, or completeness.','ProviderRequest, NetworkCapture, DeviceProfile, CoverageItem, Session, Observation.','Cloud connector; network parser; IoT adapter; source availability checker.','Cloud/IoT surveys, cloud logs, packet analysis; Zeek/Wireshark. [1–4,11,14]',[
('H1','Distributed cloud evidence','Connect authorized provider exports inside one case workspace.'),('H2','Provider-controlled access','Track requests, permission status, and unavailable records.'),('H3','Ephemeral cloud records','Track retention and provide preservation reminders.'),('H4','Multi-tenant risk','Enforce strict case and tenant isolation.'),('H5','Proprietary IoT formats','Use device-specific adapters and parsers.'),('H6','Limited device documentation','Record schema confidence and parser documentation.'),('H7','Ambiguous network attribution','Correlate IP, time, session, and other authorized records cautiously.'),('H8','Encrypted communications','Analyze accessible metadata without claiming plaintext recovery.'),('H9','Missing network logs','Surface capture/log gaps and compare independent sources.'),('H10','Cross-device duplication','Deduplicate while preserving every source reference.')]),
('I','Legal, privacy, and ethical challenges','Authority, purpose, jurisdiction, minimization, and examiner accountability constrain collection, analysis, export, and AI routing.','AuthorityRecord, ScopeVersion, RetentionPolicy, Hold, ReviewDecision, ExportLog.','Policy engine; privacy filter; access auditor; report reviewer.','Cloud forensic readiness, IoT privacy survey, SWGDE current guidance. [2,3,17]',[
('I1','Incomplete custody records','Export a traceable chain-of-custody report.'),('I2','Poor acquisition documentation','Require method, source context, and examiner notes.'),('I3','Unvalidated methods','Maintain validation suite and documented limitations.'),('I4','Unexplained AI findings','Provide evidence-linked findings and reproducible analysis records.'),('I5','Privacy overcollection','Apply scope filters and access restrictions.'),('I6','Unclear legal authority','Record authority and enforce source scope before acquisition.'),('I7','Cross-border restrictions','Record jurisdiction and require approved collection workflow.'),('I8','Sensitive data exposure','Use approved AI routing, minimization, and local inference when required.'),('I9','Contradictory evidence omitted','Require contradiction review and balanced evidence presentation.'),('I10','Unclear accountability','Record named examiner approval and sign-off history.')]),
('J','Data engineering and interoperability','Schema contracts preserve source meaning while enabling search, deduplication, reproducible parsing, and safe retention.','CanonicalSchemaVersion, RawFieldSet, ParserRun, ArtifactLineage, SearchIndexState.','Schema validator; encoding normalizer; deduplicator; indexer.','Pydantic, Pandas, PostgreSQL; Forensic Artifacts schema catalog; NIST test sets. [12,13]',[
('J1','Inconsistent schemas','Adopt versioned canonical evidence schema.'),('J2','Encoding failures','Detect encodings and normalize Unicode without altering originals.'),('J3','Duplicate ingestion','Hash content and warn on repeated datasets.'),('J4','Incorrect normalization','Preserve raw fields alongside normalized values.'),('J5','Missing source identifiers','Assign stable artifact and source-record IDs.'),('J6','Malformed files','Validate schemas, safely parse, and quarantine failures.'),('J7','Slow searches','Index high-value fields and full text as workload requires.'),('J8','Excessive retention','Use configurable retention and approved deletion workflow.'),('J9','Version incompatibility','Pin parsers and run regression tests.'),('J10','Lost provenance','Maintain parent-child lineage for every transformation.')]),
('K','Performance, scalability, and operations','The dashboard shows job states, throughput, queue delay, resource use, cost, and recovery without sacrificing validation or provenance.','JobState, QueueMetric, UsageRecord, AuditEvent, RecoveryDrill.','Async orchestrator; worker pools; backpressure manager; ops monitor.','FastAPI/Celery/Redis patterns; MLflow cost tracking; cloud readiness. [3,6]',[
('K1','Large evidence volumes','Use chunked ingestion and background processing.'),('K2','Long processing times','Provide async tasks and visible progress.'),('K3','High infrastructure costs','Measure model/resource cost; select models and caching carefully.'),('K4','Specialist dependency','Guide users with plain-language explanations and workflows.'),('K5','Inconsistent procedures','Use versioned, repeatable workflow configuration.'),('K6','Tool fragmentation','Present a unified dashboard with integrated service APIs.'),('K7','Poor case management','Connect evidence, notes, and findings to a case.'),('K8','Limited auditability','Maintain centralized, tamper-evident access history.'),('K9','No comparable benchmarks','Run repeatable benchmark datasets and publish conditions.'),('K10','Offline deployment constraints','Support self-hosted services and validated local models.')]),
('L','Security of the forensic platform','Security controls protect the evidence chain and prevent the analysis system from becoming an exfiltration or manipulation path.','Identity, RoleGrant, AuditEvent, ParserSandbox, SecretRef, BackupRestoreRecord.','Auth/policy service; secure build pipeline; backup/recovery worker.','NIST AI RMF, SWGDE, software supply-chain and isolated parser controls. [15,17]',[
('L1','Unauthorized access','Authenticate users and enforce case-level permissions.'),('L2','Privilege escalation','Apply server-side role checks and least privilege.'),('L3','Audit tampering','Restrict append-only audit writes and verify integrity.'),('L4','Malicious uploads','Validate files, enforce limits, and isolate parsers.'),('L5','Prompt injection','Treat artifact content as untrusted; restrict instructions and tools.'),('L6','Retrieval contamination','Use source-aware, permission-filtered evidence retrieval.'),('L7','External AI leakage','Control model routing, redaction, and local processing.'),('L8','Compromised dependencies','Pin, inventory, scan, and review dependencies.'),('L9','Backup compromise','Encrypt backups, restrict access, and test restore.'),('L10','Failure recovery','Checkpoint tasks, use transactional records, and document recovery.')]),
]

for code,title,intro,records,agents,papers,items in catalog:
    pages.append(pg(f'Feature encyclopedia {code}: {title}',intro,
        tab(['ID','Problem the product must handle','Planned dashboard / system behavior'],[(i,p,f) for i,p,f in items],[14*mm,58*mm,103*mm],small=True),
        P('Where this appears in the product','H2x'),P(f'<b>Dashboard:</b> {intro} <b>Records:</b> {records} <b>Workers:</b> {agents} <b>Research connection:</b> {papers}','SmallX'),
        callout('<b>Acceptance principle:</b> store the source context, expose gaps and uncertainty, and test the behavior against controlled cases before describing it as validated.','blue')))

# BH appendix page
bh=[
('1','Integrity mistaken for authenticity','Hash proves post-capture stability, not source truth. Test pre-altered and post-altered inputs.'),('2','Misleading correlation / false causation','Separate observations from inferred edges; measure false causal attribution.'),('3','Unsupported or meaning-shifted AI claims','Link claims to exact spans; test speaker, negation, and contradiction preservation.'),('4','Deepfake failure after compression/domain shift','Test robustness, calibration, abstention, and cross-dataset performance.'),('5','Hidden evidence-coverage gaps','Measure missing/unavailable source discovery and false alerts.'),('6','Account/device mistaken for person','Separate identities; measure false attribution.'),('7','Plausible fabricated timeline','Test altered timestamps, logs, and alternative reconstructions.'),('8','Missing records treated as non-occurrence','Classify retention, source availability, logging failure, and true absence.'),('9','False corroboration from dependent sources','Track common origin; measure dependency and false corroboration.'),('10','Unreproducible results/tool disagreement','Replay versions and classify output diffs.'),('11','Prompt injection in evidence','Measure conclusion change, unauthorized action, disclosure, and attack success.'),('12','Failure to abstain','Measure risk-coverage and high-confidence error outside validated domain.'),('13','Silent parser failure','Detect skipped records despite process success.'),('14','Recovered fragments presented as complete','Estimate missing context and completeness limits.'),('15','Live acquisition changes evidence','Separate natural change, acquisition effect, and historical event.'),('16','Investigator disagreement hidden','Preserve alternate readings, reviewer history, and resolution.'),('17','Technically successful but semantically incomplete parser','Report unsupported fields/structures and field-level coverage.')]
pages.append(pg('Research blackholes: 17 testable hypotheses','These are questions to investigate, not established defects in existing products. Verify coverage by versions, editions, plugins, research, and controlled experiments.',
    tab(['BH','Candidate gap','Test focus'],bh,[13*mm,56*mm,106*mm],small=True),
    callout('<b>Overlap:</b> BH-13 and BH-17 are related but test different failure modes: silent record omission versus successful extraction with missing fields or context. The source list’s 12-item shortlist and consolidated 17-item map have different scopes.','warm'),
    P('Recommended sequence','H2x'),P('<b>First:</b> silent parser-failure detector (known-count corpus; no LLM required). <b>Second:</b> evidence-grounded claim verifier. <b>Third:</b> cross-source causality and source-dependency graph. Freeze one hypothesis at a time, define false alarms, run a baseline, test held-out cases, and disclose limitations.')))

# Appendix papers refs
refs=[
('1','Ruan et al. “Cloud Forensics.” IFIP AICT, 2011.','https://opendl.ifip-tc6.org/db/conf/ifip11-9/df2011/RuanCKC11.pdf'),
('2','“A Survey on the Internet of Things (IoT) Forensics: Challenges, Approaches, and Open Issues.” IEEE Communications Surveys & Tutorials, 2020.','https://doi.org/10.1109/COMST.2019.2962586'),
('3','“A Framework for Cloud Forensic Readiness in Organizations.” 2017.','https://doi.org/10.1109/MobileCloud.2017.12'),
('4','Ghosh, De & Majumder. “A Systematic Review of Log-Based Cloud Forensics.” 2021.','https://doi.org/10.1007/978-981-33-4305-4_26'),
('5','“A Systematic Literature Review of Blockchain-Based IoT Forensic Investigation Process Models.” 2022.','https://doi.org/10.1016/j.fsidi.2022.301470'),
('6','Nayerifard et al. “Machine Learning in Digital Forensics: A Systematic Literature Review.” 2023.','https://arxiv.org/abs/2306.04965'),
('7','Rössler et al. “FaceForensics++: Learning to Detect Manipulated Facial Images.” ICCV, 2019.','https://openaccess.thecvf.com/content_ICCV_2019/papers/Rossler_FaceForensics_Learning_to_Detect_Manipulated_Facial_Images_ICCV_2019_paper.pdf'),
('8','Li et al. “Celeb-DF: A Large-Scale Challenging Dataset for DeepFake Forensics.” CVPR, 2020.','https://openaccess.thecvf.com/content_CVPR_2020/html/Li_Celeb-DF_A_Large-Scale_Challenging_Dataset_for_DeepFake_Forensics_CVPR_2020_paper.html'),
('9','Qureshi et al. “Deepfake forensics: a survey of digital forensic methods for multimodal deepfake identification on social media.” PeerJ Computer Science, 2024.','https://peerj.com/articles/cs-2037/'),
('10','Bharati et al. “Explainable deepfake detection: A multi-model framework with human-interpretable rationales for legal investigation purposes.” Machine Learning with Applications, 2026.','https://doi.org/10.1016/j.mlwa.2025.100819'),
('11','Sikos. “Packet analysis for network forensics: A comprehensive survey.” Forensic Science International: Digital Investigation, 2020.','https://doi.org/10.1016/j.fsidi.2019.200892'),
('12','Lyle, Guttman & Ayers. “Ten years of computer forensic tool testing.” NIST, 2011.','https://www.nist.gov/publications/ten-years-computer-forensic-tool-testing'),
('13','NIST. “Digital Investigation Techniques: A NIST Scientific Foundation Review.”','https://www.nist.gov/publications/digital-investigation-techniques-nist-scientific-foundation-review'),
('14','“Network forensics: Review, taxonomy, and open challenges.” Journal of Network and Computer Applications, 2016.','https://doi.org/10.1016/j.jnca.2016.03.005'),
('15','NIST AI Risk Management Framework.','https://www.nist.gov/itl/ai-risk-management-framework'),
('16','FalkorDB public repository and license information; review version-specific terms.','https://github.com/FalkorDB/FalkorDB'),
('17','SWGDE current documents and guidance. Verify applicable revisions.','https://www.swgde.org/documents/current-documents/'),
]
refrows=[(f'[{n}] {t}',f'<link href="{u}" color="#087E8B">Open source ↗</link>') for n,t,u in refs]
pages.append(pg('Selected research and technical references','Use direct links to inspect the source. Confirm bibliographic details, current versions, scope, and applicable guidance before operational use.',
    tab(['Reference','Link'],refrows,[145*mm,30*mm],small=True),
    P('Public project baselines named in the source research map','H2x'),
    P('<b>Timesketch:</b> collaborative timelines and analyst context. <b>Velociraptor:</b> endpoint visibility and live collection. <b>Autopsy / The Sleuth Kit:</b> disk and file-system analysis. <b>Volatility 3:</b> memory forensics. <b>Zeek / Wireshark:</b> network analysis. <b>Forensic Artifacts:</b> artifact definitions. <b>MLflow / Evidently:</b> model experiment tracking and monitoring. <b>NIST CFTT / CFReDS:</b> tool-testing methodology and test data. These are complementary resources, not one unified platform.','SmallX'),
    P('Research mapping for claims','H2x'),P('References [1–5] inform cloud, IoT, readiness, logs, and tamper-evident workflow questions; [6–10] inform ML and multimedia evaluation; [11,14] inform network forensics; [12,13] inform tool testing and scientific foundations; [15,17] inform risk and guidance; [16] is an architecture/technology reference for optional graph storage.'),
    callout('<b>Source files reviewed:</b> 15-page engineering matrix (three byte-identical copies), 2-page national blackholes brief, and 5-page consolidated features / blackholes / research map. This book preserves the original feature IDs and corrects the row count to 124.','blue')))

# Glossary
pages.append(pg('Glossary: plain-language definitions','A compact reference for terms used throughout the architecture.',
    tab(['Term','Plain-language meaning'],[
        ('Artifact','A preserved item of digital evidence, such as a file, export, capture, or image.'),('Canonical schema','A shared set of fields that helps search different sources without erasing source-specific meaning.'),('Chain of custody','A record of who handled, accessed, transferred, or transformed evidence and when.'),('Coverage','A declared comparison between expected evidence sources/records and what was actually available or acquired.'),('Derived artifact','A new output created from an original, with a recorded parent and transformation.'),('Entity resolution','Suggesting that records refer to the same device, account, session, or person, with uncertainty.'),('Evidence graph','A network of entities and relationships whose edges link to supporting evidence.'),('Ingestion time','When SUTRAM received a record; distinct from the event or log time.'),('OOD / out of distribution','Input that differs from data on which a model was validated.'),('Parser manifest','Versioned statement of supported formats, fields, structures, tests, and known gaps.'),('Provenance','Information about an item’s source and the steps it passed through.'),('Abstention','A model or rule declines to make a prediction because support or input quality is insufficient.'),('Source dependence','Multiple documents that ultimately derive from one original source.'),('System of record','The authoritative durable store from which derived indexes and views can be rebuilt.'),('Tamper-evident','Changes can be detected or traced; this alone does not prove the original content was true.'),('Training leakage','Test information improperly influences model training or evaluation, inflating performance.')],[39*mm,136*mm],small=True),
    P('Working rule','H2x'),callout('<b>When in doubt:</b> preserve the original, record the uncertainty, show the source, and ask a reviewer before converting a candidate signal into a conclusion.')))

# Exact pages and build.
story=[]
for i,content in enumerate(pages):
    story.extend(content)
    if i<len(pages)-1: story.append(PageBreak())
doc=BookDoc(OUT)
doc.build(story)
print(f'Pages authored: {len(pages)}; PDF: {OUT.resolve()}')
