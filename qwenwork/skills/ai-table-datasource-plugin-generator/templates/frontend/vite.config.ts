import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // 使用相对路径，确保资源引用在任意子路径部署下都正确
  base: './',
  server: {
    port: 3000,
    proxy: {
      // 开发时将 /api 请求代理到后端，绕过浏览器 CORS 限制
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  plugins: [react()],
  build: {
    outDir: 'build',
  },
  define: {
    'process.env': {},
  },
  resolve: {
    alias: {
      '@oclif/core': '/dev/null',
    },
  },
});
