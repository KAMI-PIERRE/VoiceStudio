import assert from 'node:assert/strict';
import test from 'node:test';

import {
  encodePcm16,
  createWavHeader,
  PcmWavBuilder,
  splitText,
  splitOversizedChunk,
  validateSpeechRequest,
} from '../browser/src/speech.js';

const characters = {
  heart: { voiceId: 'af_heart' },
  michael: { voiceId: 'am_michael' },
};

const validRequest = {
  id: 'recording-1',
  text: 'Welcome to Voice Studio.',
  characterId: 'heart',
  speed: 1,
  pauseMs: 220,
};

function int16Samples(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return Array.from({ length: bytes.byteLength / 2 }, (_, index) => view.getInt16(index * 2, true));
}

test('long scripts retain every word and their original order', () => {
  const words = Array.from({ length: 999 }, (_, index) => `w${String(index).padStart(4, '0')}`);
  words.push('ending');
  const script = words.join(' ');
  assert.equal(script.length, 6000);
  const chunks = splitText(script);
  assert.ok(chunks.length > 1);
  assert.ok(chunks.every((chunk) => chunk.length > 0 && chunk.length <= 160));
  assert.deepEqual(chunks.join(' ').split(/\s+/u), words);

  const paragraphs = 'First paragraph.\n\nSecond line!\tAnother sentence? Final words.';
  assert.deepEqual(splitText(paragraphs).join(' ').split(/\s+/u), paragraphs.split(/\s+/u));
});

test('oversized Unicode tokens retain every code point through initial and retry splitting', () => {
  const token = '😀𠮷é'.repeat(100);
  const script = `Before ${token} after.`;
  const chunks = splitText(script);
  assert.ok(chunks.every((chunk) => chunk.length <= 160));
  assert.equal(chunks.join('').replace(/\s/gu, ''), script.replace(/\s/gu, ''));
  for (const chunk of chunks) assert.equal(chunk, chunk.toWellFormed());

  const retryChunks = splitOversizedChunk(token);
  assert.equal(retryChunks.join(''), token);
  assert.ok(retryChunks.length > 1);
  for (const chunk of retryChunks) assert.equal(chunk, chunk.toWellFormed());
});

test('request validation rejects invalid text, unknown speakers and nonfinite settings', () => {
  const invalidChanges = [
    { text: undefined },
    { text: 123 },
    { text: ' \n\t' },
    { text: 'a'.repeat(20_001) },
    { characterId: 'unknown' },
    { characterId: 'af_heart' },
    { characterId: 'toString' },
    { characterId: '__proto__' },
    { characterId: null },
    { speed: 0.749 },
    { speed: 1.501 },
    { speed: NaN },
    { speed: Infinity },
    { speed: -Infinity },
    { pauseMs: -0.001 },
    { pauseMs: 1000.001 },
    { pauseMs: NaN },
    { pauseMs: Infinity },
    { pauseMs: -Infinity },
  ];
  for (const changes of invalidChanges) {
    assert.throws(() => validateSpeechRequest({ ...validRequest, ...changes }, characters));
  }
});

test('valid boundary controls and a full 20000-character script select the requested real voice', () => {
  for (const speed of [0.75, 1.5]) {
    for (const pauseMs of [0, 1000]) {
      const result = validateSpeechRequest({
        ...validRequest,
        text: 'a'.repeat(20_000),
        characterId: 'michael',
        speed,
        pauseMs,
      }, characters);
      assert.equal(result.text.length, 20_000);
      assert.equal(result.voiceId, 'am_michael');
      assert.equal(result.speed, speed);
      assert.equal(result.pauseMs, pauseMs);
    }
  }
  assert.equal(validateSpeechRequest({ ...validRequest, text: '  Hello.  ' }, characters).text, 'Hello.');
});

test('PCM encoding clamps peaks and encodes signed little-endian 16-bit samples', () => {
  const bytes = encodePcm16(new Float32Array([-2, -1, -0.5, 0, 0.5, 1, 2]));
  assert.equal(bytes.byteLength, 14);
  const samples = int16Samples(bytes);
  assert.deepEqual(samples.slice(0, 2), [-32768, -32768]);
  assert.equal(samples[2], -16384);
  assert.equal(samples[3], 0);
  assert.ok(Math.abs(samples[4] - 16384) <= 1);
  assert.deepEqual(samples.slice(5), [32767, 32767]);
  for (const invalid of [new Float32Array(), new Float32Array([NaN]), new Float32Array([Infinity])]) {
    assert.throws(() => encodePcm16(invalid));
  }
});

test('WAV header describes mono 24000 Hz PCM16 with exact payload length', () => {
  const header = createWavHeader(48);
  assert.equal(header.byteLength, 44);
  const bytes = Buffer.from(header);
  assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
  assert.equal(bytes.readUInt32LE(4), 36 + 48 * 2);
  assert.equal(bytes.toString('ascii', 8, 12), 'WAVE');
  assert.equal(bytes.toString('ascii', 12, 16), 'fmt ');
  assert.equal(bytes.readUInt32LE(16), 16);
  assert.equal(bytes.readUInt16LE(20), 1);
  assert.equal(bytes.readUInt16LE(22), 1);
  assert.equal(bytes.readUInt32LE(24), 24_000);
  assert.equal(bytes.readUInt32LE(28), 48_000);
  assert.equal(bytes.readUInt16LE(32), 2);
  assert.equal(bytes.readUInt16LE(34), 16);
  assert.equal(bytes.toString('ascii', 36, 40), 'data');
  assert.equal(bytes.readUInt32LE(40), 96);
});

test('WAV assembly inserts exactly the requested pause between clips without endpoint padding', async () => {
  const wav = new PcmWavBuilder();
  wav.appendAudio(new Float32Array(24).fill(1));
  wav.appendSilence(125);
  wav.appendAudio(new Float32Array(24).fill(-1));
  const blob = wav.toBlob();
  assert.equal(blob.type, 'audio/wav');
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const frames = 24 + 3000 + 24;
  assert.equal(wav.frames, frames);
  assert.equal(bytes.byteLength, 44 + frames * 2);
  assert.equal(new DataView(bytes.buffer).getUint32(40, true), frames * 2);
  const samples = int16Samples(bytes.subarray(44));
  assert.deepEqual(samples.slice(0, 24), Array(24).fill(32767));
  assert.deepEqual(samples.slice(24, 3024), Array(3000).fill(0));
  assert.deepEqual(samples.slice(3024), Array(24).fill(-32768));
});

test('a zero pause joins audio immediately and adds no trailing silence', async () => {
  const wav = new PcmWavBuilder();
  wav.appendAudio(new Float32Array([1, -1]));
  wav.appendSilence(0);
  wav.appendAudio(new Float32Array([1, -1]));
  const bytes = new Uint8Array(await wav.toBlob().arrayBuffer());
  assert.equal(bytes.byteLength, 52);
  assert.equal(wav.frames, 4);
  assert.deepEqual(int16Samples(bytes.subarray(44)), [32767, -32768, 32767, -32768]);
});
