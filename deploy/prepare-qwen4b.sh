#!/usr/bin/env bash
set -euo pipefail
umask 027
root=${RLT_DEPLOY_ROOT:-/opt/rlt-hack}
revision=${1:?Pass the Qwen3-Embedding-4B Hugging Face revision}
[[ $revision =~ ^[0-9a-f]{40}$ ]] || exit 2
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
mkdir -p "$root/qwen4b/models" "$root/qwen4b/reports"
python3 -m venv "$root/qwen4b/venv"
"$root/qwen4b/venv/bin/pip" install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
"$root/qwen4b/venv/bin/pip" install -r "$root/current/ml/serving/qwen4b/requirements.txt"
"$root/qwen4b/venv/bin/python" - "$root/qwen4b" "$revision" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
root, revision = Path(sys.argv[1]), sys.argv[2]
snapshot_download('Qwen/Qwen3-Embedding-4B', revision=revision, local_dir=root / 'models',
                  allow_patterns=['*.json', '*.safetensors', 'tokenizer*', 'vocab*', 'merges*'])
checksums = {}
for path in sorted((root / 'models').glob('*.safetensors')):
    with path.open('rb') as stream:
        checksums[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
(root / 'model-manifest.json').write_text(json.dumps({
    'model': 'Qwen/Qwen3-Embedding-4B', 'revision': revision, 'files': checksums,
}, indent=2))
PY
chown -R rlt-deploy:rlt-deploy "$root/qwen4b"
printf '%s\n' 'Qwen4B cache is ready; configure qwen4b.env and verify compatibility before switching.'
