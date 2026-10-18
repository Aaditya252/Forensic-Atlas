# First-time setup: what to download

**Just exploring?** Open https://forensic-atlas.vercel.app/ in a browser. Nothing
needs installing for the fictional public demo.

**Want live Qwen, uploads, audio processing and saved cases?** Install the full
application on your own Windows x64 computer. The public demo cannot access a
different person's laptop. The supplied launcher and model runtime target Windows;
macOS, Linux and Windows ARM do not have a supported installer in this project.

## 1. Install these four tools

| Download | Choose / do this | What it enables |
| --- | --- | --- |
| [Python for Windows](https://www.python.org/downloads/windows/) | Use a 64-bit Python 3.11+ interpreter; enable the installer option to add Python to PATH when available | Application, setup and audio processing |
| [Git for Windows](https://git-scm.com/downloads/win) | Install Git with command-line access | Download and update the project |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Choose Windows AMD64; follow its Windows/WSL requirements, reboot if requested, then open Docker Desktop and wait for its Linux engine | Persistent FalkorDB graph service |
| [FFmpeg](https://ffmpeg.org/download.html) | Under Windows builds, follow the gyan.dev link; download a release essentials ZIP, extract it, and add the folder containing **ffmpeg.exe and ffprobe.exe** to your user PATH | Audio decoding and media metadata |

Docker's current host prerequisites are in its [Windows installation guide](https://docs.docker.com/desktop/setup/install/windows-install/).
For FFmpeg, adding PATH means opening **Edit environment variables for your
account → Path → Edit → New** and selecting the extracted `bin` folder. Reopen
PowerShell after installing tools or changing PATH. Ask your device administrator
if installation or virtualization settings are restricted.

Keep internet access available during setup. Qwen weights alone are about
1.28 GB; Python packages, PyTorch, the model runtime and Docker images need
additional download and disk capacity. Reserve additional storage for evidence.
A dedicated GPU is not required by the supplied CPU launcher. Performance depends
on your hardware; this is not a bundled single-file installer.

## 2. Check the tools

Open a new PowerShell window and run:

```powershell
python --version
git --version
docker info
ffmpeg -version
ffprobe -version
```

Each command should print a version or service information. `docker info` must
show a running server, not only a client. If a command is not recognized, fix its
installation/PATH first. If `python` opens the Store, install/configure the real
Python interpreter and reopen the terminal.

## 3. Download the project and run guided setup

Run these commands from the folder where you want to keep Forensic Atlas:

```powershell
git clone https://github.com/Aaditya252/Forensic-Atlas.git
cd Forensic-Atlas
powershell -ExecutionPolicy Bypass -File scripts/setup_local.ps1 -Start
```

Already cloned the project? Open PowerShell in that folder and run only the last
command. The setup creates `.venv`, installs the full Python requirements, fetches
Qwen and its CPU runtime, fetches AASIST-L, starts the services, and runs readiness
checks. It stops at an error so you can address it before continuing.

**You do not need to find model files manually, train Qwen, obtain an OpenAI API
key, or install Node.js to run this app.** The launcher pulls the pinned FalkorDB
image through Docker. Git contains source and model manifests; large model files
are downloaded by setup.

## 4. Open the app

Open **http://127.0.0.1:8100/**. Choose **Open Workspace**, then **Hybrid agent hub**.
Look for **LOCAL MODEL READY**. Use **Run agents again** for deterministic case
coordination and **Generate new draft** for an actual Qwen summary.

A fresh installation includes the fictional Northstar case. It does not include
the author's saved cases or downloaded public sample packs. Start with your own
non-sensitive test file using **Add test files**. For audio, save a metadata
inspection in **Media analysis**, then use the experimental screen in **Deepfake
lab**. Qwen summarizes verified tool context; it is not a raw-audio or visual
deepfake detector. Review [the hybrid workflow](../README.md#run-qwen-in-the-hybrid-agent-hub).

## 5. Start again later

Open Docker Desktop, then run from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_forensic_atlas.ps1
```

Setup/download commands are for installation; the startup command reuses installed
models and saved data. Keep the project folder in place: moving it requires a
verified migration of stored paths and Docker mounts.

## If something fails

| Message / symptom | Next step |
| --- | --- |
| Missing python, docker, ffmpeg or ffprobe | Install the tool in step 1, check PATH, reopen PowerShell |
| Docker engine unavailable | Open Docker Desktop, finish its requested setup/reboot and confirm `docker info` succeeds |
| Package or model download fails | Read the specific error; check internet access, disk space and network restrictions, then rerun setup |
| Qwen unavailable | Run the startup command; inspect `output/llm.stderr.log` |
| Graph disconnected | Check Docker Desktop and `docker logs forensic-atlas-local-graph` |
| App does not open | Inspect `output/api.stderr.log`; another service may occupy port 8100 |
| Public website has demo data | Use `http://127.0.0.1:8100/` on the computer where you installed the full stack |

For a complete health check, run:

```powershell
.\.venv\Scripts\python.exe scripts/deployment_preflight.py
```

All lines should say **PASS**. Error reports should include the failing step and
relevant error text, with credentials and case details removed.
