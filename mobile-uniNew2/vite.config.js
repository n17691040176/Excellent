import { defineConfig, loadEnv } from 'vite'
import uniPlugin from '@dcloudio/vite-plugin-uni'

process.env.CI = process.env.CI || '1'

const uni = uniPlugin.default || uniPlugin

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  console.log('mode=', mode)
  console.log('VITE_API_BASE_URL=', env.VITE_API_BASE_URL)
  console.log('VITE_APP_ENV=', env.VITE_APP_ENV)
  return {
    plugins: [uni()],
    base: './',
    server: {
      host: '0.0.0.0',
      port: 5174,
      proxy: {
        '/api/v1': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
          changeOrigin: true
        },
        '/uploads': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
          changeOrigin: true
        }
      }
    }
  }
  
})
