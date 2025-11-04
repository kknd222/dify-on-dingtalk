#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import unittest
from unittest.mock import patch
from core.dify_client import ChatClient, ChatflowClient


class TestChatClient(unittest.TestCase):

    def setUp(self):
        self.chat_client = ChatClient(api_key="app-r7P5q2Dl3opvJFewFD1OD7D9", base_url="http://192.168.250.64/v1")

    @patch("core.dify_client.ChatClient._send_request")
    def test_create_chat_message_blocking(self, mock_send_request):
        # 测试 blocking 模式
        inputs = {}
        query = "你好，介绍一下你自己吧。"
        user = "user"
        response_mode = "blocking"
        conversation_id = "conv_id"
        files = None

        self.chat_client.create_chat_messages(inputs, query, user, response_mode, conversation_id, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chat-messages",
            {
                "inputs": inputs,
                "query": query,
                "user": user,
                "response_mode": response_mode,
                "conversation_id": conversation_id,
                "files": files,
                "auto_generate_name": False,
            },
            stream=False,
        )

    @patch("core.dify_client.ChatClient._send_request")
    def test_create_chat_message_streaming(self, mock_send_request):
        # 测试 streaming 模式
        inputs = {}
        query = "你好，介绍一下你自己吧。"
        user = "user"
        response_mode = "streaming"
        conversation_id = None
        files = None

        self.chat_client.create_chat_messages(inputs, query, user, response_mode, conversation_id, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chat-messages",
            {"inputs": inputs, "query": query, "user": user, "response_mode": response_mode, "files": files, "auto_generate_name": False},
            stream=True,
        )

    # 可以添加更多的测试用例来覆盖不同的场景和参数组合


class TestChatflowClient(unittest.TestCase):

    def setUp(self):
        self.chatflow_client = ChatflowClient(api_key="test_api_key", base_url="http://example.com/v1")

    @patch("core.dify_client.ChatflowClient._send_request")
    def test_run_blocking(self, mock_send_request):
        inputs = {}
        query = "test query"
        user = "test_user"
        response_mode = "blocking"
        files = None

        self.chatflow_client.query(inputs, query, user, response_mode, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chatflows/run",
            {
                "inputs": {"query": query},
                "user": user,
                "response_mode": response_mode,
                "files": files,
            },
            stream=False,
        )

    @patch("core.dify_client.ChatflowClient._send_request")
    def test_run_streaming(self, mock_send_request):
        inputs = {}
        query = "test query"
        user = "test_user"
        response_mode = "streaming"
        files = None

        self.chatflow_client.query(inputs, query, user, response_mode, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chatflows/run",
            {"inputs": {"query": query}, "user": user, "response_mode": response_mode, "files": files},
            stream=True,
        )


if __name__ == "__main__":
    unittest.main()
