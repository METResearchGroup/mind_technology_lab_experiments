#!/bin/bash
# Shared GPU entry for Hugging Face Jobs fallbacks. The workload is scripts/hf_job.py.
set -euxo pipefail
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# huggingface_hub errors if this is 1 and hf_transfer is not installed yet.
unset HF_HUB_ENABLE_HF_TRANSFER || true

python3 -c "import torch; print({'torch': torch.__version__, 'cuda': torch.cuda.is_available(), 'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})"

python3 -m pip install -q --upgrade pip
# transformers>=5 needs torch>=2.5; the RunPod 2.4 image must be upgraded in place.
python3 -m pip install -q --index-url https://download.pytorch.org/whl/cu124 \
  torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0
python3 -m pip install -q \
  'transformers>=5.0.0' \
  peft \
  accelerate \
  pillow \
  huggingface_hub \
  boto3 \
  numpy \
  safetensors \
  hf_transfer

export HF_HUB_ENABLE_HF_TRANSFER=1

python3 -c "import torch; assert torch.cuda.is_available(), torch.__version__"

python3 - <<'PY'
import os
import runpy
import sys

from huggingface_hub import snapshot_download

src = snapshot_download(
    repo_id=os.environ.get("LIFEMEM_SRC_REPO", "mtorres98/lifemem-replication-src"),
    repo_type="dataset",
    token=os.environ.get("HF_TOKEN"),
)
os.environ["LIFEMEM_SRC_MOUNT"] = src
if src not in sys.path:
    sys.path.insert(0, src)
runpy.run_path(f"{src}/scripts/hf_job.py", run_name="__main__")
PY
