import json
import requests
from typing import Union, List

from .log import logger

class ReechoConfig:
    def __init__(self,
            voice_id: str,
            prompt_id: str = "default",
            model: str = "reecho-neural-voice-001",
            randomness: int = 97,
            stability_boost: int = 100,
            probability_optimization: int = 99,
            break_clone: bool = False,
            flash: bool = False,
            origin_audio: bool = False,
            stream: bool = False,
            seed: int = -1):

        self.voice_id = voice_id
        self.prompt_id = prompt_id
        self.model = model
        self.randomness = randomness
        self.stability_boost = stability_boost
        self.probability_optimization = probability_optimization
        self.break_clone = break_clone
        self.flash = flash
        self.origin_audio = origin_audio
        self.stream = stream
        self.seed = seed

    @classmethod
    def default_config(cls):
        return cls(
            voice_id="bf2e0fe3-1988-42d6-95e7-2b8fd36f4d2f",
            prompt_id="default",
            model="reecho-neural-voice-001",
            randomness=97,
            stability_boost=100,
            probability_optimization=99,
            stream=False
        )

class ReechoWrapper:
    def __init__(self, config: ReechoConfig, api_url: str = "https://v1.reecho.cn/api/tts/simple-generate"):
        self.config = config
        self.api_url = api_url

    def synthesize(self, text: Union[str, List[str]]):
        try:
            payload = {
                "voiceId": self.config.voice_id,
                "promptId": self.config.prompt_id,
                "model": self.config.model,
                "randomness": self.config.randomness,
                "stability_boost": self.config.stability_boost,
                "probability_optimization": self.config.probability_optimization,
                "break_clone": self.config.break_clone,
                "flash": self.config.flash,
                "origin_audio": self.config.origin_audio,
                "stream": self.config.stream,
                "seed": self.config.seed
            }

            if isinstance(text, str):
                payload["text"] = text
            else:
                payload["texts"] = text

            headers = {
                'User-Agent': 'sk-b71481e4d2b6cbc8e2a9d910207ab4e2',
                'Content-Type': 'application/json'
            }

            response = requests.post(self.api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            data = response.json()['data']
            
            if self.config.stream:
                return data['streamUrl'], None
            else:
                return data['audio'], None

        except requests.RequestException as e:
            logger.exception("Couldn't get audio stream.")
            raise

    # 其他方法可以根据需要添加,比如获取可用的语音列表等