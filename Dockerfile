# 多阶段构建 Dockerfile - 不包含源码的 CosyVoice3 FastAPI 服务端
# 基于 NVIDIA CUDA 12.4.1 基础镜像，直接支持显卡

# 第一阶段：构建环境
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 AS builder

ARG VENV_NAME=cosyvoice
ENV VENV=${VENV_NAME}
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "--login", "-c"]

# 安装系统依赖
RUN apt-get update -y --fix-missing && \
    apt-get install -y \
    git \
    build-essential \
    curl \
    wget \
    ffmpeg \
    unzip \
    git-lfs \
    sox \
    libsox-dev \
    && apt-get clean \
    && git lfs install

# 安装 miniforge (使用清华镜像指定版本)
RUN wget --no-check-certificate https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-25.3.0-3-Linux-x86_64.sh -O /tmp/miniforge.sh && \
    /bin/bash /tmp/miniforge.sh -b -p /opt/conda && \
    rm /tmp/miniforge.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> /opt/nvidia/entrypoint.d/100.conda.sh && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate ${VENV}" >> /opt/nvidia/entrypoint.d/110.conda_default_env.sh && \
    echo "conda activate ${VENV}" >> $HOME/.bashrc

ENV PATH=/opt/conda/bin:/opt/conda/envs/${VENV}/bin:$PATH
ENV PYTHONPATH=/workspace/CosyVoice:/workspace/CosyVoice/third_party/Matcha-TTS

# 配置 conda
RUN conda config --add channels conda-forge && \
    conda config --set channel_priority strict

# 创建 conda 环境
RUN conda create -y -n ${VENV} python=3.10
ENV CONDA_DEFAULT_ENV=${VENV}
ENV PATH=/opt/conda/bin:/opt/conda/envs/${VENV}/bin:$PATH

WORKDIR /workspace

# 复制项目文件
COPY . /workspace/CosyVoice/

# 切换到工作目录
WORKDIR /workspace/CosyVoice

# 安装依赖
RUN conda run -n ${VENV} conda install -y -c conda-forge pynini==2.1.5

# 调试：打印当前目录内容，检查 requirements.txt 是否存在
RUN ls -laR

RUN conda run -n ${VENV} pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

# 编译所有 Python 文件为 .pyc
RUN conda run -n ${VENV} python -m compileall -b . && \
    find . -name "*.py" -type f -delete && \
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 第二阶段：运行环境
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ARG VENV_NAME=cosyvoice
ENV VENV=${VENV_NAME}
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "--login", "-c"]

# 安装运行时系统依赖
RUN apt-get update -y --fix-missing && \
    apt-get install -y \
    curl \
    wget \
    ffmpeg \
    sox \
    libsox-dev \
    && apt-get clean

# 安装 miniforge (使用清华镜像指定版本)
RUN wget --no-check-certificate https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-25.3.0-3-Linux-x86_64.sh -O /tmp/miniforge.sh && \
    /bin/bash /tmp/miniforge.sh -b -p /opt/conda && \
    rm /tmp/miniforge.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> /opt/nvidia/entrypoint.d/100.conda.sh && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate ${VENV}" >> /opt/nvidia/entrypoint.d/110.conda_default_env.sh && \
    echo "conda activate ${VENV}" >> $HOME/.bashrc

ENV PATH=/opt/conda/bin:/opt/conda/envs/${VENV}/bin:$PATH
ENV PYTHONPATH=/workspace/CosyVoice:/workspace/CosyVoice/third_party/Matcha-TTS

# 配置 conda
RUN conda config --add channels conda-forge && \
    conda config --set channel_priority strict

# 创建 conda 环境
RUN conda create -y -n ${VENV} python=3.10
ENV CONDA_DEFAULT_ENV=${VENV}
ENV PATH=/opt/conda/bin:/opt/conda/envs/${VENV}/bin:$PATH

WORKDIR /workspace/CosyVoice

# 从构建阶段复制 conda 环境
COPY --from=builder /opt/conda/envs/${VENV} /opt/conda/envs/${VENV}

# 从构建阶段复制编译后的文件
COPY --from=builder /workspace/CosyVoice /workspace/CosyVoice

# 设置环境变量
ENV SENSEVOICE_DEVICE=cuda:0

# 暴露端口
EXPOSE 50000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:50000/docs || exit 1

# 启动命令
CMD ["conda", "run", "--no-capture-output", "-n", "cosyvoice", "python", "runtime/python/fastapi/server.pyc", "--port", "50000"] 