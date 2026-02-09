"""LLM client abstraction — supports Anthropic and OpenAI APIs."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified interface for calling Anthropic or OpenAI."""

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model

        if self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        elif self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'.")

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a prompt and return the text response."""
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.content[0].text

        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content

        raise ValueError(f"Unknown provider: {self.provider}")


def create_llm_client(config: dict) -> LLMClient:
    """Create an LLM client from the llm section of config.yaml.

    Supports both the new 'llm' config format and the legacy 'anthropic' format.
    """
    # New format: config["llm"]
    if "llm" in config:
        llm = config["llm"]
        return LLMClient(
            provider=llm["provider"],
            api_key=llm["api_key"],
            model=llm["model"],
        )

    # Legacy format: config["anthropic"]
    if "anthropic" in config:
        ant = config["anthropic"]
        return LLMClient(
            provider="anthropic",
            api_key=ant["api_key"],
            model=ant.get("model", "claude-sonnet-4-5-20250929"),
        )

    raise ValueError("No LLM configuration found. Add 'llm' or 'anthropic' section to config.yaml.")
