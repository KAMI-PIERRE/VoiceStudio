export const SAMPLE_RATE = 24000;
export const MAX_TEXT_LENGTH = 20000;
export const MAX_CHUNK_CHARACTERS = 160;
export const MAX_MODEL_TOKENS = 512;

export function validateSpeechRequest(request, characters) {
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw new Error("Send a speech request with text, voice, speed, and pause.");
  }
  const { id, text, characterId, speed, pauseMs } = request;
  if (!((typeof id === "string" && id.length > 0 && id.length <= 128)
    || (typeof id === "number" && Number.isFinite(id)))) {
    throw new Error("The speech request needs a valid identifier.");
  }
  if (typeof text !== "string" || text.length > MAX_TEXT_LENGTH) {
    throw new Error("Enter English text with no more than 20,000 characters.");
  }
  if (!text.trim()) throw new Error("Enter some English text first.");
  if (typeof characterId !== "string" || !Object.hasOwn(characters, characterId)) {
    throw new Error("Choose one of the available voices.");
  }
  const character = characters[characterId];
  if (!character || typeof character.voiceId !== "string" || !character.voiceId) {
    throw new Error("This voice is unavailable. Choose another voice.");
  }
  if (typeof speed !== "number" || !Number.isFinite(speed) || speed < 0.75 || speed > 1.5) {
    throw new Error("Set speaking speed between 0.75x and 1.5x.");
  }
  if (typeof pauseMs !== "number" || !Number.isFinite(pauseMs) || pauseMs < 0 || pauseMs > 1000) {
    throw new Error("Set the pause between 0 and 1,000 milliseconds.");
  }
  return { id, text: text.trim(), characterId, voiceId: character.voiceId, speed, pauseMs };
}

// Keep every non-whitespace character, including long words and Unicode pairs.
// Sentence boundaries are preferred, then word boundaries, then a hard split.
export function splitText(text, limit = MAX_CHUNK_CHARACTERS) {
  if (typeof text !== "string") throw new TypeError("Text must be a string.");
  if (!Number.isInteger(limit) || limit < 2) throw new RangeError("Chunk size must be at least two.");
  const normalized = text.replace(/\s+/gu, " ").trim();
  const chunks = [];
  let offset = 0;
  while (offset < normalized.length) {
    let end = Math.min(offset + limit, normalized.length);
    if (end < normalized.length) {
      const lastUnit = normalized.charCodeAt(end - 1);
      const nextUnit = normalized.charCodeAt(end);
      if (lastUnit >= 0xd800 && lastUnit <= 0xdbff && nextUnit >= 0xdc00 && nextUnit <= 0xdfff) end -= 1;
      const window = normalized.slice(offset, end);
      let sentenceEnd = 0;
      for (const match of window.matchAll(/[.!?](?:["')\]]*)\s+/gu)) {
        if (match.index + match[0].length >= limit / 3) sentenceEnd = match.index + match[0].length;
      }
      const wordEnd = window.lastIndexOf(" ");
      if (sentenceEnd) end = offset + sentenceEnd;
      else if (wordEnd > 0) end = offset + wordEnd + 1;
    }
    const chunk = normalized.slice(offset, end).trim();
    if (chunk) chunks.push(chunk);
    offset = end;
  }
  return chunks;
}

export function splitOversizedChunk(text) {
  const characters = Array.from(text);
  if (characters.length < 2) {
    throw new Error("A character expands beyond the voice model's limit. Reword this part of the script.");
  }
  const middle = Math.floor(characters.length / 2);
  let boundary = middle;
  for (let distance = 0; distance < middle; distance += 1) {
    const left = middle - distance;
    const right = middle + distance;
    if (left > 0 && /\s/u.test(characters[left])) { boundary = left; break; }
    if (right < characters.length - 1 && /\s/u.test(characters[right])) { boundary = right; break; }
  }
  const halves = [
    characters.slice(0, boundary).join("").trim(),
    characters.slice(boundary).join("").trim(),
  ];
  if (halves.some((half) => !half)) throw new Error("This part of the script cannot be split safely.");
  return halves;
}

export class TokenizerLimitError extends Error {
  constructor(tokenCount) {
    super("This speech chunk needs to be split before generation.");
    this.name = "TokenizerLimitError";
    this.tokenCount = tokenCount;
  }
}

// Kokoro JS generate() normally requests truncation. Disable it and inspect the
// actual expanded phoneme tokens before any inference, including number expansion.
export function guardTokenizer(tokenizer, maxTokens = MAX_MODEL_TOKENS) {
  if (typeof tokenizer !== "function") throw new TypeError("The model tokenizer is unavailable.");
  return (phonemes, options = {}) => {
    const encoded = tokenizer(phonemes, { ...options, truncation: false });
    const tokenCount = encoded?.input_ids?.dims?.at(-1);
    if (!Number.isInteger(tokenCount) || tokenCount < 2) {
      throw new Error("The model returned invalid speech tokens.");
    }
    if (tokenCount > maxTokens) throw new TokenizerLimitError(tokenCount);
    return encoded;
  };
}

export function encodePcm16(samples) {
  if (!(samples instanceof Float32Array || samples instanceof Float64Array) || !samples.length) {
    throw new Error("The voice model returned no audio.");
  }
  const bytes = new Uint8Array(samples.length * 2);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index];
    if (!Number.isFinite(value)) throw new Error("The voice model returned invalid audio samples.");
    const clipped = Math.max(-1, Math.min(1, value));
    view.setInt16(index * 2, Math.round(clipped * (clipped < 0 ? 32768 : 32767)), true);
  }
  return bytes;
}

export function createWavHeader(frames, sampleRate = SAMPLE_RATE) {
  if (!Number.isSafeInteger(frames) || frames < 0 || frames * 2 > 0xffffffff - 36) {
    throw new RangeError("The generated audio exceeds the WAV size limit.");
  }
  if (!Number.isInteger(sampleRate) || sampleRate <= 0 || sampleRate > 0x7fffffff) {
    throw new RangeError("Invalid audio sampling rate.");
  }
  const bytes = new Uint8Array(44);
  const view = new DataView(bytes.buffer);
  const label = (offset, value) => [...value].forEach((char, index) => { bytes[offset + index] = char.charCodeAt(0); });
  label(0, "RIFF");
  view.setUint32(4, frames * 2 + 36, true);
  label(8, "WAVE");
  label(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  label(36, "data");
  view.setUint32(40, frames * 2, true);
  return bytes;
}

export class PcmWavBuilder {
  constructor() {
    this.parts = [];
    this.frames = 0;
  }
  appendAudio(samples) {
    const bytes = encodePcm16(samples);
    createWavHeader(this.frames + samples.length);
    this.parts.push(bytes);
    this.frames += samples.length;
  }
  appendSilence(milliseconds) {
    if (!Number.isFinite(milliseconds) || milliseconds < 0 || milliseconds > 1000) {
      throw new RangeError("Invalid pause duration.");
    }
    const frames = Math.round(SAMPLE_RATE * milliseconds / 1000);
    if (!frames) return;
    createWavHeader(this.frames + frames);
    this.parts.push(new Uint8Array(frames * 2));
    this.frames += frames;
  }
  toBlob() {
    if (!this.frames) throw new Error("No audio was generated.");
    return new Blob([createWavHeader(this.frames), ...this.parts], { type: "audio/wav" });
  }
}

