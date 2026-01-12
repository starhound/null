from typing import Any

from pydantic import BaseModel, Field, ValidationError


class TerminalConfig(BaseModel):
    theme: str = Field(default="null-dark", description="UI theme")
    font_size: int = Field(default=12, ge=8, le=32, description="Font size")
    cursor_blink: bool = Field(default=True, description="Enable cursor blinking")
    cursor_style: str = Field(default="block", pattern="^(block|beam|underline)$")


class AIConfig(BaseModel):
    default_model: str = Field(default="gpt-4", description="Default LLM model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    agent_mode: bool = Field(default=False)


class NullConfig(BaseModel):
    terminal: TerminalConfig = Field(default_factory=TerminalConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    @classmethod
    def validate_config(cls, data: dict[str, Any]) -> "NullConfig":
        try:
            return cls.model_validate(data)
        except ValidationError:
            # Return default config on critical failures, but log error
            # In a real implementation, we'd log this
            return cls()
