import importlib
from typing import List, Dict


class LLMEngine:
    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        self.model_name = model_name
        self._ok = False
        self._loaded = False
        self._err: Exception | None = None
        self.pipe = None

    def _ensure_loaded(self) -> None:
        if self._loaded or self._err is not None:
            return
        try:
            transformers = importlib.import_module("transformers")
            AutoModelForCausalLM = transformers.AutoModelForCausalLM
            AutoTokenizer = transformers.AutoTokenizer
            pipeline = transformers.pipeline
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForCausalLM.from_pretrained(self.model_name)
            self.pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=180,
                do_sample=True,
                top_p=0.9,
                temperature=0.6,
            )
            self._ok = True
            self._loaded = True
        except Exception as e:
            # Do not block startup; keep fallback behavior
            self._err = e
            self._ok = False
            self._loaded = False

    def chat(self, messages: List[Dict[str, str]]) -> str:
        # Lazy load on first use
        self._ensure_loaded()
        if not (self._ok and self.pipe is not None):
            last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
            return ("Noted: " + last_user)[:120]
        prompt = ""
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                prompt += f"[System]: {content}\n"
            elif role == "assistant":
                prompt += f"[Assistant]: {content}\n"
            else:
                prompt += f"[User]: {content}\n"
        prompt += "[Assistant]:"
        result = self.pipe(prompt)[0]["generated_text"]
        if "[Assistant]:" in result:
            return result.split("[Assistant]:")[-1].strip()
        return result.strip()

    def summarize(self, transcript: str) -> str:
        messages = [
            {"role": "system", "content": "You are an assistant creating concise call summaries."},
            {"role": "user", "content": ("Summarize the call:\n\n" + transcript)},
        ]
        return self.chat(messages)


llm = LLMEngine()