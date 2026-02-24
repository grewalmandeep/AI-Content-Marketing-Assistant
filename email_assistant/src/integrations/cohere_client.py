import os
import json
import logging
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class CohereClient:
    def __init__(self):
        cohere = __import__("cohere")
        self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
        self.model = "command-r"

    def _call_llm(self, messages, temperature, max_tokens):
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                system = ""
                rest = []
                for m in messages:
                    if m.get("role") == "system":
                        system = m.get("content", "")
                    else:
                        rest.append(m)
                if system and rest:
                    rest[0] = {"role": rest[0]["role"], "content": system + "\n\n" + rest[0].get("content", "")}
                if not rest:
                    rest = [{"role": "user", "content": system or "Respond with JSON."}]
                history = [{"role": "USER" if x["role"] == "user" else "CHATBOT", "message": x["content"]} for x in rest[:-1]]
                message = rest[-1]["content"]
                response = self.client.chat(
                    model=self.model,
                    chat_history=history,
                    message=message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.text
            except Exception as e:
                logger.error("Cohere API error attempt %s: %s", attempt + 1, e)
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
        sys = (system_prompt or "") + "\n\nReturn ONLY a valid JSON object, no other text."
        content = self.complete(prompt, system_prompt=sys, temperature=0.0, max_tokens=1000)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1 and start < end:
                try:
                    return json.loads(content[start : end + 1])
                except Exception:
                    pass
            raise ValueError("Malformed JSON response from Cohere.")
