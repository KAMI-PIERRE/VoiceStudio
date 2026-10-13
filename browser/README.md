---
title: Voice Studio
emoji: 🎙️
colorFrom: purple
colorTo: indigo
sdk: static
app_file: index.html
header: mini
fullWidth: true
short_description: Twelve character voices, generated on your device
models:
  - onnx-community/Kokoro-82M-v1.0-ONNX
custom_headers:
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
  cross-origin-resource-policy: cross-origin
---

# Voice Studio

Choose one of twelve English characters, preview its voice, and turn your script into a downloadable WAV recording. Speech runs on the visitor's device using Kokoro; the app has no paid inference API or Python server.

First use downloads approximately 92 MB of model weights plus runtime and selected-voice files. Files are cached by the browser when available. Use a current desktop Chrome or Edge for the best starting experience; generation speed and available memory depend on the device. Model downloads require internet access. This edition uses WebAssembly in a worker so the editor remains responsive during generation.

Scripts and generated audio stay in the visitor's browser. Model/runtime assets are fetched from Hugging Face and the runtime's public CDN. Download recordings to keep them; generated recordings are not uploaded to account storage.

The app uses Kokoro.js and the Apache-2.0 Kokoro model. [Kokoro](https://github.com/hexgrad/kokoro), [model](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX).

Developed by [KAMI Pierre](https://kamipierre.vercel.app/) · Full-stack System Developer.
