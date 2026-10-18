/**
 * FORENSIC ATLAS — SOVEREIGN DIGITAL FORENSICS INTELLIGENCE
 * 3D Scrollytelling & Interactive HUD Engine
 */

(function() {
  'use strict';

  // ── SOUND SYNTHESIS ENGINE (Web Audio API) ──
  const SoundEngine = {
    ctx: null,
    enabled: true,

    init() {
      if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioCtx();
      }
    },

    resume() {
      if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    },

    playChirp(freq = 880, type = 'sine', duration = 0.08) {
      if (!this.enabled) return;
      this.init();
      this.resume();
      if (!this.ctx) return;

      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(freq * 1.5, this.ctx.currentTime + duration);

        gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start();
        osc.stop(this.ctx.currentTime + duration);
      } catch (e) {}
    },

    playPulse() {
      if (!this.enabled) return;
      this.init();
      this.resume();
      if (!this.ctx) return;

      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(140, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(40, this.ctx.currentTime + 0.35);

        gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.35);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.35);
      } catch (e) {}
    },

    playScanSweep() {
      if (!this.enabled) return;
      this.init();
      this.resume();
      if (!this.ctx) return;

      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(400, this.ctx.currentTime);
        osc.frequency.linearRampToValueAtTime(1200, this.ctx.currentTime + 0.25);

        gain.gain.setValueAtTime(0.03, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.25);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.25);
      } catch (e) {}
    },

    playSuccess() {
      if (!this.enabled) return;
      this.init();
      this.resume();
      if (!this.ctx) return;

      try {
        const now = this.ctx.currentTime;
        const freqs = [587.33, 880, 1174.66]; // D5, A5, D6
        freqs.forEach((f, i) => {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(f, now + i * 0.08);

          gain.gain.setValueAtTime(0.04, now + i * 0.08);
          gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.25);

          osc.connect(gain);
          gain.connect(this.ctx.destination);

          osc.start(now + i * 0.08);
          osc.stop(now + i * 0.08 + 0.25);
        });
      } catch (e) {}
    }
  };

  // ── 3D THREE.JS WEBGL ENGINE ──
  const WebGLScene = {
    canvas: null,
    renderer: null,
    scene: null,
    camera: null,
    monolithGroup: null,
    centralCore: null,
    outerCage: null,
    shards: [],
    particles: null,
    rings: [],
    mouse: { x: 0, y: 0, targetX: 0, targetY: 0 },
    currentLevel: 0,
    isShattered: false,
    isWireframe: false,
    clock: new THREE.Clock(),

    init() {
      this.canvas = document.getElementById('webgl-canvas');
      if (!this.canvas) return;

      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.FogExp2(0x04060a, 0.025);

      this.camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
      this.camera.position.set(0, 0, 14);

      this.renderer = new THREE.WebGLRenderer({
        canvas: this.canvas,
        antialias: true,
        alpha: true
      });
      this.renderer.setSize(window.innerWidth, window.innerHeight);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      this.setupLights();
      this.createMonolith();
      this.createParticleField();
      this.setupEventListeners();
      this.animate();
    },

    setupLights() {
      const ambientLight = new THREE.AmbientLight(0x0c1e34, 1.8);
      this.scene.add(ambientLight);

      const cyanLight = new THREE.PointLight(0x00f2fe, 3, 25);
      cyanLight.position.set(-6, 8, 6);
      this.scene.add(cyanLight);

      const emeraldLight = new THREE.PointLight(0x00ff9d, 2.5, 25);
      emeraldLight.position.set(6, -6, 6);
      this.scene.add(emeraldLight);

      const violetLight = new THREE.PointLight(0xa855f7, 2, 20);
      violetLight.position.set(0, 0, -8);
      this.scene.add(violetLight);
    },

    createMonolith() {
      this.monolithGroup = new THREE.Group();
      this.scene.add(this.monolithGroup);

      // 1. Central Faceted Forensic Prism (Icosahedron)
      const coreGeo = new THREE.IcosahedronGeometry(2.4, 1);
      const coreMat = new THREE.MeshStandardMaterial({
        color: 0x07111e,
        emissive: 0x00334e,
        emissiveIntensity: 0.8,
        metalness: 0.85,
        roughness: 0.25,
        flatShading: true
      });
      this.centralCore = new THREE.Mesh(coreGeo, coreMat);
      this.monolithGroup.add(this.centralCore);

      // 2. Outer Wireframe Cyber Cage (Octahedron)
      const cageGeo = new THREE.OctahedronGeometry(3.6, 1);
      const cageMat = new THREE.MeshBasicMaterial({
        color: 0x00f2fe,
        wireframe: true,
        transparent: true,
        opacity: 0.35
      });
      this.outerCage = new THREE.Mesh(cageGeo, cageMat);
      this.monolithGroup.add(this.outerCage);

      // 3. Rotating Holographic Rings
      const ringGeo1 = new THREE.TorusGeometry(4.2, 0.025, 8, 80);
      const ringMat1 = new THREE.MeshBasicMaterial({
        color: 0x00ff9d,
        transparent: true,
        opacity: 0.55
      });
      const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
      ring1.rotation.x = Math.PI / 3;
      this.monolithGroup.add(ring1);
      this.rings.push(ring1);

      const ringGeo2 = new THREE.TorusGeometry(4.6, 0.025, 8, 80);
      const ringMat2 = new THREE.MeshBasicMaterial({
        color: 0x00f2fe,
        transparent: true,
        opacity: 0.4
      });
      const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
      ring2.rotation.y = Math.PI / 4;
      this.monolithGroup.add(ring2);
      this.rings.push(ring2);

      // 4. Orbiting Forensic Shard Nodes (14 Shards representing 14 Agents)
      const shardGeo = new THREE.TetrahedronGeometry(0.5, 0);
      const shardMat = new THREE.MeshStandardMaterial({
        color: 0x00f2fe,
        emissive: 0x00ff9d,
        emissiveIntensity: 0.4,
        metalness: 0.9,
        roughness: 0.1
      });

      this.shards = [];
      const shardCount = 14;
      for (let i = 0; i < shardCount; i++) {
        const shard = new THREE.Mesh(shardGeo, shardMat.clone());
        const angle = (i / shardCount) * Math.PI * 2;
        const radius = 3.2;
        const yOffset = (Math.random() - 0.5) * 2;

        shard.position.set(
          Math.cos(angle) * radius,
          yOffset,
          Math.sin(angle) * radius
        );

        shard.userData = {
          orbitAngle: angle,
          orbitRadius: radius,
          orbitSpeed: 0.3 + (i % 3) * 0.15,
          yBase: yOffset,
          originPos: shard.position.clone(),
          scatterPos: new THREE.Vector3(
            (Math.random() - 0.5) * 16,
            (Math.random() - 0.5) * 12,
            (Math.random() - 0.5) * 10
          ),
          ringPos: new THREE.Vector3(
            Math.cos(angle) * 5.5,
            Math.sin(angle) * 5.5,
            0
          )
        };

        this.monolithGroup.add(shard);
        this.shards.push(shard);
      }
    },

    createParticleField() {
      const particleCount = 900;
      const positions = new Float32Array(particleCount * 3);
      const colors = new Float32Array(particleCount * 3);

      const colorCyan = new THREE.Color(0x00f2fe);
      const colorEmerald = new THREE.Color(0x00ff9d);
      const colorBlue = new THREE.Color(0x38bdf8);

      for (let i = 0; i < particleCount; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 45;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 45;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 35;

        const choice = Math.random();
        const col = choice < 0.45 ? colorCyan : choice < 0.8 ? colorBlue : colorEmerald;
        colors[i * 3] = col.r;
        colors[i * 3 + 1] = col.g;
        colors[i * 3 + 2] = col.b;
      }

      const particleGeo = new THREE.BufferGeometry();
      particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const particleMat = new THREE.PointsMaterial({
        size: 0.14,
        vertexColors: true,
        transparent: true,
        opacity: 0.65,
        blending: THREE.AdditiveBlending
      });

      this.particles = new THREE.Points(particleGeo, particleMat);
      this.scene.add(this.particles);
    },

    setupEventListeners() {
      window.addEventListener('resize', () => {
        if (!this.camera || !this.renderer) return;
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
      });

      window.addEventListener('mousemove', (e) => {
        this.mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
        this.mouse.targetY = -(e.clientY / window.innerHeight - 0.5) * 2;
      });

      // Pulse injection button
      const pulseBtn = document.getElementById('pulseBlockBtn');
      if (pulseBtn) {
        pulseBtn.addEventListener('click', () => {
          this.triggerPulse();
          SoundEngine.playPulse();
        });
      }

      // Wireframe toggle
      const wireframeBtn = document.getElementById('toggleWireframeBtn');
      if (wireframeBtn) {
        wireframeBtn.addEventListener('click', () => {
          this.toggleWireframe();
          SoundEngine.playChirp(920);
        });
      }
    },

    triggerPulse() {
      if (!this.centralCore) return;
      gsap.to(this.centralCore.scale, {
        x: 1.35, y: 1.35, z: 1.35,
        duration: 0.18,
        yoyo: true,
        repeat: 1,
        ease: 'power2.out'
      });
      gsap.to(this.centralCore.material.emissive, {
        r: 0, g: 0.95, b: 0.99,
        duration: 0.15,
        yoyo: true,
        repeat: 1,
        ease: 'power2.out',
        onComplete: () => {
          this.centralCore.material.emissive.setHex(0x00334e);
        }
      });
      this.shards.forEach((s) => {
        gsap.to(s.scale, {
          x: 1.8, y: 1.8, z: 1.8,
          duration: 0.22,
          yoyo: true,
          repeat: 1
        });
      });
    },

    toggleWireframe() {
      this.isWireframe = !this.isWireframe;
      if (this.centralCore) {
        this.centralCore.material.wireframe = this.isWireframe;
      }
      this.shards.forEach(s => {
        s.material.wireframe = this.isWireframe;
      });
    },

    setShatteredState(shattered) {
      this.isShattered = shattered;
      this.shards.forEach((s, idx) => {
        const target = shattered ? s.userData.scatterPos : s.userData.originPos;
        gsap.to(s.position, {
          x: target.x,
          y: target.y,
          z: target.z,
          duration: 1.2,
          ease: 'power3.out',
          delay: idx * 0.02
        });
      });
    },

    updateLevelVisuals(levelIndex) {
      if (this.currentLevel === levelIndex) return;
      this.currentLevel = levelIndex;

      // Camera & monolith group repositioning based on active section
      switch (levelIndex) {
        case 0: // Intro Hero: Monolith center stage
          gsap.to(this.monolithGroup.position, { x: 0, y: 0, z: 0, duration: 1.2, ease: 'power2.out' });
          gsap.to(this.camera.position, { x: 0, y: 0, z: 14, duration: 1.2, ease: 'power2.out' });
          this.setShatteredState(false);
          break;

        case 1: // 14-Agent Pipeline: Move to left, shards arrange into an orbital ring
          gsap.to(this.monolithGroup.position, { x: -3.8, y: 0.2, z: 0, duration: 1.4, ease: 'power2.out' });
          gsap.to(this.camera.position, { x: -1.5, y: 0, z: 13, duration: 1.4, ease: 'power2.out' });
          this.shards.forEach((s, i) => {
            gsap.to(s.position, {
              x: s.userData.ringPos.x,
              y: s.userData.ringPos.y,
              z: s.userData.ringPos.z,
              duration: 1.2,
              ease: 'power2.out',
              delay: i * 0.03
            });
          });
          break;

        case 2: // 3D Graph Nexus: Center-back, expanded constellation
          gsap.to(this.monolithGroup.position, { x: 3.5, y: -0.5, z: -2, duration: 1.4, ease: 'power2.out' });
          gsap.to(this.camera.position, { x: 1, y: 0, z: 15, duration: 1.4, ease: 'power2.out' });
          this.shards.forEach((s, i) => {
            const spreadX = (Math.sin(i * 1.4) * 6);
            const spreadY = (Math.cos(i * 1.8) * 4);
            const spreadZ = (Math.sin(i * 0.8) * 4);
            gsap.to(s.position, {
              x: spreadX, y: spreadY, z: spreadZ,
              duration: 1.4,
              ease: 'power2.out'
            });
          });
          break;

        case 3: // Deepfake Lab: Oscillating cylindrical audio visualizer ring
          gsap.to(this.monolithGroup.position, { x: -3.6, y: 0, z: -1, duration: 1.4, ease: 'power2.out' });
          gsap.to(this.camera.position, { x: -1.2, y: 0, z: 14, duration: 1.4, ease: 'power2.out' });
          this.shards.forEach((s, i) => {
            const angle = (i / this.shards.length) * Math.PI * 2;
            gsap.to(s.position, {
              x: Math.cos(angle) * 4.2,
              y: Math.sin(i * 1.2) * 2.5,
              z: Math.sin(angle) * 4.2,
              duration: 1.2,
              ease: 'power2.out'
            });
          });
          break;

        case 4: // Evidence Vault: Secure lockup geometry
          gsap.to(this.monolithGroup.position, { x: 3.4, y: 0, z: 0, duration: 1.4, ease: 'power2.out' });
          gsap.to(this.camera.position, { x: 1.2, y: 0, z: 13.5, duration: 1.4, ease: 'power2.out' });
          this.setShatteredState(false);
          break;
      }
    },

    animate() {
      requestAnimationFrame(() => this.animate());

      const delta = this.clock.getDelta();
      const time = this.clock.getElapsedTime();

      // Mouse Parallax Smooth Interpolation
      this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
      this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

      if (this.camera) {
        this.camera.position.x += (this.mouse.x * 0.6 - this.camera.position.x * 0.1) * 0.05;
        this.camera.position.y += (this.mouse.y * 0.6 - this.camera.position.y * 0.1) * 0.05;
      }

      // Rotate Monolith Elements
      if (this.monolithGroup) {
        this.monolithGroup.rotation.y = time * 0.15;
        this.monolithGroup.rotation.x = Math.sin(time * 0.1) * 0.1;
      }

      if (this.centralCore) {
        this.centralCore.rotation.y = -time * 0.25;
        this.centralCore.rotation.z = time * 0.15;
      }

      if (this.outerCage) {
        this.outerCage.rotation.x = time * 0.2;
        this.outerCage.rotation.y = time * 0.3;
      }

      this.rings.forEach((ring, idx) => {
        ring.rotation.z = time * (0.2 + idx * 0.1);
        ring.rotation.x = Math.sin(time * 0.3 + idx) * 0.5;
      });

      // Shard dynamics when in default orbit
      if (!this.isShattered && this.currentLevel === 0) {
        this.shards.forEach((shard, idx) => {
          const u = shard.userData;
          const currentAngle = u.orbitAngle + time * u.orbitSpeed;
          shard.position.x = Math.cos(currentAngle) * u.orbitRadius;
          shard.position.z = Math.sin(currentAngle) * u.orbitRadius;
          shard.position.y = u.yBase + Math.sin(time * 1.5 + idx) * 0.3;
          shard.rotation.x += 0.02;
          shard.rotation.y += 0.03;
        });
      }

      // Rotate Background Starfield Particles
      if (this.particles) {
        this.particles.rotation.y = time * 0.02;
        this.particles.rotation.x = time * 0.01;
      }

      this.renderer.render(this.scene, this.camera);
    }
  };

  // ── 14-AGENT DATA & CONTROLLER ──
  const AgentController = {
    agents: [
      {
        id: "case-orchestrator",
        name: "Case Orchestrator",
        domain: "Cross-Layer",
        mode: "Deterministic Hybrid",
        status: "ACTIVE",
        desc: "Coordinates scoped case, graph, media, and research tools into a cited examiner brief. Enforces cite-or-drop proof policies.",
        rules: "Grounds every fact card into an explicit artifact ID. Rejects unverified inference."
      },
      {
        id: "case-summary",
        name: "Cited Case Summary",
        domain: "Evidence Summary",
        mode: "Local LLM (Qwen 3.5)",
        status: "ACTIVE",
        desc: "Air-gapped local Qwen 3.5 selects and orders verified fact cards for an extractive examiner draft with zero cloud leaks.",
        rules: "Selects verified fact IDs only; never generates hallucinations or ungrounded claims."
      },
      {
        id: "graph-context",
        name: "Graph Context Agent",
        domain: "FalkorDB Graph",
        mode: "Tool + Rules",
        status: "ACTIVE",
        desc: "Finds bounded, source-linked entity paths across FalkorDB. Discovers compromised accounts, sessions, and host traversal.",
        rules: "Executes bounded Cypher path traversals up to 4 hops; validates node origin state."
      },
      {
        id: "timeline-normalizer",
        name: "Timeline Normalizer",
        domain: "Timeline",
        mode: "Deterministic ISO",
        status: "ACTIVE",
        desc: "Normalizes divergent system clock logs. Converts timestamps only when an explicit timezone offset is present.",
        rules: "Preserves raw source clock string side-by-side with UTC normalizations."
      },
      {
        id: "review-triage",
        name: "Review Triage",
        domain: "Examiner Review",
        mode: "Precise Dependency",
        status: "ACTIVE",
        desc: "Calculates an optimal review queue from source dependencies, prioritizing unverified exfiltration indicators.",
        rules: "Scores items based on credential tier, exfiltration volume, and time window."
      },
      {
        id: "media-context",
        name: "Media Metadata Context",
        domain: "Media Integrity",
        mode: "FFprobe Inspector",
        status: "ACTIVE",
        desc: "Extracts container metadata, stream codecs, bitrate shifts, and muxing timestamps across uploaded video/audio.",
        rules: "Flags container creation mismatch and missing encoder signatures."
      },
      {
        id: "media-forensics",
        name: "AASIST-L Voice Screener",
        domain: "Deepfake / Audio",
        mode: "AASIST-L Acoustic Model",
        status: "GATED",
        desc: "Windowed spectral and phase analysis screening for synthesized voice clones and adversarial speech splices.",
        rules: "Screening output is strictly advisory; never issues unverified judicial verdicts."
      },
      {
        id: "case-memory",
        name: "Case Memory & Handoffs",
        domain: "Cross-Layer",
        mode: "FalkorDB Episodes",
        status: "ACTIVE",
        desc: "Persists case-scoped episodes, review decisions, and versioned multi-specialist handoffs with cryptographic trails.",
        rules: "Stores immutable episodes with SHA-256 provenance in dedicated case graph."
      }
    ],

    selectedAgent: null,

    init() {
      this.selectedAgent = this.agents[0];
      this.renderAgentCards();
      this.setupFilters();
      this.setupSimulator();
    },

    renderAgentCards(filter = 'ALL') {
      const grid = document.getElementById('agentsGrid');
      if (!grid) return;

      grid.innerHTML = '';
      const list = filter === 'ALL' 
        ? this.agents 
        : this.agents.filter(a => a.domain.toUpperCase().includes(filter.toUpperCase()));

      list.forEach(agent => {
        const card = document.createElement('div');
        card.className = `agent-card-item ${this.selectedAgent && this.selectedAgent.id === agent.id ? 'selected' : ''}`;
        card.innerHTML = `
          <div class="agent-card-top">
            <span class="agent-name">${agent.name}</span>
            <span class="agent-mode-badge">${agent.mode}</span>
          </div>
          <p class="agent-desc-short">${agent.desc}</p>
        `;

        card.addEventListener('click', () => {
          document.querySelectorAll('.agent-card-item').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          this.selectedAgent = agent;
          SoundEngine.playChirp(750);
          this.updateAgentSpecsDisplay(agent);
        });

        grid.appendChild(card);
      });
    },

    setupFilters() {
      const tabs = document.querySelectorAll('.agent-tab-btn');
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          tabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          const filter = tab.getAttribute('data-filter') || 'ALL';
          SoundEngine.playChirp(600);
          this.renderAgentCards(filter);
        });
      });
    },

    updateAgentSpecsDisplay(agent) {
      const nameEl = document.getElementById('simCurrentAgentName');
      if (nameEl) nameEl.textContent = agent.name;
    },

    setupSimulator() {
      const simBtn = document.getElementById('runAgentSimBtn');
      const consoleStream = document.getElementById('simConsoleStream');
      if (!simBtn || !consoleStream) return;

      simBtn.addEventListener('click', () => {
        SoundEngine.playChirp(1040);
        simBtn.disabled = true;
        simBtn.innerHTML = `<span>SYNTHESIZING BRIEF...</span>`;

        consoleStream.innerHTML = '';
        const lines = [
          { time: '00:00.12', tag: 'INIT', tagCls: 'cyan', msg: 'Case Orchestrator reading workspace DF-24-017 snapshot...' },
          { time: '00:00.34', tag: 'INGEST', tagCls: 'cyan', msg: 'Loaded 28 registered artifacts. SHA-256 byte digests validated.' },
          { time: '00:00.68', tag: 'GRAPH', tagCls: 'green', msg: 'FalkorDB graph agent traversing: Okta Session -> Host WS-ENG-402 -> C2 198.51.100.42' },
          { time: '00:01.05', tag: 'TIMELINE', tagCls: 'cyan', msg: 'Timeline Normalizer resolved 412 events to monotonic UTC sequence.' },
          { time: '00:01.42', tag: 'LOCAL-LLM', tagCls: 'amber', msg: 'Local Qwen 3.5 selecting verified fact cards: [FACT-01, FACT-03, FACT-07].' },
          { time: '00:01.88', tag: 'VERIFIED', tagCls: 'green', msg: 'Cited Case Brief generated. Envelope SHA-256: 7f89d0e2... SEALED.' }
        ];

        lines.forEach((l, i) => {
          setTimeout(() => {
            const row = document.createElement('div');
            row.className = 'sim-line';
            row.innerHTML = `
              <span class="sim-time">[${l.time}]</span>
              <span class="sim-tag ${l.tagCls}">${l.tag}</span>
              <span>${l.msg}</span>
            `;
            consoleStream.appendChild(row);
            consoleStream.scrollTop = consoleStream.scrollHeight;
            SoundEngine.playChirp(600 + i * 80);

            if (i === lines.length - 1) {
              simBtn.disabled = false;
              simBtn.innerHTML = `<span>EXECUTE CASE SYNTHESIS &rarr;</span>`;
              SoundEngine.playSuccess();
            }
          }, (i + 1) * 320);
        });
      });
    }
  };

  // ── FALKORDB INTERACTIVE GRAPH CANVAS ──
  const GraphVisualizer = {
    canvas: null,
    ctx: null,
    nodes: [],
    edges: [],
    selectedNode: null,
    hoveredNode: null,
    pulsePos: 0,
    animationFrameId: null,

    init() {
      this.canvas = document.getElementById('graphInteractiveCanvas');
      if (!this.canvas) return;
      this.ctx = this.canvas.getContext('2d');

      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());

      this.setupGraphData();
      this.setupInteractivity();
      this.setupPresetButtons();
      this.render();
    },

    resizeCanvas() {
      const rect = this.canvas.getBoundingClientRect();
      this.canvas.width = rect.width * (window.devicePixelRatio || 1);
      this.canvas.height = rect.height * (window.devicePixelRatio || 1);
      this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    },

    setupGraphData() {
      const w = this.canvas.clientWidth || 500;
      const h = this.canvas.clientHeight || 290;

      this.nodes = [
        { id: 'n1', label: 'Alex Rivera', type: 'Lead Examiner', x: w * 0.18, y: h * 0.45, color: '#38bdf8', r: 16 },
        { id: 'n2', label: 'Session e89a', type: 'Okta Session', x: w * 0.38, y: h * 0.3, color: '#00f2fe', r: 14 },
        { id: 'n3', label: 'WS-ENG-402', type: 'Endpoint Device', x: w * 0.58, y: h * 0.32, color: '#00ff9d', r: 15 },
        { id: 'n4', label: 'archive_northstar.tar', type: 'Exfiltrated File', x: w * 0.78, y: h * 0.42, color: '#ffb703', r: 15 },
        { id: 'n5', label: '198.51.100.42', type: 'C2 Network Endpoint', x: w * 0.88, y: h * 0.72, color: '#ff3366', r: 14 },
        { id: 'n6', label: 'Alert #904', type: 'DLP Detection', x: w * 0.48, y: h * 0.75, color: '#a855f7', r: 13 }
      ];

      this.edges = [
        { from: 'n1', to: 'n2', label: 'AUTHENTICATED_AS', active: true },
        { from: 'n2', to: 'n3', label: 'OBSERVED_ON', active: true },
        { from: 'n3', to: 'n4', label: 'DOWNLOADED', active: true },
        { from: 'n4', to: 'n5', label: 'TRANSFERRED_FROM', active: true },
        { from: 'n3', to: 'n6', label: 'TRIGGERED', active: false }
      ];

      this.selectedNode = this.nodes[3]; // Default to target file
      this.updateInspectPanel(this.selectedNode);
    },

    setupInteractivity() {
      const getPos = (e) => {
        const rect = this.canvas.getBoundingClientRect();
        return {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        };
      };

      this.canvas.addEventListener('mousemove', (e) => {
        const pos = getPos(e);
        this.hoveredNode = null;
        for (const n of this.nodes) {
          const dist = Math.hypot(n.x - pos.x, n.y - pos.y);
          if (dist <= n.r + 6) {
            this.hoveredNode = n;
            this.canvas.style.cursor = 'pointer';
            break;
          }
        }
        if (!this.hoveredNode) this.canvas.style.cursor = 'default';
      });

      this.canvas.addEventListener('click', (e) => {
        const pos = getPos(e);
        for (const n of this.nodes) {
          const dist = Math.hypot(n.x - pos.x, n.y - pos.y);
          if (dist <= n.r + 6) {
            this.selectedNode = n;
            this.updateInspectPanel(n);
            SoundEngine.playChirp(840);
            break;
          }
        }
      });
    },

    setupPresetButtons() {
      const btnExfil = document.getElementById('cypherExfilPathBtn');
      const btnAll = document.getElementById('cypherAllNodesBtn');
      const btnLateral = document.getElementById('cypherLateralBtn');

      if (btnExfil) {
        btnExfil.addEventListener('click', () => {
          this.edges.forEach(e => e.active = true);
          SoundEngine.playChirp(900);
          this.pulseEdges();
        });
      }

      if (btnAll) {
        btnAll.addEventListener('click', () => {
          this.edges.forEach(e => e.active = true);
          SoundEngine.playChirp(700);
        });
      }

      if (btnLateral) {
        btnLateral.addEventListener('click', () => {
          this.edges.forEach(e => {
            e.active = (e.from === 'n2' || e.from === 'n3' || e.to === 'n3');
          });
          SoundEngine.playChirp(800);
          this.pulseEdges();
        });
      }
    },

    pulseEdges() {
      this.pulsePos = 0;
      gsap.to(this, {
        pulsePos: 1,
        duration: 0.9,
        ease: 'power2.inOut'
      });
    },

    updateInspectPanel(node) {
      const nameEl = document.getElementById('insEntityName');
      const typeEl = document.getElementById('insEntityType');
      const statusEl = document.getElementById('insEntityStatus');

      if (nameEl) nameEl.textContent = node.label;
      if (typeEl) typeEl.textContent = node.type;
      if (statusEl) {
        statusEl.textContent = node.id === 'n4' || node.id === 'n5' ? 'EXFILTRATION SUSPECT' : 'VERIFIED EVIDENCE';
        statusEl.className = node.id === 'n4' || node.id === 'n5' ? 'entity-val crimson' : 'entity-val green';
      }
    },

    render() {
      this.animationFrameId = requestAnimationFrame(() => this.render());
      const w = this.canvas.clientWidth;
      const h = this.canvas.clientHeight;
      if (!w || !h) return;

      this.ctx.clearRect(0, 0, w, h);

      // Draw Edges
      for (const edge of this.edges) {
        const fromNode = this.nodes.find(n => n.id === edge.from);
        const toNode = this.nodes.find(n => n.id === edge.to);
        if (!fromNode || !toNode) continue;

        this.ctx.beginPath();
        this.ctx.moveTo(fromNode.x, fromNode.y);
        this.ctx.lineTo(toNode.x, toNode.y);

        if (edge.active) {
          this.ctx.strokeStyle = 'rgba(0, 242, 254, 0.45)';
          this.ctx.lineWidth = 2;
        } else {
          this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
          this.ctx.lineWidth = 1;
        }
        this.ctx.stroke();

        // Edge Laser Pulse
        if (edge.active && this.pulsePos > 0 && this.pulsePos < 1) {
          const px = fromNode.x + (toNode.x - fromNode.x) * this.pulsePos;
          const py = fromNode.y + (toNode.y - fromNode.y) * this.pulsePos;
          this.ctx.beginPath();
          this.ctx.arc(px, py, 4, 0, Math.PI * 2);
          this.ctx.fillStyle = '#00ff9d';
          this.ctx.shadowColor = '#00ff9d';
          this.ctx.shadowBlur = 10;
          this.ctx.fill();
          this.ctx.shadowBlur = 0;
        }

        // Edge Label (Midpoint)
        const midX = (fromNode.x + toNode.x) / 2;
        const midY = (fromNode.y + toNode.y) / 2;
        this.ctx.font = '8.5px "JetBrains Mono"';
        this.ctx.fillStyle = edge.active ? 'rgba(56, 189, 248, 0.85)' : 'rgba(255, 255, 255, 0.25)';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(edge.label, midX, midY - 4);
      }

      // Draw Nodes
      for (const node of this.nodes) {
        const isSel = this.selectedNode && this.selectedNode.id === node.id;
        const isHov = this.hoveredNode && this.hoveredNode.id === node.id;

        // Outer Glow Ring
        if (isSel || isHov) {
          this.ctx.beginPath();
          this.ctx.arc(node.x, node.y, node.r + 6, 0, Math.PI * 2);
          this.ctx.strokeStyle = node.color;
          this.ctx.lineWidth = 2;
          this.ctx.shadowColor = node.color;
          this.ctx.shadowBlur = 12;
          this.ctx.stroke();
          this.ctx.shadowBlur = 0;
        }

        // Node Body
        this.ctx.beginPath();
        this.ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
        this.ctx.fillStyle = '#0c121e';
        this.ctx.fill();
        this.ctx.strokeStyle = node.color;
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

        // Node Label
        this.ctx.font = 'bold 9.5px "JetBrains Mono"';
        this.ctx.fillStyle = '#ffffff';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(node.label, node.x, node.y + node.r + 14);

        this.ctx.font = '8px "JetBrains Mono"';
        this.ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
        this.ctx.fillText(node.type, node.x, node.y + node.r + 25);
      }
    }
  };

  // ── DEEPFAKE LAB & AUDIO WAVEFORM SCANNER ──
  const DeepfakeScanner = {
    canvas: null,
    ctx: null,
    currentSample: 'sample-a',
    samples: {
      'sample-a': {
        name: 'Lead Examiner Memo (Voice)',
        score: 0.038,
        status: 'AUTHENTIC HUMAN VOICE',
        statusCls: 'green',
        codec: 'AAC-LC (Stereo)',
        rate: '44,100 Hz',
        provenance: 'Observed Mobile Dictation (Hardware Mic)',
        waveformType: 'natural'
      },
      'sample-b': {
        name: 'Synthesized Voice Clone (TTS)',
        score: 0.942,
        status: 'SYNTHETIC SPOOF DETECTED',
        statusCls: 'crimson',
        codec: 'MP3 (MPEG Audio Layer 3)',
        rate: '22,050 Hz (Upsampled)',
        provenance: 'Model Artifact: Phase Inconsistency',
        waveformType: 'flat-synthetic'
      },
      'sample-c': {
        name: 'Wiretap Audio (Splice Tampering)',
        score: 0.785,
        status: 'CONTAINER & SPLICE ANOMALY',
        statusCls: 'amber',
        codec: 'PCM S16LE (WAV)',
        rate: '48,000 Hz',
        provenance: 'Muxing Shift: Discontinuous Room Tone',
        waveformType: 'spliced'
      }
    },

    init() {
      this.canvas = document.getElementById('waveformCanvas');
      if (!this.canvas) return;
      this.ctx = this.canvas.getContext('2d');

      this.setupSampleButtons();
      this.updateDisplay(this.samples['sample-a']);
      this.renderWaveform();
    },

    setupSampleButtons() {
      const btns = document.querySelectorAll('.audio-sample-btn');
      btns.forEach(btn => {
        btn.addEventListener('click', () => {
          btns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const sampleKey = btn.getAttribute('data-sample') || 'sample-a';
          this.currentSample = sampleKey;
          SoundEngine.playScanSweep();
          this.updateDisplay(this.samples[sampleKey]);
        });
      });
    },

    updateDisplay(data) {
      const scoreNum = document.getElementById('spoofScoreVal');
      const scoreTag = document.getElementById('spoofScoreDesc');
      const circleFill = document.getElementById('scoreCircleFill');
      const metaCodec = document.getElementById('metaCodecVal');
      const metaRate = document.getElementById('metaRateVal');
      const metaProv = document.getElementById('metaProvVal');

      if (scoreNum) scoreNum.textContent = data.score.toFixed(3);
      if (scoreTag) {
        scoreTag.textContent = data.status;
        scoreTag.style.color = data.statusCls === 'green' ? '#00ff9d' : data.statusCls === 'amber' ? '#ffb703' : '#ff3366';
      }

      if (circleFill) {
        // Circle circumference ~ 200
        const offset = 200 - (data.score * 200);
        circleFill.style.strokeDashoffset = offset;
        circleFill.style.stroke = data.statusCls === 'green' ? '#00ff9d' : data.statusCls === 'amber' ? '#ffb703' : '#ff3366';
      }

      if (metaCodec) metaCodec.textContent = data.codec;
      if (metaRate) metaRate.textContent = data.rate;
      if (metaProv) metaProv.textContent = data.provenance;
    },

    renderWaveform() {
      requestAnimationFrame(() => this.renderWaveform());
      if (!this.canvas || !this.ctx) return;

      const w = this.canvas.clientWidth;
      const h = this.canvas.clientHeight;
      if (this.canvas.width !== w || this.canvas.height !== h) {
        this.canvas.width = w;
        this.canvas.height = h;
      }

      this.ctx.clearRect(0, 0, w, h);

      // Draw Center Baseline
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      this.ctx.beginPath();
      this.ctx.moveTo(0, h / 2);
      this.ctx.lineTo(w, h / 2);
      this.ctx.stroke();

      // Procedural Audio Waveform Bars
      const bars = 90;
      const barW = w / bars;
      const t = Date.now() * 0.003;
      const sample = this.samples[this.currentSample];

      for (let i = 0; i < bars; i++) {
        let amp = 0.5;
        if (sample.waveformType === 'natural') {
          amp = (Math.sin(i * 0.25 + t) * 0.4 + Math.sin(i * 0.8) * 0.3 + 0.3) * (h * 0.38);
        } else if (sample.waveformType === 'flat-synthetic') {
          amp = (Math.sin(i * 0.4 + t * 2) * 0.15 + 0.5) * (h * 0.32);
        } else {
          // spliced: sudden jump in amplitude
          const spike = (i > 40 && i < 52) ? 1.6 : 0.6;
          amp = (Math.sin(i * 0.3 + t) * 0.35 * spike + 0.25) * (h * 0.35);
        }

        const barX = i * barW;
        const barY = (h - amp) / 2;

        this.ctx.fillStyle = sample.statusCls === 'green' 
          ? 'rgba(0, 255, 157, 0.7)' 
          : sample.statusCls === 'amber'
          ? 'rgba(255, 183, 3, 0.75)'
          : 'rgba(255, 51, 102, 0.8)';

        this.ctx.fillRect(barX + 1, barY, barW - 2, amp);
      }
    }
  };

  // ── EVIDENCE VAULT & CRYPTOGRAPHIC HASHING ENGINE ──
  const EvidenceHasher = {
    sampleFiles: [
      {
        id: 'ART-001',
        name: 'sample_memory_dump.raw',
        size: '4.29 GB',
        type: 'Volatile RAM Capture',
        contentToHash: 'SUTRAM_VOLATILE_RAM_SNAPSHOT_CASE_DF24017_OFFSET_0x7FFF8000'
      },
      {
        id: 'ART-002',
        name: 'pcap_capture_eng_vlan.pcap',
        size: '812.4 MB',
        type: 'Network Packet Stream',
        contentToHash: 'PCAP_ETHERNET_TRAFFIC_TCP_EXFIL_PORT_443_NORTHSTAR_ARCHIVE'
      },
      {
        id: 'ART-003',
        name: 'cctv_server_room_vault.mp4',
        size: '1.45 GB',
        type: 'H.264 Security Footage',
        contentToHash: 'CCTV_FACILITY_NORTHSTAR_CORRIDOR_CAM04_H264_FRAME_SYNC_20261018'
      },
      {
        id: 'ART-004',
        name: 'okta_system_audit.log',
        size: '18.2 MB',
        type: 'Identity Provider JSON',
        contentToHash: 'OKTA_AUTH_EVENT_STREAM_ALEX_RIVERA_CREDENTIAL_ISSUANCE_TOKEN_OKTA'
      }
    ],

    init() {
      this.setupFileCards();
      this.hashString(this.sampleFiles[0].contentToHash, this.sampleFiles[0]);
    },

    setupFileCards() {
      const cards = document.querySelectorAll('.evidence-file-card');
      cards.forEach((card, idx) => {
        card.addEventListener('click', () => {
          cards.forEach(c => c.classList.remove('active'));
          card.classList.add('active');
          const file = this.sampleFiles[idx] || this.sampleFiles[0];
          SoundEngine.playChirp(880);
          this.hashString(file.contentToHash, file);
        });
      });
    },

    async hashString(text, file) {
      const hashEl = document.getElementById('sha256HashOutput');
      const fileEl = document.getElementById('activeHashFilename');
      const timeEl = document.getElementById('activeHashTimestamp');
      const idempEl = document.getElementById('activeIdempToken');

      if (hashEl) hashEl.innerHTML = `<span style="color: #64748b;">COMPUTING SHA-256 DIGEST...</span>`;

      try {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

        if (hashEl) hashEl.textContent = hashHex;
        if (fileEl) fileEl.textContent = `${file.name} (${file.size})`;
        if (timeEl) timeEl.textContent = new Date().toISOString();
        if (idempEl) idempEl.textContent = `IDEMP-${hashHex.substring(0, 12).toUpperCase()}`;

        SoundEngine.playSuccess();
      } catch (e) {
        if (hashEl) hashEl.textContent = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
      }
    }
  };

  // ── SCROLL POSITION & LEVEL SCRUBBER ──
  const ScrollController = {
    sections: [],
    scrubberItems: [],
    scrubberFill: null,

    init() {
      this.sections = Array.from(document.querySelectorAll('.level-section'));
      this.scrubberItems = Array.from(document.querySelectorAll('.scrubber-item'));
      this.scrubberFill = document.getElementById('scrubberFill');

      window.addEventListener('scroll', () => this.handleScroll(), { passive: true });
      this.setupScrubberClicks();
      this.setupNextButton();
    },

    handleScroll() {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = Math.min(Math.max(scrollY / (docHeight || 1), 0), 1);

      if (this.scrubberFill) {
        this.scrubberFill.style.height = `${progress * 100}%`;
      }

      // Find active section
      const scrollMid = scrollY + window.innerHeight * 0.45;
      let activeIndex = 0;

      this.sections.forEach((sec, idx) => {
        const top = sec.offsetTop;
        const height = sec.offsetHeight;
        if (scrollMid >= top && scrollMid < top + height) {
          activeIndex = idx;
        }
      });

      this.scrubberItems.forEach((item, idx) => {
        item.classList.toggle('active', idx === activeIndex);
      });

      // Update Nav Link highlighting
      const navLinks = document.querySelectorAll('.nav-module-link');
      navLinks.forEach((link, idx) => {
        if (idx === activeIndex) {
          link.classList.add('active');
        } else if (!link.classList.contains('highlight')) {
          link.classList.remove('active');
        }
      });

      // Inform WebGL scene
      WebGLScene.updateLevelVisuals(activeIndex);
    },

    setupScrubberClicks() {
      this.scrubberItems.forEach(item => {
        item.addEventListener('click', () => {
          const targetId = item.getAttribute('data-target');
          const targetEl = document.getElementById(targetId);
          if (targetEl) {
            SoundEngine.playChirp(720);
            targetEl.scrollIntoView({ behavior: 'smooth' });
          }
        });
      });
    },

    setupNextButton() {
      const nextBtn = document.getElementById('quickNextBtn');
      if (!nextBtn) return;

      nextBtn.addEventListener('click', () => {
        const scrollY = window.scrollY;
        const currentSec = this.sections.findIndex(s => {
          const top = s.offsetTop;
          return scrollY + 100 < top;
        });

        const target = currentSec !== -1 ? this.sections[currentSec] : this.sections[0];
        if (target) {
          SoundEngine.playChirp(680);
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  };

  // ── MODAL SYSTEM ──
  const ModalController = {
    init() {
      const openArchBtns = document.querySelectorAll('[data-open-modal="architecture"]');
      const openSpecsBtns = document.querySelectorAll('[data-open-modal="agentspecs"]');
      const archModal = document.getElementById('architectureModal');
      const specsModal = document.getElementById('specsModal');
      const closeBtns = document.querySelectorAll('.modal-close-btn');
      const overlays = document.querySelectorAll('.modal-overlay');

      const openModal = (modal) => {
        if (!modal) return;
        modal.classList.add('open');
        SoundEngine.playChirp(920);
      };

      const closeModal = (modal) => {
        if (!modal) return;
        modal.classList.remove('open');
      };

      openArchBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          openModal(archModal);
        });
      });

      openSpecsBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          openModal(specsModal);
        });
      });

      closeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          overlays.forEach(closeModal);
        });
      });

      overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
          if (e.target === overlay) closeModal(overlay);
        });
      });

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') overlays.forEach(closeModal);
      });
    }
  };

  // ── SOUND TOGGLE CONTROLLER ──
  function setupSoundToggle() {
    const btn = document.getElementById('soundToggleBtn');
    const text = document.getElementById('soundText');
    if (!btn || !text) return;

    btn.addEventListener('click', () => {
      SoundEngine.enabled = !SoundEngine.enabled;
      if (SoundEngine.enabled) {
        btn.classList.add('active');
        text.textContent = 'SFX ON';
        SoundEngine.playSuccess();
      } else {
        btn.classList.remove('active');
        text.textContent = 'SFX OFF';
      }
    });
  }

  // ── INITIALIZATION ──
  window.addEventListener('DOMContentLoaded', () => {
    WebGLScene.init();
    AgentController.init();
    GraphVisualizer.init();
    DeepfakeScanner.init();
    EvidenceHasher.init();
    ScrollController.init();
    ModalController.init();
    setupSoundToggle();

    // Shatter button trigger in intro hero
    const shatterTrigger = document.getElementById('shatterMonolithBtn');
    if (shatterTrigger) {
      shatterTrigger.addEventListener('click', () => {
        WebGLScene.setShatteredState(!WebGLScene.isShattered);
        SoundEngine.playPulse();
      });
    }
  });

})();
