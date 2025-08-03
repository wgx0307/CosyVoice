# CosyVoice3 Docker 部署指南

本项目提供了基于 FastAPI 的 CosyVoice3 语音合成服务的 Docker 部署方案，**最终镜像中不包含源码**，只包含编译后的字节码文件。基于 NVIDIA CUDA 12.4.1 构建，直接支持 GPU 加速。

## 特性

- ✅ **源码保护**: 使用多阶段构建，最终镜像只包含编译后的 `.pyc` 文件
- ✅ **GPU 加速**: 基于 NVIDIA CUDA 12.4.1，直接支持显卡加速
- ✅ **Conda 环境**: 使用 conda 管理 Python 环境，确保依赖兼容性
- ✅ **轻量化**: 通过 `.dockerignore` 排除不必要的文件，减小镜像大小
- ✅ **健康检查**: 内置健康检查机制
- ✅ **跨平台**: 提供 Linux 和 Windows 构建脚本
- ✅ **智能检测**: 自动检测 GPU 支持，支持 CPU 降级模式

## 系统要求

### 硬件要求
- **GPU**: NVIDIA GPU (推荐 RTX 3060 或更高)
- **内存**: 至少 8GB RAM (推荐 16GB+)
- **存储**: 至少 20GB 可用磁盘空间
- **CPU**: 支持 AVX2 指令集

### 软件要求
- **操作系统**: Ubuntu 20.04+, Windows 10+, macOS 10.15+
- **Docker**: Docker 20.10+ 或 Docker Desktop 4.0+
- **NVIDIA 驱动**: 版本 470+ (GPU 版本)
- **NVIDIA Docker Runtime**: 用于 GPU 支持

## 快速开始

### 1. 检查系统信息

**Linux/macOS:**
```bash
chmod +x build_docker.sh
./build_docker.sh info
```

**Windows:**
```powershell
.\build_docker.ps1 info
```

### 2. 构建镜像

**Linux/macOS:**
```bash
./build_docker.sh build
```

**Windows:**
```powershell
.\build_docker.ps1 build
```

### 3. 运行服务

**Linux/macOS:**
```bash
./build_docker.sh run
```

**Windows:**
```powershell
.\build_docker.ps1 run
```

### 4. 一键构建并运行

**Linux/macOS:**
```bash
./build_docker.sh all
```

**Windows:**
```powershell
.\build_docker.ps1 all
```

## GPU 支持配置

### 1. 安装 NVIDIA 驱动

**Ubuntu:**
```bash
sudo apt update
sudo apt install nvidia-driver-535
sudo reboot
```

**Windows:**
从 [NVIDIA 官网](https://www.nvidia.com/Download/index.aspx) 下载并安装最新驱动。

### 2. 安装 NVIDIA Docker Runtime

**Ubuntu:**
```bash
# 添加 NVIDIA 仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 安装
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**Windows:**
Docker Desktop 4.0+ 已内置 NVIDIA 支持，无需额外配置。

### 3. 验证 GPU 支持

```bash
# 测试 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## API 接口

服务启动后，可以通过以下地址访问：

- **服务地址**: http://localhost:50000
- **API 文档**: http://localhost:50000/docs
- **健康检查**: http://localhost:50000/docs (自动检查)

### 主要接口

1. **TTS 合成** (`/tts`)
   - 方法: POST
   - 参数: `reference_audio`, `reference_text`, `text`
   - 返回: MP3 音频文件

2. **语音识别** (`/asr`)
   - 方法: POST
   - 参数: `reference_audio`, `language`, `use_itn`
   - 返回: JSON 格式的识别结果

3. **零样本合成** (`/inference_zero_shot`)
   - 方法: POST
   - 参数: `tts_text`, `prompt_wav`
   - 返回: 音频流

4. **SFT 合成** (`/inference_sft`)
   - 方法: POST
   - 参数: `tts_text`, `spk_id`
   - 返回: 音频流

## 手动 Docker 命令

### 构建镜像
```bash
docker build -t cosyvoice3-fastapi .
```

### 运行容器 (GPU 模式)
```bash
docker run -d \
  --name cosyvoice3-server \
  -p 50000:50000 \
  --gpus all \
  -e SENSEVOICE_DEVICE=cuda:0 \
  --shm-size=2g \
  cosyvoice3-fastapi
```

### 运行容器 (CPU 模式)
```bash
docker run -d \
  --name cosyvoice3-server \
  -p 50000:50000 \
  -e SENSEVOICE_DEVICE=cpu \
  --shm-size=2g \
  cosyvoice3-fastapi
```

### 查看日志
```bash
docker logs -f cosyvoice3-server
```

### 进入容器
```bash
docker exec -it cosyvoice3-server bash
```

### 停止容器
```bash
docker stop cosyvoice3-server
docker rm cosyvoice3-server
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SENSEVOICE_DEVICE` | `cuda:0` | GPU 设备选择 (`cuda:0`, `cuda:1`, `cpu`) |
| `PYTHONPATH` | `/workspace/CosyVoice:/workspace/CosyVoice/third_party/Matcha-TTS` | Python 路径 |
| `VENV` | `cosyvoice` | Conda 环境名称 |

## 目录结构

```
/workspace/CosyVoice/
├── cosyvoice/          # 编译后的 cosyvoice 模块
├── runtime/
│   └── python/
│       └── fastapi/
│           └── server.pyc  # 主服务文件
├── third_party/        # 第三方依赖
├── pretrained_models/  # 预训练模型
└── iic/               # SenseVoice 模型
```

## 性能优化

### 1. GPU 内存优化
```bash
# 限制 GPU 内存使用
docker run -d --gpus '"device=0,capabilities=compute,utility"' cosyvoice3-fastapi
```

### 2. 系统内存优化
```bash
# 增加共享内存大小
docker run -d --shm-size=4g cosyvoice3-fastapi
```

### 3. 多 GPU 支持
```bash
# 使用多个 GPU
docker run -d --gpus all -e SENSEVOICE_DEVICE=cuda:0,1 cosyvoice3-fastapi
```

### 4. 多实例部署
```yaml
version: '3.8'
services:
  cosyvoice1:
    image: cosyvoice3-fastapi
    ports:
      - "50000:50000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - SENSEVOICE_DEVICE=cuda:0
  
  cosyvoice2:
    image: cosyvoice3-fastapi
    ports:
      - "50001:50000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - SENSEVOICE_DEVICE=cuda:1
```

## 故障排除

### 1. 构建失败

**问题**: 构建过程中出现依赖安装错误
**解决**: 
```bash
# 清理 Docker 缓存
docker system prune -a
# 重新构建
./build_docker.sh build
```

### 2. GPU 不可用

**问题**: 容器无法使用 GPU
**解决**:
```bash
# 检查 NVIDIA Docker 是否安装
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

# 如果没有安装，请参考 NVIDIA Docker 官方文档
```

### 3. 内存不足

**问题**: 容器启动失败，提示内存不足
**解决**: 
```bash
# 增加内存限制
docker run -d --memory=16g --gpus all cosyvoice3-fastapi
```

### 4. 端口冲突

**问题**: 端口 50000 被占用
**解决**: 修改端口映射
```bash
docker run -d -p 50001:50000 --name cosyvoice3-server cosyvoice3-fastapi
```

### 5. Conda 环境问题

**问题**: conda 环境激活失败
**解决**:
```bash
# 进入容器检查环境
docker exec -it cosyvoice3-server bash
conda info --envs
conda activate cosyvoice
```

## 安全注意事项

1. **源码保护**: 最终镜像中不包含 `.py` 源文件，只包含编译后的 `.pyc` 文件
2. **网络安全**: 生产环境建议使用反向代理和 HTTPS
3. **资源限制**: 建议设置容器资源限制，防止资源滥用
4. **日志管理**: 定期清理容器日志，避免磁盘空间不足
5. **GPU 安全**: 限制 GPU 访问权限，防止恶意使用

## 许可证

本项目遵循 Apache License 2.0 许可证。 