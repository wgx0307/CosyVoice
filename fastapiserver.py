# HTTP TTS API: 接收字符串，返回合成音频
import os
import sys
import argparse
import logging
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
import torch

sys.path.append('third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import CosyVoice2

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

# 单例模式，服务启动即加载模型
class CosyVoice2Singleton:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # 可根据实际模型路径调整
            cls._instance = CosyVoice2("pretrained_models/CosyVoice2-0.5B")
        return cls._instance

CosyVoice2Singleton.get_instance()

# 音频流生成器
def generate_data(model_output):
    for i in model_output:
        tts_audio = (i['tts_speech'].numpy() * (2 ** 15)).astype(np.int16).tobytes()
        yield tts_audio

@app.post("/tts")
async def tts_api(text: str = Form(...)):
    """
    接收字符串text，返回合成音频流（wav格式，16k采样率，单通道）
    """
    cosyvoice = CosyVoice2Singleton.get_instance()
    # 这里可根据实际需求选择推理接口
    # 例：inference_zero_shot 需提供 prompt_text/prompt_speech_16k
    # 这里只用 SFT 方式（需模型支持）
    # spk_id = "speaker1"  # 可扩展为参数
    # prompt_speech_16k = load_wav('./asset/zero_shot_prompt.wav', 16000)
    # prompt_text = '希望你以后能够做的比我还好呦。'
    model_output = cosyvoice.inference_zero_shot(text,
                    prompt_text = "",  # 使用空字符串，因为我们已经有了预提取的特征
                    prompt_speech_16k = torch.zeros(1, 16000),  # 占位符
                    stream=False, speed=1.5, zero_shot_spk_id=spk_id)
    return StreamingResponse(generate_data(model_output), media_type="audio/wav")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7007)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port, workers=1)
