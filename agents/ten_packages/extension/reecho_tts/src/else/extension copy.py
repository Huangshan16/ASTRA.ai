#
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
from datetime import datetime
from contextlib import closing
from .wrapper import ReechoWrapper, ReechoConfig
import traceback
import queue
import threading
import requests

PROPERTY_ORIGIN_AUDIO = "origin_audio"
PROPERTY_VOICE_ID = "voice_id"
PROPERTY_MODEL = "model"
PROPERTY_PROMPT_ID = "prompt_id"
PROPERTY_RANDOMNESS = "randomness"
PROPERTY_STABILITY_BOOST = "stability_boost"
PROPERTY_PROBABILITY_OPTIMIZATION = "probability_optimization"
PROPERTY_BREAK_CLONE = "break_clone"
PROPERTY_FLASH = "flash"
PROPERTY_STREAM = "stream"
PROPERTY_SEED = "seed"
PROPERTY_API_URL = "api_url"

class Reecho_ttsExtension(Extension):
    def on_init(self, ten_env: TenEnv) -> None:
        super().on_init(ten_env)
        self.outdateTs = datetime.now()
        self.stopped = False
        self.thread = None
        self.queue = queue.Queue()
        self.frame_size = None
        self.bytes_per_sample = 2
        self.number_of_channels = 1

        logger.info("Reecho_ttsExtension on_init")
        ten_env.on_init_done()

    def on_start(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_start")

        tts_config = ReechoConfig.default_config()
        api_url = ""

        for prop in [PROPERTY_VOICE_ID, PROPERTY_MODEL, PROPERTY_PROMPT_ID, PROPERTY_RANDOMNESS,
                     PROPERTY_STABILITY_BOOST, PROPERTY_PROBABILITY_OPTIMIZATION, PROPERTY_BREAK_CLONE,
                     PROPERTY_FLASH, PROPERTY_STREAM, PROPERTY_SEED, PROPERTY_API_URL]:
            try:
                value = ten.get_property_string(prop).strip()
                if value:
                    if prop == PROPERTY_API_URL:
                        api_url = value
                    elif prop == PROPERTY_ORIGIN_AUDIO:
                        tts_config.origin_audio = value.lower() == 'true'
                    else:
                        setattr(tts_config, prop, value)
            except Exception as err:
                logger.debug(f"GetProperty optional {prop} failed, err: {err}. Using default value: {getattr(tts_config, prop, 'N/A')}")

        self.tts = ReechoWrapper(tts_config, api_url)
        self.frame_size = 1600  # 假设采样率为16000，每帧100ms
        self.thread = threading.Thread(target=self.async_tts_handler, args=[ten])
        self.thread.start()
        ten_env.on_start_done()

    def on_stop(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_stop")

        # 设置stopped变量为True，表示扩展需要停止
        self.stopped = True
        # 向队列中放入None，表示线程需要退出
        self.queue.put(None)
        # 刷新队列，确保所有数据都被处理
        self.flush()
        # 等待线程结束
        self.thread.join()

        # 通知tenEnv对象停止完成
        ten_env.on_stop_done()

    def on_deinit(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_deinit")
        ten_env.on_deinit_done()

    def on_cmd(self, ten_env: TenEnv, cmd: Cmd) -> None:
        cmd_name = cmd.get_name()
        logger.info("on_cmd name {}".format(cmd_name))

        cmd_result = CmdResult.create(StatusCode.OK)
        ten_env.return_result(cmd_result, cmd)

    def on_data(self, ten_env: TenEnv, data: Data) -> None:
        logger.info("ReechoTTSExtension on_data")
        inputText = data.get_property_string("text")
        if len(inputText) == 0:
            logger.info("ignore empty text")
            return

        is_end = data.get_property_bool("end_of_segment")

        logger.info("on data %s %d", inputText, is_end)
        self.queue.put((inputText, datetime.now()))

    def on_pcm_frame(self, ten_env: TenEnv, audio_frame: AudioFrame) -> None:
        # TODO: process pcm frame
        pass

    def on_image_frame(self, ten_env: TenEnv, video_frame: VideoFrame) -> None:
        # TODO: process image frame
        pass
