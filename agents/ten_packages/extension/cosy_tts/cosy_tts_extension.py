
# 导入追踪栈中函数调用的库
import traceback

# 导入TEN SDK中的扩展、环境、命令、音频帧、音频帧数据格式、数据、状态码和命令结果等模块
from ten import (
    Extension,
    TenEnv,
    Cmd,
    AudioFrame,
    AudioFrameDataFmt,
    Data,
    StatusCode,
    CmdResult,
)

# 导入python内置的typing模块中的List和Any，用于类型提示
from typing import List, Any

# 导入阿里云语音合成服务SDK中的SpeechSynthesizer和ResultCallback类
import dashscope
from dashscope.audio.tts_v2 import ResultCallback, SpeechSynthesizer, AudioFormat

# 导入cosy_tts_extension模块中的queue和threading模块，用于创建队列和线程
import queue
import threading

# 导入python内置的datetime模块，用于处理时间
from datetime import datetime

# 导入自定义的日志记录器模块log，用于记录日志信息
from.log import logger


# 定义了一个CosyTTSCallback类，继承自ResultCallback类。这个类负责处理语音合成的回调事件，包括打开、完成、错误、关闭等。
class CosyTTSCallback(ResultCallback):
    def __init__(self, ten: TenEnv, sample_rate: int, need_interrupt_callback):
        """
        初始化CosyTTSCallback对象，设置相关属性。

        参数：
        ten (TenEnv)：与扩展关联的TenEnv对象。
        sample_rate (int)：音频采样率。
        need_interrupt_callback：回调函数，用于确定是否需要中断。

        设置frame_size为根据采样率计算的一帧音频数据的大小，以字节为单位。
        设置ts为当前任务的时间戳，init_ts为初始化时的时间戳。
        设置ttfb为None。
        设置need_interrupt_callback属性。
        设置closed属性为False。
        """
        super().__init__()
        self.ten = ten
        self.sample_rate = sample_rate
        self.frame_size = int(self.sample_rate * 1 * 2 / 100)
        self.ts = datetime.now()  # current task ts
        self.init_ts = datetime.now()
        self.ttfb = None  # time to first byte
        self.need_interrupt_callback = need_interrupt_callback
        self.closed = False

    def need_interrupt(self) -> bool:
        """
        检查是否需要中断当前任务。

        返回：
        bool：如果需要中断则返回True，否则返回False。

        调用need_interrupt_callback并传入当前时间戳，根据返回值判断是否需要中断。
        """
        return self.need_interrupt_callback(self.ts)

    def set_input_ts(self, ts: datetime):
        """
        设置输入文本的时间戳。

        参数：
        ts (datetime)：输入文本的时间戳。

        设置ts属性，更新任务的时间戳，确保后续处理基于新的时间。
        """
        self.ts = ts

    def on_open(self):
        """
        在语音合成任务开始时被调用，记录一条日志信息。
        """
        logger.info("websocket is open.")

    def on_complete(self):
        logger.info("speech synthesis task complete successfully.")

    def on_error(self, message: str):
        logger.info(f"speech synthesis task failed, {message}")

    def on_close(self):
        logger.info("websocket is closed.")
        self.closed = True

    def on_event(self, message):
        pass
        # logger.info(f"recv speech synthsis message {message}")

    def get_frame(self, data: bytes) -> AudioFrame:
        """
        将字节数据转换为音频帧对象。

        参数：
        data (bytes)：音频数据的字节表示。

        返回：
        AudioFrame：包含音频数据的音频帧对象。

        创建一个名为pcm_frame的音频帧对象。
        设置音频帧的采样率、每个样本的字节数、通道数和时间戳。
        将音频数据格式设置为交错模式。
       根据音频数据的长度计算样本数量，并为音频帧分配内存。
       锁定内存缓冲区，并将音频数据复制到缓冲区。
       解锁内存缓冲区并返回音频帧对象。
        """
        f = AudioFrame.create("pcm_frame")
        f.set_sample_rate(self.sample_rate)
        f.set_bytes_per_sample(2)
        f.set_number_of_channels(1)
        # f.set_timestamp = 0
        f.set_data_fmt(AudioFrameDataFmt.INTERLEAVE)
        f.set_samples_per_channel(len(data) // 2)
        f.alloc_buf(len(data))
        buff = f.lock_buf()
        buff[:] = data
        f.unlock_buf(buff)
        return f

    def on_data(self, data: bytes) -> None:
        """
        当语音合成结果数据准备好时，将会调用这个方法。

        参数：
        data (bytes)：合成的音频数据，以字节数组的形式传递。

        这个方法首先会检查是否需要中断当前的语音合成任务。如果需要中断，它将立即返回，不会处理数据。
        如果不需要中断，它会检查`ttfb`（time to first byte）是否为`None`。`ttfb`用于标记从任务开始到接收到第一个音频字节的时间间隔。如果`ttfb`为`None`，意味着这是任务开始后接收到的第一个音频字节，它会记录当前时间与初始化时间之间的时间差，并将其记录为`ttfb`，然后通过日志输出。
        接着，`on_data`方法会将音频数据转换为音频帧对象，通过`get_frame`方法实现。这涉及到对音频数据的解析和填充到音频帧对象的缓冲区中，确保其正确的声道、采样率和格式。
        最后，`on_data`方法会调用`ten`对象的`send_audio_frame`方法，将音频帧对象发送到目标接收端。这可能是一个音频播放器或者其他音频处理组件，具体行为取决于`ten`对象的实现。
        在`CosyTTSCallback`类初始化后，它被用作语音合成任务的回调处理程序。一旦任务开始，它将根据从语音合成服务接收到的音频数据做出响应。例如，它可能在一个循环中不断检查服务端发送来的音频数据，一旦有新的数据到达，它将更新并传递音频帧给接收端。

        总结来说，`CosyTTSCallback`类充当了数据处理器和分发器的角色，确保音频数据被正确地格式化、记录（在`ttfb`的情况下）并发送给最终的音频消费组件。
        """
        if self.need_interrupt():
            return

        if self.ttfb is None:
            self.ttfb = datetime.now() - self.init_ts
            logger.info("TTS TTFB {}ms".format(int(self.ttfb.total_seconds() * 1000)))

        # logger.info("audio result length: %d, %d", len(data), self.frame_size)
        try:
            f = self.get_frame(data)
            self.ten.send_audio_frame(f)
        except Exception as e:
            logger.exception(e)


# 定义了一个名为CosyTTSExtension的类，继承自Extension类。这个类实现了一个语音合成扩展，用于处理文本到语音的转换任务。

class CosyTTSExtension(Extension):
    def __init__(self, name: str):
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
        self.api_key = ""
        self.voice = ""
        self.model = ""
        self.sample_rate = 16000
        self.tts = None
        self.callback = None
        self.format = None

        self.outdate_ts = datetime.now()

        self.stopped = False
        self.thread = None
        self.queue = queue.Queue()

    def on_start(self, ten: TenEnv) -> None:
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
        logger.info("on_start")
        self.api_key = ten.get_property_string("api_key")
        self.voice = ten.get_property_string("voice")
        self.model = ten.get_property_string("model")
        self.sample_rate = ten.get_property_int("sample_rate")

        dashscope.api_key = self.api_key
        f = AudioFormat.PCM_16000HZ_MONO_16BIT
        if self.sample_rate == 8000:
            f = AudioFormat.PCM_8000HZ_MONO_16BIT
        elif self.sample_rate == 16000:
            f = AudioFormat.PCM_16000HZ_MONO_16BIT
        elif self.sample_rate == 22050:
            f = AudioFormat.PCM_22050HZ_MONO_16BIT
        elif self.sample_rate == 24000:
            f = AudioFormat.PCM_24000HZ_MONO_16BIT
        elif self.sample_rate == 44100:
            f = AudioFormat.PCM_44100HZ_MONO_16BIT
        elif self.sample_rate == 48000:
            f = AudioFormat.PCM_48000HZ_MONO_16BIT
        else:
            logger.error("unknown sample rate %d", self.sample_rate)
            exit()

        self.format = f

        self.thread = threading.Thread(target=self.async_handle, args=[ten])
        self.thread.start()
        ten.on_start_done()

    def on_stop(self, ten: TenEnv) -> None:
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
        logger.info("on_stop")
        self.stopped = True
        self.flush()
        self.queue.put(None)
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        ten.on_stop_done()

    def need_interrupt(self, ts: datetime.time) -> bool:
        """
        通过比较给定的时间戳ts是否超过outdate_ts，返回是否需要中断。

        参数：
        ts (datetime.time)：要比较的时间戳。

        返回：
        bool：如果给定的时间戳超过outdate_ts，则返回True，否则返回False。

        在逻辑中，outdate_ts是在初始化CosyTTSExtension对象时设置的一个属性，它代表了一个过去的时间点。这个过去的时间点通常用来标记一段数据或任务已经过期。
        need_interrupt方法的目的是检查给定的时间戳ts是否在outdate_ts之后。如果ts在outdate_ts之后，这意味着它是在过期时间之后的某个时间点，因此可能需要中断或终止与这个时间戳相关联的任务或数据处理。
        返回值为True，表示应该中断当前任务或数据处理，因为它已经过期；返回值为False，则表示任务或数据处理可以继续，因为它还没有过期。
        """
        return self.outdate_ts > ts

    def async_handle(self, ten: TenEnv):
        """
        异步处理音频数据的入口点。

        参数：
            ten (TenEnv): 扩展的运行时环境。

        返回：
            None

        使用一个无限循环，直到`stopped`标志设置为True才会结束。它检查队列中是否有新数据。如果有，它将创建一个新的`SpeechSynthesizer`对象，并调用`streaming_call`方法。最后，如果当前音频片段结束，调用`streaming_complete`方法来处理音频数据。
        """
        try:
            # 初始化语音合成器和回调对象
            tts = None
            callback = None
            while not self.stopped:
                try:
                    # 从队列中获取音频数据
                    value = self.queue.get()
                    if value is None:
                        # 如果队列为空，则退出循环
                        break
                    input_text, ts, end_of_segment = value

                    # 如果旧的语音合成器已关闭，则清理它并创建一个新的
                    if callback is not None and callback.closed is True:
                        tts = None
                        callback = None

                    # 如果需要中断上一个语音合成任务，取消它
                    if (
                        callback is not None
                        and tts is not None
                        and callback.need_interrupt()
                    ):
                        tts.streaming_cancel()
                        tts = None
                        callback = None

                    if self.need_interrupt(ts):
                        logger.info("drop outdated input")
                        continue

                    # 如果需要，创建新的语音合成器
                    if tts is None or callback is None:
                        logger.info("creating tts")
                        callback = CosyTTSCallback(
                            ten, self.sample_rate, self.need_interrupt
                        )
                        tts = SpeechSynthesizer(
                            model=self.model,
                            voice=self.voice,
                            format=self.format,
                            callback=callback,
                        )

                    logger.info(
                        "on message [{}] ts [{}] end_of_segment [{}]".format(
                            input_text, ts, end_of_segment
                        )
                    )

                    # 确保新数据不会被标记为过时
                    callback.set_input_ts(ts)

                    if len(input_text) > 0:
                        # 如果有文本数据，则调用streaming_call方法进行语音合成
                        tts.streaming_call(input_text)

                    # 完成语音合成任务，处理剩余音频数据
                    if True:  # end_of_segment:
                        try:
                            tts.streaming_complete()
                        except Exception as e:
                            logger.warning(e)
                        tts = None
                        callback = None
                except Exception as e:
                    logger.exception(e)
                    logger.exception(traceback.format_exc())
        finally:
            if tts is not None:
                tts.streaming_cancel()
                tts = None
                callback = None

    def flush(self):
        """
        清空队列。

        在while循环中使用self.queue.get()方法，针对队列中的每个值调用queue.get()，进行清空操作。
        """
        while not self.queue.empty():
            self.queue.get()

    def on_data(self, ten: TenEnv, data: Data) -> None:
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

    def on_cmd(self, ten: TenEnv, cmd: Cmd) -> None:
        """
        扩展接收到命令时的回调方法。

        参数：
        ten (TenEnv)：与扩展关联的TenEnv对象。
        cmd (Cmd)：包含命令信息的Cmd对象。

        获取cmd对象的名称。
        记录一条日志信息，表明接收到新的命令，包含命令的名称。
        根据命令名称做不同的处理：
        如果命令名称为"flush"，更新outdate_ts为当前时间。
        调用flush方法。
        创建一个名为flush的cmd_out对象。
        通过ten对象发送cmd_out对象。
        通过ten对象返回cmd_result对象，表明命令处理成功，并包含详细信息。
        如果命令名称为其他的，记录一条日志信息，表明遇到未知的命令。
        通过ten对象返回cmd_result对象，表明命令处理成功。
        """
        cmd_name = cmd.get_name()
        logger.info("on_cmd {}".format(cmd_name))
        if cmd_name == "flush":
            self.outdate_ts = datetime.now()
            self.flush()
            cmd_out = Cmd.create("flush")
            ten.send_cmd(cmd_out, lambda ten, result: print("send_cmd flush done"))
        else:
            logger.info("unknown cmd {}".format(cmd_name))

        cmd_result = CmdResult.create(StatusCode.OK)
        cmd_result.set_property_string("detail", "success")
        ten.return_result(cmd_result, cmd)
        
