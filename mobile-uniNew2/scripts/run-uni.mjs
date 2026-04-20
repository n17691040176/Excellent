import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const rootDir = path.resolve(__dirname, '..')
const uniBin = process.platform === 'win32'
  ? path.join(rootDir, 'node_modules', '.bin', 'uni.cmd')
  : path.join(rootDir, 'node_modules', '.bin', 'uni')

const result = spawnSync(uniBin, process.argv.slice(2), {
  cwd: rootDir,
  shell: process.platform === 'win32',
  stdio: 'inherit',
  env: {
    ...process.env,
    UNI_INPUT_DIR: rootDir
  }
})

if (result.error) {
  console.error(result.error)
  process.exit(1)
}

process.exit(result.status ?? 1)
