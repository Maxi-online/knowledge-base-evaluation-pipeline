"""Stateless request messages keep parallel jobs independent."""

import os
from openai import OpenAI
from .chat_interface import ChatInterface


class OpenAIChatBot(ChatInterface):
    def __init__(self):
        self.model = None
        self.system_message = ""
        self.client = None

    def init(self, config):
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENAI_API_KEY is required for live generation stages")
        self.model = config["model"]
        self.system_message = config.get("system_message", "")
        self.client = OpenAI(api_key=key, timeout=60, max_retries=2)

    def chat(self, message):
        if self.client is None:
            raise RuntimeError("The chat adapter has not been initialized")
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": message},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("The model returned no text")
        return content
