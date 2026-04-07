import { defineConfig } from 'vite'
import uniPlugin from '@dcloudio/vite-plugin-uni'

process.env.CI = process.env.CI || '1'

const uni = uniPlugin.default || uniPlugin

export default defineConfig({
  plugins: [uni()],
  server: {
    host: '127.0.0.1',
    port: 5173
  }
})
