"""Exercise only the deploy health gate in the local container; never deploy."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / 'deploy.sh').read_text(encoding='utf-8')
start = source.index('check_health() {')
end = source.index('\necho ""', start)
gate = source[start:end]
command = ['docker', 'compose', '-f', 'tools/compose.local-test.yml', '-f', 'tools/compose.local-app.yml',
           'exec', '-T', 'server', 'bash', '-s']
syntax = subprocess.run(command[:-1] + ['-n'], input=source.encode('utf-8'), capture_output=True, cwd=root, timeout=30)
assert syntax.returncode == 0, syntax.stderr
results = []
for failed_port in [None, '8000', '8081', '8082']:
    curl = 'curl() { return 0; }' if failed_port is None else f'curl() {{ case "$*" in *localhost:{failed_port}/*) return 22;; *) return 0;; esac; }}'
    script = 'set -e\n' + curl + '\nsleep() { :; }\n' + gate + '\necho DEPLOY_SUCCEEDED\n'
    result = subprocess.run(command, input=script.encode('utf-8'), capture_output=True, cwd=root, timeout=30)
    assert result.returncode == (0 if failed_port is None else 1), result.stderr
    assert (b'DEPLOY_SUCCEEDED' in result.stdout) == (failed_port is None), result.stdout
    results.append({'failed_port': failed_port, 'exit_code': result.returncode, 'passed': True})
(root / 'logs/local-test/deploy-health-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results))
