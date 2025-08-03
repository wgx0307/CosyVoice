# Copyright (c) 2024 Alibaba Inc (authors: Xiang Lyu)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import io
import os
import sys
import argparse
import logging

import torch
import torchaudio
from starlette.responses import FileResponse, Response

logging.getLogger('matplotlib').setLevel(logging.WARNING)
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append('{}/../../..'.format(ROOT_DIR))
sys.path.append('{}/../../../third_party/Matcha-TTS'.format(ROOT_DIR))
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
from cosyvoice.utils.file_utils import load_wav


import os

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

model_dir = "iic/SenseVoiceSmall"

model = AutoModel(
    model=model_dir,
    # vad_model="fsmn-vad",
    # vad_kwargs={"max_single_segment_time": 30000},
    device=os.getenv("SENSEVOICE_DEVICE", "cuda:0")
)
app = FastAPI()
# set cross region allowance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])


def generate_data(model_output):
    for i in model_output:
        tts_audio = (i['tts_speech'].numpy() * (2 ** 15)).astype(np.int16).tobytes()
        yield tts_audio


@app.get("/inference_sft")
@app.post("/inference_sft")
async def inference_sft(tts_text: str = Form(), spk_id: str = Form()):
    model_output = cosyvoice.inference_sft(tts_text, spk_id)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_zero_shot")
@app.post("/inference_zero_shot")
async def inference_zero_shot(tts_text: str = Form(), prompt_wav: UploadFile = File()):
    # en
    res = model.generate(
        input=prompt_wav.file,
        cache={},
        language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        # batch_size_s=60,
        # merge_vad=True,
        # merge_length_s=15,
        # ban_emo_unk=True,
    )
    prompt_text =  rich_transcription_postprocess(res[0]["text"])
    print(prompt_text)
    speed = 0.9



    prompt_speech_16k = load_wav(prompt_wav.file, 16000)
    model_output = cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_speech_16k,speed=speed)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_cross_lingual")
@app.post("/inference_cross_lingual")
async def inference_cross_lingual(tts_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_speech_16k = load_wav(prompt_wav.file, 16000)
    model_output = cosyvoice.inference_cross_lingual(tts_text, prompt_speech_16k)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct")
@app.post("/inference_instruct")
async def inference_instruct(tts_text: str = Form(), spk_id: str = Form(), instruct_text: str = Form()):
    model_output = cosyvoice.inference_instruct(tts_text, spk_id, instruct_text)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct2")
@app.post("/inference_instruct2")
async def inference_instruct2(tts_text: str = Form(), instruct_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_speech_16k = load_wav(prompt_wav.file, 16000)
    model_output = cosyvoice.inference_instruct2(tts_text, instruct_text, prompt_speech_16k)
    return StreamingResponse(generate_data(model_output))


@app.get("/asr")
@app.post("/asr")
async def audio_to_text(prompt_wav: UploadFile = File()):


    # en
    res = model.generate(
        input=prompt_wav.file,
        cache={},
        language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        # batch_size_s=60,
        # merge_vad=True,  #
        # merge_length_s=15,
        # ban_emo_unk=True,
    )
    prompt_text = rich_transcription_postprocess(res[0]["text"])
    # print(prompt_text)
    return {"result": [prompt_text]}


@app.get("/tts")
@app.post("/tts")
async def tts(tts_text: str = Form(),prompt_text: str = Form() ,prompt_wav: UploadFile = File()):

    speed = 1.0
    prompt_speech_16k = load_wav(prompt_wav.file, 16000)
    model_output = cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_speech_16k,speed=speed)
    # 1. 收集所有 chunks 成完整的 PCM 数据
    pcm_data = b"".join(generate_data(model_output))
    # 2. 转换为 torch.Tensor (int16)
    pcm_np = np.frombuffer(pcm_data, dtype=np.int16)
    tts_speech = torch.from_numpy(pcm_np).unsqueeze(0)  # shape: [1, samples]
    # 3. 使用 torchaudio 保存为 WAV（带 header）
    buffer = io.BytesIO()
    torchaudio.save(buffer, tts_speech, 22050, format="mp3")
    buffer.seek(0)  # 移动指针到开头

    # 4. 直接返回 WAV 文件
    return Response(
        content=buffer.read(),
        media_type="audio/mp3",
        headers={"Content-Disposition": "attachment; filename=output.mp3"}
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type=int,
                        default=50000)
    parser.add_argument('--model_dir',
                        type=str,
                        default='pretrained_models/CosyVoice2-0.5',
                        help='local path or modelscope repo id')
    args = parser.parse_args()
    try:
        cosyvoice = CosyVoice(args.model_dir)
    except Exception:
        try:
            cosyvoice = CosyVoice2(args.model_dir)
        except Exception:
            raise TypeError('no valid model_type!')
    uvicorn.run(app, host="0.0.0.0", port=args.port)
