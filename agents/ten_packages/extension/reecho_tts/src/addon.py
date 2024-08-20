#
#
# Agora Real Time Engagement
# Created by Wei Hu in 2024-08.
# Copyright (c) 2024 Agora IO. All rights reserved.
#
#
from ten import (
    Addon,
    register_addon_as_extension,
    TenEnv,
)
from .extension import Reecho_ttsExtension
from .log import logger


@register_addon_as_extension("reecho_tts")
class Reecho_ttsExtensionAddon(Addon):

    def on_create_instance(self, ten_env: TenEnv, name: str, context) -> None:
        logger.info("Reecho_ttsExtensionAddon on_create_instance")
        ten_env.on_create_instance_done(Reecho_ttsExtension(name), context)
