"""HarvestShield UK package."""

import os

# Prevent macOS dual-OpenMP conflicts between LightGBM and PyTorch in the same process.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
