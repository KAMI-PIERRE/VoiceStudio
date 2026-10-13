import { CHARACTERS, DEFAULT_CHARACTER } from "./characters.js";

const MAX_CHARACTERS = 20_000;
const PREVIEW_SCRIPT = "Hello. This is a preview of my voice. Let me help bring your next story to life.";
const SAMPLES = {
  story: "The little bookshop was the last place Maya expected to find an adventure. But on a rainy Tuesday, a letter slipped from the pages of an old atlas. It contained just six words: The island is waiting for you. She smiled, folded the letter carefully, and began to pack.",
  presentation: "Good morning, everyone. Today, we are introducing a simpler way to turn ideas into action. Our goal is clear: help people spend less time on routine tasks and more time on the work that matters. Let's start with the opportunity, then walk through our plan together.",
  advertisement: "Make room for a brighter morning. With freshly roasted coffee and a moment to yourself, an ordinary day becomes something special. Discover your new favorite blend today. One small ritual. A whole new start.",
};

const element = (id) => document.getElementById(id);
const ui = {
  workspace: element("workspace"),
  choices: element("character-choices"),
  script: element("script"),
  speed: element("speed"),
  pause: element("pause"),
  generate: element("generate"),
  preview: element("preview"),
  status: element("recording-status"),
  audio: element("recording-audio"),
  placeholder: element("recording-placeholder"),
  progress: element("progress"),
  progressArea: element("generation-progress"),
  download: element("download"),
};

let selectedId = CHARACTERS[DEFAULT_CHARACTER] ? DEFAULT_CHARACTER : Object.keys(CHARACTERS)[0];
let worker = null;
let busy = false;
let activeRequest = null;
let sequence = 0;
let recordingUrl = null;

function avatarUrl(character, id) {
  const filename = /^[a-z]+\.svg$/.test(character.avatar || "") ? character.avatar : `${id}.svg`;
  return new URL(`assets/avatars/${filename}`, document.baseURI).href;
}

function voiceLabel(character) {
  return character.voice_label || character.voiceLabel || "English";
}

function updateCharacter() {
  const character = CHARACTERS[selectedId];
  for (const input of ui.choices.querySelectorAll("input")) {
    input.checked = input.value === selectedId;
    input.closest("label").classList.toggle("is-selected", input.checked);
  }
  const avatar = element("selected-avatar");
  avatar.src = avatarUrl(character, selectedId);
  avatar.alt = `${character.name} character avatar`;
  element("selected-name").textContent = character.name;
  element("selected-role").textContent = character.role ? `· ${character.role}` : "";
  element("selected-description").textContent = character.description || "A distinct character voice for your next story.";
  element("selected-accent").textContent = voiceLabel(character);
  updateButtons();
}

function renderCharacters() {
  const count = Object.keys(CHARACTERS).length;
  element("voice-count").textContent = String(count).padStart(2, "0");
  element("character-count").textContent = `${count} voices`;
  for (const [id, character] of Object.entries(CHARACTERS)) {
    const label = document.createElement("label");
    label.className = "voice-card";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "character";
    input.value = id;
    const image = document.createElement("img");
    image.src = avatarUrl(character, id);
    image.alt = "";
    image.width = 36;
    image.height = 36;
    const copy = document.createElement("span");
    copy.className = "voice-card-copy";
    const name = document.createElement("span");
    name.className = "voice-card-name";
    name.textContent = character.name;
    const accent = document.createElement("span");
    accent.className = "voice-card-accent";
    accent.textContent = voiceLabel(character);
    copy.append(name, accent);
    label.append(input, image, copy);
    input.addEventListener("change", () => {
      if (input.checked) {
        selectedId = id;
        updateCharacter();
      }
    });
    ui.choices.append(label);
  }
  updateCharacter();
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function updateStatistics() {
  const text = ui.script.value;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const boundaries = Math.max(0, (text.match(/[.!?]+(?:\s|$)/g) || []).length - 1);
  const seconds = Math.ceil(words * 60 / (165 * Number(ui.speed.value)) + boundaries * Number(ui.pause.value) / 1000);
  element("character-total").textContent = text.length.toLocaleString();
  element("word-total").textContent = words.toLocaleString();
  element("duration-estimate").textContent = formatDuration(seconds);
  element("script-meter-fill").style.width = `${Math.min(100, text.length / MAX_CHARACTERS * 100)}%`;
  element("speed-value").textContent = `${Number(ui.speed.value).toFixed(2)}×`;
  element("pause-value").textContent = `${Number(ui.pause.value)} ms`;
}

function setStatus(message, state = "") {
  ui.status.textContent = message;
  ui.status.dataset.state = state;
}

function updateButtons() {
  ui.generate.disabled = busy;
  ui.preview.disabled = busy;
  ui.generate.textContent = busy && !activeRequest?.preview ? "Creating speech…" : `Generate speech · ${CHARACTERS[selectedId].name}`;
  ui.preview.textContent = busy && activeRequest?.preview ? "Creating preview…" : "Preview this voice";
  ui.workspace.setAttribute("aria-busy", String(busy));
  ui.progressArea.hidden = !busy;
}

function resetWorker() {
  if (worker) worker.terminate();
  worker = null;
}

function finishError(message) {
  resetWorker();
  activeRequest = null;
  busy = false;
  updateButtons();
  setStatus(message || "We couldn’t create this recording. Check your connection and try again.", "error");
}

function receiveMessage(event) {
  const data = event.data;
  if (!activeRequest || !data || data.id !== activeRequest.id) return;
  if (data.type === "progress") {
    const value = Number(data.progress);
    ui.progress.value = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0;
    if (typeof data.message === "string" && data.message.trim()) setStatus(data.message);
    return;
  }
  if (data.type === "error") {
    finishError(typeof data.message === "string" ? data.message : "We couldn’t create this recording. Please try again.");
    return;
  }
  if (data.type !== "complete") return;
  if (!(data.blob instanceof Blob) || !data.blob.size || !Number.isFinite(data.frames) || data.frames <= 0 || !Number.isFinite(data.sampleRate) || data.sampleRate <= 0) {
    finishError("This recording wasn’t ready to play. Please try again.");
    return;
  }

  const completed = activeRequest;
  const nextUrl = URL.createObjectURL(data.blob);
  const previousUrl = recordingUrl;
  recordingUrl = nextUrl;
  ui.audio.src = nextUrl;
  ui.audio.hidden = false;
  ui.placeholder.hidden = true;
  ui.download.href = nextUrl;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  ui.download.download = `voice-studio-${completed.characterId}${completed.preview ? "-preview" : ""}-${stamp}.wav`;
  ui.download.hidden = false;
  element("download-size").textContent = data.blob.size < 1_000_000 ? `${Math.ceil(data.blob.size / 1000)} KB` : `${(data.blob.size / 1_000_000).toFixed(1)} MB`;
  if (previousUrl) URL.revokeObjectURL(previousUrl);
  const elapsed = Number(data.elapsedSeconds);
  const timing = Number.isFinite(elapsed) && elapsed >= 0 ? ` · created in ${elapsed.toFixed(1)}s` : "";
  const label = completed.preview ? "Voice preview" : "Ready to listen";
  setStatus(`${label} · ${completed.characterName} · ${formatDuration(data.frames / data.sampleRate)} audio${timing}`, "success");
  activeRequest = null;
  busy = false;
  updateButtons();
}

function getWorker() {
  if (!worker) {
    worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
    worker.addEventListener("message", receiveMessage);
    worker.addEventListener("error", () => finishError("Voice generation stopped. Check your connection and try again."));
    worker.addEventListener("messageerror", () => finishError("We couldn’t receive this recording. Please try again."));
  }
  return worker;
}

function startRecording(preview = false) {
  if (busy) return;
  const text = preview ? PREVIEW_SCRIPT : ui.script.value.trim();
  if (!text || !/[\p{L}\p{N}]/u.test(text)) {
    setStatus("Add some English words to your script first.", "error");
    ui.script.focus();
    return;
  }
  if (text.length > MAX_CHARACTERS) {
    setStatus("Keep your script within 20,000 characters.", "error");
    ui.script.focus();
    return;
  }
  const speed = Number(ui.speed.value);
  const pauseMs = Number(ui.pause.value);
  if (!Number.isFinite(speed) || speed < 0.75 || speed > 1.5 || !Number.isFinite(pauseMs) || pauseMs < 0 || pauseMs > 1000) {
    setStatus("Choose a valid speaking speed and pause length.", "error");
    return;
  }
  activeRequest = {
    id: `${Date.now()}-${++sequence}`,
    characterId: selectedId,
    characterName: CHARACTERS[selectedId].name,
    preview,
  };
  busy = true;
  ui.progress.value = 0;
  setStatus("Preparing your voice. First use downloads the voice library; keep this tab open.");
  updateButtons();
  element("recording-panel").scrollIntoView({ block: "nearest", behavior: "auto" });
  try {
    getWorker().postMessage({ id: activeRequest.id, text, characterId: selectedId, speed, pauseMs });
  } catch {
    finishError("We couldn’t start this recording. Check your connection and try again.");
  }
}

for (const control of [ui.script, ui.speed, ui.pause]) control.addEventListener("input", updateStatistics);
for (const button of document.querySelectorAll("[data-sample]")) {
  button.addEventListener("click", () => {
    ui.script.value = SAMPLES[button.dataset.sample];
    updateStatistics();
  });
}
element("clear-script").addEventListener("click", () => {
  ui.script.value = "";
  updateStatistics();
  ui.script.focus();
});
ui.generate.addEventListener("click", () => startRecording(false));
ui.preview.addEventListener("click", () => startRecording(true));
element("cancel").addEventListener("click", () => {
  if (!busy) return;
  resetWorker();
  activeRequest = null;
  busy = false;
  updateButtons();
  setStatus("Recording canceled. Your script is still here.");
});
ui.script.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    startRecording(false);
  }
});

renderCharacters();
updateStatistics();
