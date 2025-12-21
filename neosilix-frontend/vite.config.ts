import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { visualizer } from 'rollup-plugin-visualizer';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [
    react(),
    // Optional: Visualize bundle size
    visualizer({
      filename: 'dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }) as any,
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor libraries
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['recharts'],
          'ui-vendor': ['lucide-react', 'clsx', 'sonner'],
          'utils-vendor': ['date-fns', 'axios', 'lodash-es'],
        },
      },
    },
    // Optimize build output
    chunkSizeWarningLimit: 800, // Increased from default 500
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false, // Keep console for development
        drop_debugger: true,
      },
    },
    // Enable source maps in development only
    sourcemap: process.env.NODE_ENV !== 'production',
    // Optimize assets
    assetsInlineLimit: 4096, // 4kb
    cssCodeSplit: true,
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'recharts',
      'clsx',
      'sonner',
    ],
    exclude: ['lucide-react'], // Let Vite handle tree-shaking for icons
  },
  // CSS optimization
  css: {
    devSourcemap: true,
    modules: {
      localsConvention: 'camelCase',
    },
  },
});
