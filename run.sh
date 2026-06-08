#!/bin/bash
# ─── Conversator Backend Launcher ───
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="$PROJECT_ROOT/venv310"

# ── Activate venv ──
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
else
    echo "ERROR: venv not found at $VENV"
    echo "Create it with: python3.10 -m venv venv310"
    exit 1
fi

# ── CUDA library paths (nvidia wheel bundles) ──
PYTHON_VERSION="python$(python3 -c 'import sys; print(str(sys.version_info.major) + "." + str(sys.version_info.minor))')"
NVIDIA_LIBS="$VENV/lib/$PYTHON_VERSION/site-packages/nvidia"

if [ -d "$NVIDIA_LIBS" ]; then
    for lib in cublas cudnn cuda_runtime cuda_nvrtc; do
        lib_path="$NVIDIA_LIBS/$lib/lib"
        if [ -d "$lib_path" ]; then
            export LD_LIBRARY_PATH="$lib_path:${LD_LIBRARY_PATH:-}"
        fi
    done
fi

# ── Load .env ──
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | grep -v '^$' | xargs)
fi

# ── Verify CUDA ──
echo "── CUDA Check ──"
python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
else:
    print('WARNING: CUDA not available, will use CPU')
"

echo ""
echo "── Starting Conversator Backend ──"
echo ""

cd "$SCRIPT_DIR"
exec "$VENV/bin/python" -m app.main
