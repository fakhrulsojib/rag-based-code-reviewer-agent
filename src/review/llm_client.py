"""LLM client with provider abstraction."""
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import settings
from src.logger import logger


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""
    
    def __init__(self):
        """Initialize Gemini provider."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config={
                "temperature": settings.gemini_temperature,
                "max_output_tokens": settings.gemini_max_tokens,
                "response_mime_type": "application/json",
            }
        )
        logger.info(f"Initialized Gemini provider with model: {settings.gemini_model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(self, prompt: str) -> str:
        """Generate a response from Gemini.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            logger.info("="*80)
            logger.info("FULL PROMPT:")
            logger.info(prompt)
            logger.info("="*80)
            response = self.model.generate_content(prompt)
            logger.info(f"Received response from Gemini (length: {len(response.text)} chars)")
            logger.info("FULL RESPONSE:")
            logger.info(response.text)
            
            if response.prompt_feedback:
                logger.info(f"Prompt Feedback: {response.prompt_feedback}")
                
            return response.text
        except Exception as e:
            logger.error(f"Error generating from Gemini: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider (fallback)."""
    
    def __init__(self):
        """Initialize OpenAI provider."""
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("Initialized OpenAI provider")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(self, prompt: str) -> str:
        """Generate a response from OpenAI.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.gemini_temperature,
                max_tokens=settings.gemini_max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating from OpenAI: {e}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider (fallback)."""
    
    def __init__(self):
        """Initialize Anthropic provider."""
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        logger.info("Initialized Anthropic provider")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(self, prompt: str) -> str:
        """Generate a response from Claude.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=settings.gemini_max_tokens,
                temperature=settings.gemini_temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error generating from Anthropic: {e}")
            raise


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self):
        """Initialize Ollama provider."""
        import ollama
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.model = settings.ollama_model
        logger.info(f"Initialized Ollama provider with model: {settings.ollama_model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(self, prompt: str) -> str:
        """Generate a response from Ollama.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            # Run sync chat in thread pool
            import asyncio
            import json
            response = await asyncio.to_thread(
                self.client.chat,
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error generating from Ollama: {e}")
            raise


class LLMClient:
    """Main LLM client with provider abstraction."""
    
    def __init__(self):
        """Initialize LLM client with configured provider."""
        self.provider = self._create_provider()
        logger.info(f"Initialized LLM client with provider: {settings.llm_provider}")
    
    def _create_provider(self) -> LLMProvider:
        """Create the appropriate LLM provider.
        
        Returns:
            LLMProvider instance
        """
        if settings.llm_provider == "gemini":
            return GeminiProvider()
        elif settings.llm_provider == "openai":
            return OpenAIProvider()
        elif settings.llm_provider == "anthropic":
            return AnthropicProvider()
        elif settings.llm_provider == "ollama":
            return OllamaProvider()
        else:
            logger.warning(f"Unknown provider {settings.llm_provider}, defaulting to Ollama")
            return OllamaProvider()
    
    async def generate_review(self, prompt: str) -> str:
        """Generate a code review response.
        
        Args:
            prompt: Review prompt
            
        Returns:
            Generated review response
        """
        logger.info("Generating review with LLM")
        
        try:
            response = await self.provider.generate(prompt)
            logger.info("FULL RESPONSE:")
            logger.info(response)
            logger.info(f"Generated review response ({len(response)} chars)")
            return response
        except Exception as e:
            logger.error(f"Error generating review: {e}")
            raise
    
    async def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = None
    ) -> str:
        """Generate with custom retry logic.
        
        Args:
            prompt: Input prompt
            max_retries: Maximum number of retries
            
        Returns:
            Generated response
        """
        max_retries = max_retries or settings.max_retries
        
        for attempt in range(max_retries):
            try:
                return await self.generate_review(prompt)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Retry {attempt + 1}/{max_retries} after error: {e}")
                await asyncio.sleep(settings.retry_delay * (attempt + 1))
        
        raise Exception("Max retries exceeded")
