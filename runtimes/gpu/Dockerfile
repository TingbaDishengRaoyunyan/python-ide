# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv git && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip && python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
WORKDIR /workspace
CMD ["python3", "-c", "import torch; print(torch.cuda.is_available()); print(torch.__version__)"]
