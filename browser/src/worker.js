import { KokoroTTS } from "kokoro-js";
import { CHARACTERS } from "./characters.js";
import {
  SAMPLE_RATE,
  validateSpeechRequest,
  splitText,
  splitOversizedChunk,
  TokenizerLimitError,
  guardTokenizer,
  PcmWavBuilder,
} from "./speech.js";

const MODEL_ID = "onnx-community/Kokoro-82M-v1.0-ONNX";
let modelPromise = null;
let busy = false;
let activeRequestId = null;
let activeProgress = 0;

function progress(value, message) {
  activeProgress = Math.max(activeProgress, Math.min(1, Math.max(0, value)));
  self.postMessage({ id: activeRequestId, type: "progress", progress: activeProgress, message });
}

async function loadModel() {
  if (!modelPromise) {
    const files = new Map();
    progress(0.01, "Preparing the voice model. The first download is about 100 MB.");
    modelPromise = KokoroTTS.from_pretrained(MODEL_ID, {
      dtype: "q8",
      device: "wasm",
      progress_callback: (event) => {
        if (typeof event?.file === "string") {
          const previous = files.get(event.file) || { loaded: 0, total: 0 };
          const total = Number.isFinite(event.total) ? event.total : previous.total;
          let loaded = Number.isFinite(event.loaded) ? event.loaded : previous.loaded;
          if (event.status === "done" && total > 0) loaded = total;
          files.set(event.file, { loaded, total });
          let loadedBytes = 0;
          let totalBytes = 0;
          for (const file of files.values()) {
            loadedBytes += file.loaded;
            totalBytes += file.total;
          }
          const ratio = Math.min(1, loadedBytes / Math.max(totalBytes, 92_400_000));
          const percent = Math.floor(ratio * 100);
          progress(0.01 + 0.30 * ratio, `Downloading voice model: ${percent}%.`);
        } else if (event?.status === "ready") {
          progress(0.32, "Voice model downloaded. Preparing local speech generation.");
        }
      },
    }).then((model) => {
      model.tokenizer = guardTokenizer(model.tokenizer);
      return model;
    }).catch((error) => {
      modelPromise = null;
      throw error;
    });
  }
  const model = await modelPromise;
  progress(0.35, "Voice model ready. Preparing your selected voice.");
  return model;
}

self.addEventListener("message", async ({ data }) => {
  const id = data && typeof data === "object" ? data.id : null;
  if (busy) {
    self.postMessage({ id, type: "error", message: "Speech is already generating. Wait for it to finish, then try again." });
    return;
  }
  let request;
  try {
    request = validateSpeechRequest(data, CHARACTERS);
  } catch (error) {
    self.postMessage({ id, type: "error", message: error.message || "Check your speech settings." });
    return;
  }
  busy = true;
  activeRequestId = request.id;
  activeProgress = 0;
  const started = performance.now();
  try {
    const model = await loadModel();
    if (!Object.hasOwn(model.voices, request.voiceId)) {
      throw new Error("Your selected voice is unavailable in this model.");
    }
    const pending = splitText(request.text);
    const totalCharacters = pending.reduce((sum, chunk) => sum + chunk.length, 0);
    const wav = new PcmWavBuilder();
    let completedCharacters = 0;
    let completedChunks = 0;
    while (pending.length) {
      const text = pending.shift();
      let audio;
      try {
        audio = await model.generate(text, { voice: request.voiceId, speed: request.speed });
      } catch (error) {
        if (error instanceof TokenizerLimitError) {
          pending.unshift(...splitOversizedChunk(text));
          continue;
        }
        throw error;
      }
      if (audio.sampling_rate !== SAMPLE_RATE) {
        throw new Error("The voice model returned an unexpected audio sampling rate.");
      }
      // Append pauses before successful chunks, so the finished WAV has no trailing pause.
      if (completedChunks) wav.appendSilence(request.pauseMs);
      wav.appendAudio(audio.audio);
      completedCharacters += text.length;
      completedChunks += 1;
      const ratio = Math.min(1, completedCharacters / totalCharacters);
      progress(0.35 + 0.64 * ratio, `Generating speech: ${Math.round(ratio * 100)}%.`);
    }
    const blob = wav.toBlob();
    progress(1, "Your speech is ready.");
    self.postMessage({
      id: request.id,
      type: "complete",
      blob,
      frames: wav.frames,
      sampleRate: SAMPLE_RATE,
      elapsedSeconds: (performance.now() - started) / 1000,
    });
  } catch (error) {
    self.postMessage({
      id: request.id,
      type: "error",
      message: error.message || "Speech generation failed. Try again.",
    });
  } finally {
    busy = false;
    activeRequestId = null;
    activeProgress = 0;
  }
});

