import { defineConfig } from 'vite';

const headers = {
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'cross-origin',
};

export default defineConfig({
  base: './',
  server: { headers },
  preview: { headers },
  worker: { format: 'es' },
});
