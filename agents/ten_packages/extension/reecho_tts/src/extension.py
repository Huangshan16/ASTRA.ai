#
# Agora Real Time Engagement
# Created by Wei Hu in 2024-08.
# Copyright (c) 2024 Agora IO. All rights reserved.
#
#
from ten import (
    AudioFrame,
    VideoFrame,
    Extension,
    TenEnv,
    Cmd,
    StatusCode,
    CmdResult,
    Data,
)
from .log import logger
import json
import requests

class Reecho_ttsExtension(Extension):
    def __init__(self, name):
        super().__init__(name)
        self.api_url = "https://v1.reecho.cn/api/tts/simple-generate"

    def on_init(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_init")
        ten_env.on_init_done()

    def on_start(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_start")
        ten_env.on_start_done()

    def on_stop(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_stop")
        ten_env.on_stop_done()

    def on_deinit(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_deinit")
        ten_env.on_deinit_done()

    def on_cmd(self, ten_env: TenEnv, cmd: Cmd) -> None:
        cmd_name = cmd.get_name()
        logger.info("on_cmd name {}".format(cmd_name))

        if cmd_name == "generate_tts":
            payload = json.loads(cmd.get_payload())
            result = self.generate_tts(payload)
            cmd_result = CmdResult.create(StatusCode.OK, json.dumps(result))
        else:
            cmd_result = CmdResult.create(StatusCode.ERR_INVALID_ARGUMENT, "未知命令")

        ten_env.return_result(cmd_result, cmd)

    def on_data(self, ten_env: TenEnv, data: Data) -> None:
        pass

    def on_audio_frame(self, ten_env: TenEnv, audio_frame: AudioFrame) -> None:
        pass

    def on_image_frame(self, ten_env: TenEnv, video_frame: VideoFrame) -> None:
        pass

    def generate_tts(self, payload):
        headers = {
            'User-Agent': 'Bearer sk-b71481e4d2b6cbc8e2a9d910207ab4e2',
            'Content-Type': 'Authorization'
        }
        
        default_payload = {
            "voiceId": "bf2e0fe3-1988-42d6-95e7-2b8fd36f4d2f",
            "text": "你好呀！你今天感觉怎么样？",
            "texts": ["你好呀！你今天感觉怎么样？"],
            "promptId": "default",
            "model": "reecho-neural-voice-001",
            "randomness": 97,
            "stability_boost": 100,
            "probability_optimization": 99,
            "break_clone": False,
            "flash": False,
            "origin_audio": False,
            "stream": False,
            "seed": -1
        }
        
        # 更新默认payload与用户提供的payload
        default_payload.update(payload)
        
        try:
            response = requests.post(self.api_url, headers=headers, json=default_payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"生成TTS时发生错误: {str(e)}")
            return {"status": 500, "message": "服务器内部错误", "data": None}