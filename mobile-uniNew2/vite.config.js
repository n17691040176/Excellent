import {
	defineConfig,
	loadEnv
} from 'vite'
import {
	resolve
} from 'node:path'
import {
	fileURLToPath
} from 'node:url'
import uniPlugin from '@dcloudio/vite-plugin-uni'

process.env.CI = process.env.CI || '1'

const uni = uniPlugin.default || uniPlugin
const projectRoot = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig(({
	mode
}) => {
	const env = loadEnv(mode || 'development', projectRoot, '')
	const appEnv = env.VITE_APP_ENV || 'dev'
	const apiBaseUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
	const inviteWebBaseUrl = env.VITE_INVITE_WEB_BASE_URL || 'http://127.0.0.1:5174'

	return {
		plugins: [uni()],
		base: './',
		define: {
			'globalThis.__APP_ENV__': JSON.stringify(appEnv),
			'globalThis.__API_BASE_URL__': JSON.stringify(apiBaseUrl),
			'globalThis.__INVITE_WEB_BASE_URL__': JSON.stringify(inviteWebBaseUrl)
		},
		server: {
			host: '0.0.0.0',
			port: 5174,
			proxy: {
				'/api/v1': {
					target: apiBaseUrl,
					changeOrigin: true
				},
				'/uploads': {
					target: apiBaseUrl,
					changeOrigin: true
				}
			}
		},
		resolve: {
			alias: {
				'@': resolve(projectRoot, '.')
			}
		}
	}
})
