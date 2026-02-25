import os
import json
import logging
import time
import streamlit as st
from openai import OpenAI

def get_api_key(key_name):
    try:
        return st.secrets[key_name]
    except Exception:
        return os.getenv(key_name)

client = OpenAI(api_key=get_api_key("OPENAI_API_KEY"))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self):
        self.client = __import__("openai").OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("DEFAULT_MODEL", "gpt-4o")

    def _call_llm(self, messages, temperature, max_tokens, response_format=None):
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if response.usage:
                    logger.debug("OpenAI usage: %s", response.usage)
                return content
            except Exception as e:
                logger.error("OpenAI API error attempt %s: %s", attempt + 1, e)
                if attempt < retry_attempts - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def complete(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._call_llm(messages, temperature, max_tokens)

    def complete_json(self, prompt: str, system_prompt: str = None) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        content = self._call_llm(messages, 0.0, 1000, {"type": "json_object"})
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from OpenAI: %s", e)
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1 and start < end:
                try:
                    return json.loads(content[start : end + 1])
                except Exception:
                    pass
            raise ValueError("Malformed JSON response from OpenAI.")

    def complete_with_functions(self, prompt: str, functions: list, system_prompt: str = None) -> dict:
        schema_str = json.dumps(functions, indent=2)
        combined = (system_prompt or "") + "\n\nReturn ONLY valid JSON matching this schema:\n" + schema_str
        return self.complete_json(prompt, system_prompt=combined)
