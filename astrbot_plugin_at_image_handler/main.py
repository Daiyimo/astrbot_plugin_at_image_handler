import time
from astrbot.api.event import filter, AstrMessageEvent, EventMessageType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from typing import Dict, Tuple

# 全局缓存：{(group_id, user_id): timestamp}
awaiting_image: Dict[Tuple[str, str], float] = {}

@register("at_image_handler", "YourName", "At 后处理图片", "1.0.0")
class AtImageHandlerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.bot_id = None  # 将在第一条消息中自动获取

    def _get_bot_id(self, event: AstrMessageEvent) -> str:
        """从事件中提取机器人自身 ID"""
        if self.bot_id is None:
            self.bot_id = event.message_obj.self_id
        return self.bot_id

    def _is_at_bot(self, event: AstrMessageEvent) -> bool:
        """判断消息是否 @ 了本机器人"""
        bot_id = self._get_bot_id(event)
        for comp in event.message_obj.message:
            if comp.type == "at":
                # comp 是 astrbot.api.message_components.At 类型
                if str(comp.qq) == bot_id:
                    return True
        return False

    def _get_image_url(self, event: AstrMessageEvent) -> str | None:
        """从消息链中提取图片 URL"""
        for comp in event.message_obj.message:
            if comp.type == "image":
                # comp 是 astrbot.api.message_components.Image
                if hasattr(comp, 'url') and comp.url:
                    return comp.url
                if hasattr(comp, 'file') and comp.file.startswith("http"):
                    return comp.file
        return None

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def handle_group_message(self, event: AstrMessageEvent):
        """
        监听所有群消息，实现 @ + 图片 关联逻辑
        """
        group_id = event.message_obj.group_id
        user_id = event.get_sender_id()
        key = (group_id, user_id)

        # 情况1：用户 @ 了机器人
        if self._is_at_bot(event):
            awaiting_image[key] = time.time()
            yield event.plain_result("📷 请发送图片，我将为你处理～")
            return

        # 情况2：用户发送了图片
        img_url = self._get_image_url(event)
        if img_url:
            now = time.time()
            if key in awaiting_image and (now - awaiting_image[key]) < 30:
                del awaiting_image[key]
                reply = f"✅ 收到你的图片啦！\n🔗 地址：{img_url}"
                yield event.plain_result(reply)
                return