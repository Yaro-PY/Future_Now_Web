import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';

const output = fileURLToPath(new URL('../static/react/', import.meta.url));
const expected = fileURLToPath(new URL('../', import.meta.url));
if (!output.startsWith(expected) || !output.endsWith('static\\react\\') && !output.endsWith('static/react/')) {
  throw new Error('React output must stay in this website’s static/react directory');
}

export default defineConfig(({command}) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : '/assets/react/',
  publicDir: false,
  build: {outDir: output, emptyOutDir: true, assetsDir: 'bundles'},
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8002',
      '/assets/images': 'http://127.0.0.1:8002',
      '/assets/favicon.svg': 'http://127.0.0.1:8002',
      '/favicon.ico': 'http://127.0.0.1:8002',
    },
  },
}));
