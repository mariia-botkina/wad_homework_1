import asyncio
from typing import Optional
from app.config import settings

class LLMService:
    def __init__(self):
        self._model = None
        self._initialized = False
    
    def _load_model(self):
        if self._initialized:
            return
        self._initialized = True
        if not settings.LLM_MODEL_PATH:
            return
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=settings.LLM_MODEL_PATH,
                n_ctx=2048,
                n_threads=4,
                verbose=False,
            )
        except Exception as e:
            print(f"Could not load LLM model: {e}")
    
    async def generate(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, prompt)
    
    def _generate_sync(self, prompt: str) -> str:
        self._load_model()
        if self._model is None:
            return self._mock_response(prompt)
        try:
            result = self._model(
                f"Human: {prompt}\nAssistant:",
                max_tokens=512,
                stop=["Human:", "\n\n"],
                stream=False,
            )
            return result["choices"][0]["text"].strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _mock_response(self, prompt: str) -> str:
        return (
            f"I received your message: \"{prompt}\". "
            "Note: No LLM model is currently loaded. "
            "To enable AI responses, set LLM_MODEL_PATH in your .env file to point to a GGUF model file."
        )

llm_service = LLMService()
