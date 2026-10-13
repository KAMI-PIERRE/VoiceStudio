# Deploy Voice Studio

Voice Studio has a Python edition for local/server use and a browser edition for free static hosting. Hosting is not configured until you sign in to a provider and publish the prepared files.

## Free browser edition (recommended for a $0 budget)

The `browser/` edition runs the same twelve Kokoro characters on the visitor's device, with the character portraits, Voice Studio branding, speed/pause controls, preview, playback, and WAV download. Hugging Face Static Spaces are free for every account and do not require PRO or an account older than 30 days. [Static Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-static).

Build and package from the project directory (Node.js 20.19+ or 22.12+ is required by the build tool):

```powershell
.\.venv\Scripts\python.exe scripts\sync_browser_assets.py
cd browser
npm.cmd ci
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe scripts\prepare_static_deploy.py
```

Sign in with the secure browser flow, then create a **Static** Space and upload the static deployment folder printed by the script:

```powershell
.\.venv\Scripts\hf.exe auth login --format agent
.\.venv\Scripts\hf.exe auth whoami
.\.venv\Scripts\hf.exe repos create YOUR_ACCOUNT/voice-studio --repo-type space --sdk static
.\.venv\Scripts\hf.exe upload YOUR_ACCOUNT/voice-studio deployment\voice-studio-static-VERSION . --repo-type space
```

Use a new repository name if `voice-studio` already exists; do not overwrite an existing project accidentally. No paid hardware, inference subscription, API key, or Python server is needed. The static README supplies the required cross-origin isolation headers.

First use downloads approximately 92 MB of quantized model weights plus runtime and selected-voice assets. Browser caching can reduce later downloads but is not guaranteed. Scripts and generated audio stay in the visitor's browser; generation speed and memory depend on the device. The internet is needed to fetch uncached files. Download recordings to keep them. Use a current desktop Chrome or Edge for the initial verification, and test your intended mobile devices before relying on them.

Do not upload the Python deployment ZIP to a Static Space; upload the **static** folder or ZIP instead. For a local browser preview, run `npm.cmd run dev` from `browser/` and open the URL it prints.

## Prepare the upload files

From the project folder:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_deploy.py
```

This creates a versioned folder and ZIP under `deployment/`. Only application source, required configuration, documentation, and visual assets are included. Your local Python environment, model cache, recordings, logs, screenshots, and credentials are excluded.

## Hugging Face Spaces

The root README already declares the Gradio SDK, Gradio 6.30.0, Python 3.12, and `app.py` as the entry point. `requirements.txt` and `packages.txt` supply the Python and Linux dependencies.

### Free hosting

As checked on October 13, 2026, free personal accounts in good standing with a verified email and an account older than 30 days can host up to two **ZeroGPU Gradio Spaces**. Standard CPU Gradio/Docker Spaces require a paid account plan. [Free ZeroGPU eligibility](https://huggingface.co/docs/hub/en/spaces-zerogpu), [Spaces account requirements](https://huggingface.co/docs/hub/en/spaces-overview).

The current app uses CPU ONNX inference and cannot run unchanged on ZeroGPU: ZeroGPU requires a GPU-decorated handler registered with Gradio. A genuine GPU backend adaptation is needed before selecting that hardware; adding an unused GPU handler is not a deployment solution. [Hugging Face's ZeroGPU implementation guidance](https://github.com/huggingface/skills/blob/main/skills/huggingface-spaces/references/zerogpu.md).

Static Spaces are free for all accounts, but serving this Python app as static files will not run its speech engine. A browser inference edition would need a separate JavaScript implementation. Render's free web service has 512 MB of memory; the current app has exceeded that amount in local Windows measurements, so it is not a verified alternative for reliable speech generation. [Render compute plans](https://render.com/docs/compute-plans).

The upload package is ready for the current CPU app. Do not use the CPU creation command below if your requirement is entirely free hosting.

### Standard CPU hosting (requires a paid account plan)

1. Sign in to Hugging Face and create a Space with the **Gradio** SDK and **CPU Basic** hardware.
2. Choose your intended visibility. Public Spaces expose source code and the app; private Spaces require permitted viewers to sign in. Protected Spaces keep source private while the app is publicly accessible.
3. Upload the files inside the prepared deployment folder to the Space repository root, preserving the `assets/` folder.
4. Wait for the build and runtime to reach **Running**. Generate a voice preview to load the model and verify a WAV download.
5. Share the direct `https://...hf.space` app URL for the studio branding and browser icon, or share its Hugging Face Space page.

As checked on October 13, 2026, Hugging Face requires a paid personal PRO or organization Team/Enterprise plan to create standard CPU Gradio/Docker Spaces. CPU Basic has no hourly hardware charge. Do not choose upgraded hardware without reviewing its price. [Current account and resource requirements](https://huggingface.co/docs/hub/en/spaces-overview).

For CLI authentication, use browser sign-in; do not paste tokens into chat:

```powershell
.\.venv\Scripts\hf.exe auth login --format agent
.\.venv\Scripts\hf.exe auth whoami
```

After authentication, substitute your own account and the folder printed by the packaging script:

```powershell
.\.venv\Scripts\hf.exe repos create YOUR_ACCOUNT/voice-studio --repo-type space --sdk gradio --flavor cpu-basic
.\.venv\Scripts\hf.exe upload YOUR_ACCOUNT/voice-studio deployment\voice-studio-VERSION . --repo-type space
```

The first preview downloads and verifies the approximately 145 MB model and voices. Runtime storage on Spaces is ephemeral; the model may need downloading again after a restart.

## Container hosting

The Dockerfile uses Python 3.12 on Debian, installs the required native libraries, runs as UID 1000, and downloads the verified model during the build. Do not upload the Windows `.venv` or local `.models` folder.

```text
docker build -t voice-studio .
docker run --rm -p 7860:7860 voice-studio
```

Open `http://localhost:7860`. On Render or another container host, deploy the Dockerfile and let the host provide `PORT`. Model files are included in the built image, so restarts do not require a model download.

### Render

The root `render.yaml` configures a Docker web service on Render's **Free** plan. To deploy:

1. Push this project to a GitHub or GitLab repository.
2. In Render, choose **New > Blueprint**, connect that repository, and apply the `render.yaml` configuration.
3. Wait for the image build and service health check to complete, then open the service URL.
4. Generate a short recording to check inference and download behavior.

The Free plan is best-effort for this app. Its 512 MB memory limit is below the memory observed for local speech generation, so the service may restart or fail while generating audio. Free services also spin down when idle, making the first request slower, and their filesystem is ephemeral. The model is bundled into each image build, but recordings are temporary and may disappear on restart; the app also expires hosted recordings after 24 hours. Upgrade the Render plan if reliable speech generation is required.

For Docker Spaces instead of the Gradio SDK, change the deployed README frontmatter to `sdk: docker` and `app_port: 7860`; remove `sdk_version`, `python_version`, and `app_file`. The local container can run on other providers without this metadata change.

## Runtime configuration

| Environment variable | Purpose |
| --- | --- |
| `VOICE_STUDIO_HOSTED=1` | Enables hosted defaults and temporary recording retention. Spaces and Render are also detected from their platform environment variables. |
| `GRADIO_SERVER_NAME` | Bind address; hosted defaults to `0.0.0.0`, local defaults to `127.0.0.1`. |
| `PORT` | Hosting server port; takes precedence over `GRADIO_SERVER_PORT`. Default is 7860. |
| `VOICE_STUDIO_MODEL_DIR` | Writable location for model files. |
| `VOICE_STUDIO_OUTPUT_DIR` | Recording location; hosted defaults to a directory under the system temporary folder. |
| `VOICE_STUDIO_RETENTION_SECONDS` | Hosted download lifetime, default 86400 (24 hours). Local default 0 keeps recordings. |

Hosted scripts are processed on the server and require an internet connection from the visitor. Download links expire; they are not private account storage. Gradio clears cached recordings on a 10-minute cleanup schedule after their retention period. Original expired recordings are pruned when the app starts or generates another recording; active partial files are retained. Local recordings keep their previous saved-file behavior.

Run one app process initially: the model cache, download lock, and one-recording queue are process-local. The queue holds up to eight requests. Long scripts can take time on a CPU.

## Deployment checks

- Install dependencies in a fresh Linux Python 3.12 environment or build the container.
- Confirm the host's build and runtime logs show a successful launch on its expected port.
- Check the header logo, tab icon, character portraits, and developer footer on the hosted URL.
- Generate a character preview and confirm playback and WAV download.
- Verify the host's access settings and intended audience before sharing the URL.

Docker is not installed in the current Windows workspace, so the container must be built on the selected host or another machine with Docker. Local runtime configuration, recording cleanup, and package contents can still be checked here.

References: [Gradio Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-gradio), [Spaces configuration](https://huggingface.co/docs/hub/en/spaces-config-reference), [Docker Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-docker), [CLI authentication and uploads](https://huggingface.co/docs/huggingface_hub/en/guides/cli).
