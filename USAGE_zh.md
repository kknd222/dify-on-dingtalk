# Dify-Dingtalk 集成中文使用说明

## 概述

本项目旨在将强大的 Dify AI 应用与钉钉（Dingtalk）机器人相结合，让您可以在钉钉中直接与 Dify 应用进行交互。

此集成支持文本和图片消息的输入与输出，您可以：
- 在钉钉中向机器人发送文本或图片。
- 机器人会将消息发送到 Dify 应用进行处理。
- Dify 应用返回的文本或图片结果将由机器人发送回钉钉。

## 功能特性

- **文本交互**：支持与 Dify 的聊天机器人（Chatbot）、完成应用（Completion）和工作流（Workflow）进行文本对话。
- **图片输入**：您可以将图片发送给机器人，Dify 应用可以接收并处理这些图片（例如，进行图片内容识别）。
- **图片输出**：如果 Dify 应用返回的是图片（例如，生成图表、图像），机器人会自动将其发送到钉钉聊天中。
- **上下文保持**：在设定的时间内，机器人能够记住之前的对话内容，实现连续对话。

## 配置与使用

### 1. Dify 应用配置

您需要在 Dify 平台创建一个应用，并获取其 API 密钥。

- **支持的应用类型**：`chatbot`, `completion`, `workflow`。
- **获取 API 密钥**：在 Dify 应用的“API 访问”页面，您可以找到所需的 API 密钥。

### 2. 钉钉机器人配置

您需要在钉钉开放平台创建一个机器人，并获取其 `Client ID` 和 `Client Secret`。

- **创建机器人**：请参考钉钉官方文档，创建一个机器人应用。
- **添加机器人能力**：为您的应用添加“机器人”能力。
- **消息接收模式**：请选择 `Stream` 模式。
- **配置API权限（重要）**：为了支持图片消息，您必须为机器人的应用添加以下两个API权限：
  - `robot.file.download`：机器人文件下载权限（用于接收用户发送的图片）。
  - `robot.media.upload`：机器人上传文件权限（用于发送图片给用户）。
  请在钉钉开放平台的 **权限管理** 页面确保这两个权限已被添加。

### 3. 项目配置

将本项目代码下载到您的服务器后，您需要配置以下环境变量：

- `DIFY_OPEN_API_URL`: 您的 Dify API 地址，例如 `https://api.dify.ai/v1`。
- `LOG_LEVEL`: 日志级别，例如 `INFO`。
- `DINGTALK_AI_CARD_TEMPLATE_ID`: 钉钉的 AI 卡片模板 ID（可选）。
- `DIFY_CONVERSATION_REMAIN_TIME`: 对话上下文保持时间（分钟）。

此外，您需要创建一个 `.bots.yaml` 文件，用于配置一个或多个机器人。您可以参考 `.bots.yaml.example` 文件进行创建：

```yaml
bots:
  - name: "我的 Dify 机器人"
    dingtalk_app_client_id: "ding_client_id"
    dingtalk_app_client_secret: "ding_client_secret"
    dify_app_type: "chatbot" # 可选值: chatbot, completion, workflow
    dify_app_api_key: "dify_api_key"
    handler: "DifyAiCardBotHandler"
```

### 4. 运行项目

配置完成后，运行以下命令启动项目：

```bash
python app.py
```

## 如何使用

### 发送文本消息

在钉钉中，像与普通用户聊天一样，直接向机器人发送文本消息即可。

### 发送图片（图片输入）

在钉钉聊天中，直接选择并发送图片给机器人。机器人会自动将图片上传到 Dify 进行处理。

### 接收图片（图片输出）

如果 Dify 应用的处理结果是图片，机器人会自动将图片发送到钉钉聊天中，您无需进行任何额外操作。

## 常见问题解答

**Q: 为什么机器人没有回复我？**

**A:** 请检查以下几点：
1.  您的 `app.py` 服务是否正常运行。
2.  `.bots.yaml` 文件中的 `Client ID`, `Client Secret`, 和 `API Key` 是否配置正确。
3.  您的 Dify 应用是否已发布并可正常访问。

**Q: 机器人回复“对不起，我目前只看得懂文字喔~”**

**A:** 这个提示表明机器人收到了它无法处理的消息类型。目前项目仅支持文本和图片，请确认您发送的是否是这两种类型之一。

**Q: 如何让机器人拥有长期记忆？**

**A:** 您可以调整 `DIFY_CONVERSATION_REMAIN_TIME` 环境变量的值，以延长机器人的上下文保持时间。

---

如果您有任何其他问题，欢迎提出。
