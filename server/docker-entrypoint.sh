#!/bin/sh
set -eu

upload_dir="${UPLOAD_DIR:-/app/uploads}"
mkdir -p "$upload_dir"
if ! chown -R appuser:appgroup "$upload_dir"; then
    # Docker Desktop bind mounts backed by NTFS may reject chown even though
    # the mounted directory is writable. Verify the effective appuser access
    # below instead of failing startup solely on the ownership operation.
    echo "warning: could not chown $upload_dir; checking appuser write access" >&2
fi

# Use an explicit argv[0] placeholder. `su` implementations commonly consume
# `--` while parsing options, which would leave the shell's `$1` empty.
if ! su -s /bin/sh -c 'test -w "$1"' appuser _ "$upload_dir"; then
    echo "error: $upload_dir is not writable by appuser" >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    set -- uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

# Keep the container's long-running process non-root while allowing the
# startup step above to repair an existing named/bind-mounted volume.
exec su -s /bin/sh -c 'exec "$@"' appuser _ "$@"
