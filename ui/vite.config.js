import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.js', 'src/**/*.jsx'],
      exclude: [
        'src/setupTests.js',
        'src/**/*.test.js',
        'src/**/*.test.jsx',
        'src/main.jsx',
      ],
      thresholds: {
        lines: 15,
        functions: 12,
        statements: 14,
        branches: 10,
        'src/services/**': {
          lines: 75,
          functions: 75,
          statements: 75,
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    watch: {
      ignored: ['**/src-tauri/**'],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8765',
        ws: true,
      },
    },
  },
});
