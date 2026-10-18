# Forensic Atlas — Sovereign Digital Forensics Intelligence Platform

Air-gapped digital forensics intelligence platform combining 14 deterministic specialist agents, FalkorDB sub-millisecond knowledge graphs, offline local neural models, and cryptographic chain-of-custody verification.

---

## 📂 Page Hierarchy & Flow

When deployed, the user journey flows seamlessly:

1. **`index.html` (Root `/`)**:
   - The primary **3D WebGL Landing Page**.
   - Features the rotating central Forensic Monolith, 14-Agent deterministic execution simulator, interactive FalkorDB graph canvas, deepfake acoustic waveform scanner, and real-time Web Crypto FIPS SHA-256 evidence hasher.
2. **`cases.html` (`/cases`)**:
   - The **Case Selection Library**.
   - Browse active cases (`DF-24-017 Northstar`, `PUBLIC-NITROBA-2008`, `PUBLIC-MEDIA-TESTS`, `PUBLIC-DEEPFAKE-AUDIO`).
3. **`workspace.html` (`/workspace`)**:
   - The **Interactive Forensic Case Workspace**.
   - Full case investigation suite (Evidence Library, Normalized Timeline, Entity Graph, Hybrid Hub, Deepfake Lab, Cited Reports, and Audit Trail).

---

## 🚀 How to Push to GitHub

From this folder (`landing-page`):

```bash
# 1. Initialize git (if not already done)
git init

# 2. Stage all files
git add .

# 3. Commit
git commit -m "feat: Forensic Atlas sovereign 3D landing page and workspace suite"

# 4. Link your GitHub repository
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git

# 5. Push to GitHub
git push -u origin main
```

---

## ⚡ How to Deploy on Vercel

### Option A: Via Vercel Web Dashboard (Recommended)
1. Go to [vercel.com/new](https://vercel.com/new) and select your GitHub repository.
2. **Root Directory**:
   - If this `landing-page` folder is the repository root, leave it as `./`.
   - If this is inside a subfolder in your repo, set **Root Directory** to `landing-page`.
3. **Framework Preset**: Select **Other** (Static HTML).
4. Click **Deploy**!
   - Vercel will automatically read `vercel.json`.
   - Visitors will **first land on `index.html`** at `https://your-project.vercel.app/`.
   - Clicking **"Live System →"** opens `cases.html`.
   - Selecting a case opens `workspace.html`.

### Option B: Via Vercel CLI
```bash
npm install -g vercel
vercel
```

---

## 🛠️ Architecture & Technologies
- **3D Graphics**: Three.js r128 with custom procedural geometry, floating particle dust field, and mouse parallax.
- **Audio Synthesis**: Native Web Audio API cyber synthesizer (zero external audio file dependencies).
- **Animations**: GSAP 3.12 for smooth scroll-driven morphing.
- **Typography**: Google Fonts (`JetBrains Mono`, `Space Grotesk`).
- **Styling**: Vanilla CSS design system with glassmorphic panels and cyber HUD reticles.
- **Security & Provenance**: Web Crypto API FIPS 180-4 SHA-256 hashing.
