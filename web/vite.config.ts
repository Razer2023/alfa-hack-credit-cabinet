import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// API ядра всегда по относительному адресу /api/v1: в разработке его проксирует Vite,
// в Docker — nginx (см. nginx.conf). Адрес ядра для разработки можно поменять через CORE_URL.
const coreUrl = process.env.CORE_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: coreUrl, changeOrigin: true },
    },
  },
});
