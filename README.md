---
title: Voice Studio
emoji: 🎙️
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 6.30.0
python_version: "3.12"
app_file: app.py
fullWidth: true
header: mini
short_description: Twelve English character voices with previews and WAV downloads.
models:
  - hexgrad/Kokoro-82M
tags:
  - text-to-speech
  - kokoro
  - english
---

# Voice Studio

A local English text-to-speech workspace with 12 selectable character voices, voice previews, and downloadable WAV recordings. The interface includes a script editor, live character and word counts, an estimated reading time, sample scripts, speaking-speed controls, and pauses.

## Run on Windows

Use Windows 10/11 and Python 3.12 or 3.11. This app supports Python 3.11–3.13.

1. Double-click `setup_windows.bat`. It reuses an existing `.venv` or creates one and installs the packages.
2. Double-click `start_windows.bat`.
3. Open [http://127.0.0.1:7860](http://127.0.0.1:7860).
4. Choose a character, then click **Preview this voice** to hear a sample.
5. Write or paste your English script, adjust the speed and pauses, and click **Generate speech**.
6. Listen to the recording and download the WAV file.

The first preview or recording downloads approximately 145 MB of model and voice files. Downloads are checked against pinned SHA-256 hashes and cached in `.models/kokoro/`. After the files are cached, speech generation works locally without an internet connection or an API key. Your script is processed on your computer.

You can download the library before opening the app:

```powershell
.\.venv\Scripts\python.exe app.py --download-model
```

Start with an automatically opened browser:

```powershell
.\.venv\Scripts\python.exe app.py --open-browser
```

Use `--port 7861` if port 7860 is already occupied. In an editor, select `.venv/Scripts/python.exe` as the Python interpreter.

## Characters

Each character selects a different pretrained voice. Role names suggest uses; they do not add emotion or impersonate a person.

| Character | Accent | Voice |
| --- | --- | --- |
| Heart | American | Feminine |
| Bella | American | Feminine |
| Nicole | American | Feminine |
| Sarah | American | Feminine |
| Sky | American | Feminine |
| Adam | American | Masculine |
| Michael | American | Masculine |
| Fenrir | American | Masculine |
| Emma | British | Feminine |
| Isabella | British | Feminine |
| George | British | Masculine |
| Fable | British | Masculine |

These are synthetic character voices. Voice cloning and imitations of specific people are not included.

## Recording controls

- Scripts can contain up to **20,000 characters**, including spaces and punctuation.
- Speaking speed ranges from **0.75× to 1.50×**.
- The pause control adds **0–1,000 ms** between sentences and longer script sections.
- Voice preview uses a short sample without replacing your script.
- Generated WAV files are mono, 24 kHz, 16-bit PCM and saved in `outputs/`.
- Long scripts are split into sections and written incrementally to limit memory use. Longer recordings take more time, especially on a CPU.
- The displayed reading time is an estimate; the completed recording shows its actual duration.
- One recording runs at a time. Incomplete recordings are removed when generation fails.

## Model and packages

The app uses the compact, CPU-friendly Kokoro v1.0 INT8 ONNX model and the matching v1.0 voice library. The original single-speaker MMS model has been replaced; PyTorch and Transformers are no longer required by the app.

- [Kokoro model card and Apache 2.0 model license](https://huggingface.co/hexgrad/Kokoro-82M)
- [Official voice catalog](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
- [Kokoro ONNX runtime and MIT code license](https://github.com/thewh1teagle/kokoro-onnx)
- [Pinned model release files and SHA-256 hashes](https://github.com/thewh1teagle/kokoro-onnx/releases/expanded_assets/model-files-v1.1)

The server binds to `127.0.0.1` for local use. In a Hugging Face Space or the supplied container, it binds to `0.0.0.0`. Hosting setup, including the Render Blueprint and its Free plan limitations, is described in [DEPLOYMENT.md](DEPLOYMENT.md). The application does not include visitor accounts.

## Verification

Run the automated recording tests without downloading a model:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

With the app running and model files cached, check actual audio and downloads for every voice:

```powershell
.\.venv\Scripts\python.exe tests\voice_smoke.py
```

Optional browser checks use Microsoft Edge and Playwright. They verify character selection, live counts, samples, clearing the script, and mobile layout, and save screenshots in `artifacts/`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tests\browser_smoke.py
```
