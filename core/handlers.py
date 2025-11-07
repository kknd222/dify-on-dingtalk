#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import json
import os
import hashlib
from typing import Callable

from dingtalk_stream import AckMessage, ChatbotHandler, CallbackHandler, CallbackMessage, ChatbotMessage, AICardReplier
from loguru import logger
from sseclient import SSEClient

from core.cache import Cache
from core.dify_client import ChatClient, DifyClient


class HandlerFactory(object):

    @staticmethod
    def create_handler(handler_type: str, **kwargs) -> CallbackHandler:
        if handler_type == "DifyAiCardBotHandler":
            return DifyAiCardBotHandler(**kwargs)
        else:
            raise ValueError(f"Unsupported handler type: {handler_type}")


class DifyAiCardBotHandler(ChatbotHandler):

    def __init__(self, dify_api_client: DifyClient):
        super().__init__()
        self.dify_api_client = dify_api_client
        self.cache = Cache(expiry_time=60 * int(os.getenv("DIFY_CONVERSATION_REMAIN_TIME")))  # 每个用户维持会话时间xx秒

    async def process(self, callback_msg: CallbackMessage):
        logger.debug(callback_msg)
        incoming_message = ChatbotMessage.from_dict(callback_msg.data)

        logger.info(f"收到用户消息：{incoming_message}")

        if incoming_message.message_type != "text":
            self.reply_text("对不起，我目前只看得懂文字喔~", incoming_message)
            return AckMessage.STATUS_OK, "OK"

        # 在企业开发者后台配置的卡片模版id https://open-dev.dingtalk.com/fe/card
        card_template_id = os.getenv("DINGTALK_AI_CARD_TEMPLATE_ID")
        content_key = "content"
        card_data = {content_key: ""}
        card_instance = AICardReplier(self.dingtalk_client, incoming_message)
        # 先投放卡片
        card_instance_id = card_instance.create_and_send_card(card_template_id, card_data, callback_type="STREAM")

        # 快速返回 ack，避免钉钉超时重试
        # 钉钉允许在返回 ack 后继续更新卡片
        import asyncio

        async def update_card():
            try:
                full_content_value = self._call_dify_with_stream(
                    incoming_message,
                    lambda content_value: card_instance.streaming(
                        card_instance_id,
                        content_key=content_key,
                        content_value=content_value,
                        append=False,   # 用全量覆盖的方式递增刷新；若想逐条追加可改 True
                        finished=False,
                        failed=False,
                    ),
                )
                card_instance.streaming(
                    card_instance_id,
                    content_key=content_key,
                    content_value=full_content_value,
                    append=False,
                    finished=True,
                    failed=False,
                )
            except Exception as e:
                logger.exception(e)
                card_instance.streaming(
                    card_instance_id,
                    content_key=content_key,
                    content_value=f"出现了异常: {e}",
                    append=False,
                    finished=False,
                    failed=True,
                )

        # 启动异步任务更新卡片
        asyncio.create_task(update_card())

        # 立即返回 ack
        return AckMessage.STATUS_OK, "OK"

    def _call_dify_with_stream(self, incoming_message: ChatbotMessage, callback: Callable[[str], None]):
        """
        核心增强点：
        - 继续支持 message / text_chunk 的增量；
        - 新增 agent_log( Final Answer ) 与 node_finished(agent) 的增量切片流式；
        - 通过 MD5 去重避免多次推送同样的 Final Answer。
        """
        def _split_chunks(s: str, size: int = 140):
            s = s or ""
            size = max(40, int(size or 140))
            return [s[i:i + size] for i in range(0, len(s), size)]

        chunk_size = int(os.getenv("DIFY_STREAM_CHUNK_SIZE", "140"))

        if incoming_message.message_type != "text":
            request_content = ""
        else:
            request_content = incoming_message.text.content

        conversation_id = self.cache.get(incoming_message.sender_staff_id)
        response = self.dify_api_client.query(
            inputs={"sys_user_id": incoming_message.sender_staff_id},
            query=request_content,
            user=incoming_message.sender_nick,
            response_mode="streaming",
            files=None,
            conversation_id=conversation_id,  # 需要考虑下怎么让一个用户的回话保持自己的上下文
        )
        if response.status_code != 200:
            raise Exception(f"调用模型服务失败，返回码：{response.status_code}，返回内容：{response.text}")

        sse_client = SSEClient(response)
        full_content = ""     # 我们对卡片采取“全量覆盖”的逐步刷新策略
        length = 0            # 发流频控（按累计长度差 > 10 再发）
        streamed_final = False
        final_hash = None     # 避免 agent_log 与 node_finished(agent) 重复推送

        for event in sse_client.events():
            # 兼容非 JSON 片段（比如心跳、DONE）
            try:
                r = json.loads(event.data)
            except Exception:
                logger.debug(f"收到无法解析的事件：{event.data}")
                continue

            logger.debug(f"接收到模型服务返回：{r}")
            evt = r.get("event")

            # --- 常规 message / agent_message（对话/Agent文本） ---
            if evt in ["message", "agent_message"]:
                # Dify: {"event": "message", "answer": "..."}
                delta = r.get("answer", "")
                if delta:
                    full_content += delta
                    full_content_length = len(full_content)
                    if full_content_length - length > 10:
                        callback(full_content)
                        logger.debug(
                            f'调用流式接口更新内容：message/agent_message, current_length={length}, next_length={full_content_length}'
                        )
                        length = full_content_length
                continue

            # --- 完成式模型 text_chunk（逐块 token） ---
            if evt in ["text_chunk"]:
                # Dify: {"event": "text_chunk", "data": {"text": "..."}}
                delta = (r.get("data") or {}).get("text", "")
                if delta:
                    full_content += delta
                    full_content_length = len(full_content)
                    if full_content_length - length > 10:
                        callback(full_content)
                        logger.debug(
                            f'调用流式接口更新内容：text_chunk, current_length={length}, next_length={full_content_length}'
                        )
                        length = full_content_length
                continue

            # --- 新增：Agent 推理日志（抓 Final Answer）---
            if evt == "agent_log":
                d = r.get("data") or {}
                status = d.get("status")
                dd = d.get("data") or {}
                action = dd.get("action") or dd.get("action_name")
                # 只在成功时抓 Final Answer
                if status == "success" and action == "Final Answer":
                    text = dd.get("action_input") or ""
                    if text:
                        h = hashlib.md5(text.encode("utf-8")).hexdigest()
                        if h != final_hash:
                            for ch in _split_chunks(text, size=chunk_size):
                                full_content += ch
                                callback(full_content)
                            streamed_final = True
                            final_hash = h
                            logger.debug("已按 agent_log.Final Answer 推送流式文本")
                continue

            # --- 新增：节点结束（兜底 Agent 输出）---
            if evt == "node_finished":
                data = r.get("data") or {}
                node_type = data.get("node_type")
                outputs = data.get("outputs") or {}
                # 有些策略把最终话术放这里
                if node_type == "agent":
                    text = outputs.get("text")
                    if text:
                        h = hashlib.md5(text.encode("utf-8")).hexdigest()
                        if h != final_hash:
                            for ch in _split_chunks(text, size=chunk_size):
                                full_content += ch
                                callback(full_content)
                            streamed_final = True
                            final_hash = h
                            logger.debug("已按 node_finished(agent).outputs.text 推送流式文本")
                # 其他节点忽略
                continue

            # --- Agent 思考/工具/文件事件：只记录日志 ---
            if evt in ["agent_thought", "message_file", "workflow_started", "workflow_finished",
                       "node_started", "parallel_branch_started", "parallel_branch_message",
                       "parallel_branch_finished"]:
                if evt == "message_file":
                    # 生成文件：可在此扩展卡片附件渲染
                    pass
                elif evt == "workflow_finished":
                    # 在主循环结束后会发送 finished=True；这里无需处理
                    pass
                else:
                    logger.debug(f"Ignoring event: {evt}")
                continue

            # --- 对话结束：记录会话ID，便于上下文保持 ---
            if evt == "message_end":
                # Dify: {'event':'message_end', 'conversation_id':'...', 'metadata':{...}}
                self.cache.set(incoming_message.sender_staff_id, r.get("conversation_id"))
                continue

            # 其它未知事件
            logger.debug(f"未知事件（忽略）：{evt}")

        logger.info(
            {
                "request_content": request_content,
                "full_response": full_content,
                "full_response_length": len(full_content),
            }
        )
        return full_content
