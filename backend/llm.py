import os
from typing import Any, Dict, List, Tuple

import httpx

from .prompts import SYSTEM_PROMPT


class GymLLM:
    def __init__(self, provider: str, model: str, api_key: str = ""):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key

        if provider == "openai":
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        elif provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
        elif provider == "groq":
            from groq import Groq

            self.client = Groq(api_key=api_key)
        elif provider == "ollama":
            self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        else:
            raise ValueError(f"Noma'lum provider: {provider}")

    def generate(
        self, history: List[Dict[str, str]], user_msg: str
    ) -> Tuple[str, Dict[str, Any]]:
        if self.provider == "ollama":
            return self._generate_ollama(history, user_msg)
        elif self.provider == "gemini":
            return self._generate_gemini(history, user_msg)
        elif self.provider == "groq":
            return self._generate_groq(history, user_msg)
        else:  # openai
            return self._generate_openai(history, user_msg)

    def _generate_ollama(self, history, user_msg):
        messages = self.build_messages(history, user_msg)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.4, "top_p": 0.9, "max_tokens": 600},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                answer = data["message"]["content"]
                return answer, {"usage": data.get("usage", {}), "model": self.model}
        except Exception as e:
            return f"Ollama xatosi: {e}", {"error": str(e)}

    def _generate_gemini(self, history, user_msg):
        # Gemini uchun conversation history
        chat_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})

        try:
            chat = self.client.start_chat(history=chat_history)
            # System promptni user message bilan birlashtirish
            full_prompt = f"{SYSTEM_PROMPT}\n\nFoydalanuvchi: {user_msg}"
            response = chat.send_message(full_prompt)
            return response.text, {"model": self.model, "usage": {}}
        except Exception as e:
            return f"Gemini xatosi: {e}", {"error": str(e)}

    def _generate_groq(self, history, user_msg):
        messages = self.build_messages(history, user_msg)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.4,
                max_tokens=600,
                top_p=0.9,
            )
            answer = resp.choices[0].message.content
            return answer, {"usage": resp.usage.__dict__, "model": self.model}
        except Exception as e:
            return f"Groq xatosi: {e}", {"error": str(e)}

    def _generate_openai(self, history, user_msg):
        messages = self.build_messages(history, user_msg)
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.4, max_tokens=600
        )
        answer = resp.choices[0].message.content
        return answer, {"usage": resp.usage.__dict__, "model": self.model}

    def build_messages(self, history, user_msg):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history:
            messages.append(item)
        messages.append({"role": "user", "content": user_msg})
        return messages
