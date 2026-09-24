FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
CMD ["python3","-c","import torch; print({'torch':torch.__version__,'cuda':torch.cuda.is_available()})"]
