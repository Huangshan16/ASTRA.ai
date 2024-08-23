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
# 导入追踪栈中函数调用的库
import traceback
# 导入python内置的typing模块中的List和Any，用于类型提示
from typing import List, Any
# 导入python内置的datetime模块，用于处理时间
from datetime import datetime
# 导入自定义的日志记录器模块log，用于记录日志信息
from .log import logger
# 导入 json 模块，用于处理 JSON 格式的数据
import json
# 导入 requests 模块，用于发送 HTTP 请求
import requests
# 导入queue和threading模块，用于创建队列和线程
import queue
import threading


class Reecho_ttsExtension(Extension):
    def __init__(self, name):
        """
        初始化CosyTTSExtension对象，设置属性的默认值。

        参数：
        name (str)：扩展的名称。

        设置api_key、voice、model和format属性为None。
        设置sample_rate属性为16000。
        设置outdate_ts属性为当前时间。
        设置stopped标志为False。
        创建一个queue.Queue对象，并设置thread为None。
        """
        super().__init__(name)
        self.api_url = "https://v1.reecho.cn/api/tts/simple-generate"
        self.voice_id = ""
        self.default_text = ""
        self.default_texts = [""]
        self.prompt_id = "default"
        self.model = "reecho-neural-voice-001"
        self.randomness = 97
        self.stability_boost = 100
        self.probability_optimization = 99
        self.break_clone = False
        self.flash = False
        self.origin_audio = False
        self.stream = False
        self.seed = -1
    
        # 初始化停止标志为False
        self.stopped = False
        # 初始化线程为None
        self.thread = None
        # 创建一个新的队列用于异步处理
        self.queue = queue.Queue()


    def on_init(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_init")
        ten_env.on_init_done()

    def on_start(self, ten_env: TenEnv) -> None:
        """
        扩展启动时的处理逻辑。

        参数：
        ten (TenEnv)：与扩展关联的TenEnv对象。

        记录一条日志信息。
        从ten对象中获取api_key、voice、model和sample_rate属性，并打印日志。
        根据sample_rate属性设置format格式。
        创建一个线程，启动异步处理任务。
        调用ten的on_start_done方法，表示启动完成。
        """
        logger.info("Reecho_ttsExtension on_start")
        self.api_url = ten_env.get_property_string("api_url", self.api_url)
        self.voice_id = ten_env.get_property_string("voice_id", self.voice_id)
        self.default_text = ten_env.get_property_string("default_text", self.default_text)
        self.default_texts = ten_env.get_property_list("default_texts", self.default_texts)
        self.prompt_id = ten_env.get_property_string("prompt_id", self.prompt_id)
        self.model = ten_env.get_property_string("model", self.model)
        self.randomness = ten_env.get_property_int("randomness", self.randomness)
        self.stability_boost = ten_env.get_property_int("stability_boost", self.stability_boost)
        self.probability_optimization = ten_env.get_property_int("probability_optimization", self.probability_optimization)
        self.break_clone = ten_env.get_property_bool("break_clone", self.break_clone)
        self.flash = ten_env.get_property_bool("flash", self.flash)
        self.origin_audio = ten_env.get_property_bool("origin_audio", self.origin_audio)
        self.stream = ten_env.get_property_bool("stream", self.stream)
        self.seed = ten_env.get_property_int("seed", self.seed)

        self.thread = threading.Thread(target=self.async_handle, args=[ten_env])
        self.thread.start()
        ten_env.on_start_done()

    def on_stop(self, ten_env: TenEnv) -> None:
        """
        扩展停止时的处理逻辑。

        参数：
        ten (TenEnv)：与扩展关联的TenEnv对象。

        记录一条日志信息。
        将stopped标志设置为True。
        清空队列。
        启动一个线程，通过queue.put(None)来安全地停止异步处理线程。
        等待异步处理线程结束。
        调用ten的on_stop_done方法，表示停止完成。
        """
        logger.info("Reecho_ttsExtension on_stop")
        self.stopped = True
        self.flush()
        self.queue.put(None)
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        ten_env.on_stop_done()

    def flush(self):
        """
        清空队列。

        在while循环中使用self.queue.get()方法，针对队列中的每个值调用queue.get()，进行清空操作。
        """
        while not self.queue.empty():
            self.queue.get()

    def on_deinit(self, ten_env: TenEnv) -> None:
        logger.info("Reecho_ttsExtension on_deinit")
        ten_env.on_deinit_done()

    def on_data(self, ten_env: TenEnv, data: Data) -> None:
        """
        扩展接收到新数据时的回调方法。

        参数：
        ten (TenEnv)：与扩展关联的TenEnv对象。
        data (Data)：包含文本和其他属性的Data对象。

        获取data对象中的text属性。
        通过ten对象获取text属性的字符串值，并赋值给inputText。
        通过ten对象获取end_of_segment属性，并将其赋值给end_of_segment。
        记录一条日志信息，表明接收到新的数据，包含inputText和end_of_segment的值。
        将(inputText, datetime.now(), end_of_segment)作为三元组放入队列。
        """
        inputText = data.get_property_string("text")
        end_of_segment = data.get_property_bool("end_of_segment")

        logger.info("on data {} {}".format(inputText, end_of_segment))
        self.queue.put((inputText, datetime.now(), end_of_segment))

    def on_cmd(self, ten_env: TenEnv, cmd: Cmd) -> None:
        cmd_name = cmd.get_name()
        logger.info("on_cmd {}".format(cmd_name))

        if cmd_name == "flush":
            self.outdate_ts = datetime.now()
            self.flush()
            cmd_out = Cmd.create("flush")
            ten_env.send_cmd(cmd_out, lambda ten, result: print("send_cmd flush done"))
            # 在flush指令时同时执行generate_tts任务
            payload = json.loads(cmd.get_payload())
            result = self.generate_tts(payload)
            logger.info("generated result: {}".format(result))
        else:
            logger.info("unknown cmd: {}".format(cmd_name))

        cmd_result = CmdResult.create(StatusCode.OK)
        cmd_result.set_property_string("detail", "success")
        ten_env.return_result(cmd_result, cmd)

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