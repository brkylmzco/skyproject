from __future__ import annotations

import json
import os
import asyncio
from typing import Any, Optional, Callable, Coroutine

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
from dotenv import load_dotenv
from skyproject.shared.logging_utils import log_error, log_warning, log_info, ErrorCode

load_dotenv()


class LLMClientError(Exception):
    """Base class for exceptions in this module."""


class UnknownProviderError(LLMClientError):
    """Exception raised for using an unknown provider."""
    def __init__(self, provider: str):
        self.provider = provider
        self.message = f"Unknown provider: {provider}"
        super().__init__(self.message)


class LLMClient:
    """Unified LLM client for both PM AI and IrgatAI."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None

    def _get_openai_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client

    def _get_anthropic_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a response from the LLM with enhanced context."""
        try:
            if self.provider == "openai":
                return await self._generate_with_retries(self._generate_openai, system_prompt, user_prompt, response_format)
            elif self.provider == "anthropic":
                return await self._generate_with_retries(self._generate_anthropic, system_prompt, user_prompt)
            else:
                raise UnknownProviderError(self.provider)
        except LLMClientError as e:
            log_error(ErrorCode.UNKNOWN_PROVIDER, f"Error generating response: {str(e)}")
            raise
        except Exception as e:
            log_error(ErrorCode.OPENAI_GENERATION_ERROR if self.provider == 'openai' else ErrorCode.ANTHROPIC_GENERATION_ERROR, f"Error generating response: {str(e)}")
            raise

    async def _generate_openai(
        self, system_prompt: str, user_prompt: str, response_format: Optional[str] = None
    ) -> str:
        client = self._get_openai_client()

        enhanced_system_prompt = f"You are a sophisticated AI assistant. {system_prompt}"
        enhanced_user_prompt = f"Provide a clear and concise response to the following: {user_prompt}"

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": enhanced_user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await asyncio.to_thread(client.chat.completions.create, **kwargs)
            return response.choices[0].message.content or ""
        except ConnectionError as e:
            log_error(ErrorCode.NETWORK_ERROR, f"Network error in OpenAI generation: {str(e)}")
            raise
        except HTTPError as e:
            log_error(ErrorCode.HTTP_ERROR, f"HTTP error in OpenAI generation: {str(e)}")
            raise
        except Timeout as e:
            log_error(ErrorCode.TIMEOUT_ERROR, f"Timeout error in OpenAI generation: {str(e)}")
            raise
        except RequestException as e:
            log_error(ErrorCode.REQUEST_EXCEPTION, f"Request error in OpenAI generation: {str(e)}")
            raise
        except Exception as e:
            log_error(ErrorCode.OPENAI_GENERATION_ERROR, f"Unexpected error in OpenAI generation: {str(e)}")
            raise

    async def _generate_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_anthropic_client()

        enhanced_system_prompt = f"You are a sophisticated AI assistant. {system_prompt}"
        enhanced_user_prompt = f"Provide a clear and concise response to the following: {user_prompt}"

        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=self.model,
                max_tokens=self.max_tokens,
                system=enhanced_system_prompt,
                messages=[{"role": "user", "content": enhanced_user_prompt}],
                temperature=self.temperature,
            )
            return response.content[0].text
        except ConnectionError as e:
            log_error(ErrorCode.NETWORK_ERROR, f"Network error in Anthropic generation: {str(e)}")
            raise
        except HTTPError as e:
            log_error(ErrorCode.HTTP_ERROR, f"HTTP error in Anthropic generation: {str(e)}")
            raise
        except Timeout as e:
            log_error(ErrorCode.TIMEOUT_ERROR, f"Timeout error in Anthropic generation: {str(e)}")
            raise
        except RequestException as e:
            log_error(ErrorCode.REQUEST_EXCEPTION, f"Request error in Anthropic generation: {str(e)}")
            raise
        except Exception as e:
            log_error(ErrorCode.ANTHROPIC_GENERATION_ERROR, f"Unexpected error in Anthropic generation: {str(e)}")
            raise

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Generate and parse a JSON response."""
        try:
            if self.provider == "openai":
                raw = await self.generate(system_prompt, user_prompt, response_format="json")
            else:
                raw = await self.generate(
                    system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation.",
                    user_prompt,
                )

            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1])

            return json.loads(raw)
        except json.JSONDecodeError as e:
            log_error(ErrorCode.JSON_DECODE_ERROR, f"Failed to decode JSON response: {str(e)}")
            raise
        except Exception as e:
            log_error(ErrorCode.OPENAI_GENERATION_ERROR if self.provider == 'openai' else ErrorCode.ANTHROPIC_GENERATION_ERROR, f"Error generating JSON response: {str(e)}")
            raise

    async def _generate_with_retries(self, func: Callable[..., Coroutine[Any, Any, str]], *args, **kwargs) -> str:
        """Retries a function call with exponential backoff."""
        attempt = 0
        while attempt < self.max_retries:
            try:
                return await func(*args, **kwargs)
            except (ConnectionError, Timeout, RequestException) as e:
                attempt += 1
                log_warning(f"Attempt {attempt}/{self.max_retries} failed due to network issue: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                else:
                    log_error(ErrorCode.MAX_RETRIES_REACHED, f"Max retries reached due to network issue. Failing with error: {str(e)}")
                    raise
            except Exception as e:
                log_warning(f"Attempt {attempt}/{self.max_retries} failed with error: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                else:
                    log_error(ErrorCode.MAX_RETRIES_REACHED, f"Max retries reached. Failing with error: {str(e)}")
                    raise
