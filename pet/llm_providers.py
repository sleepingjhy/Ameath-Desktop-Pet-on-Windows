"""该模块定义支持的AI模型提供商和模型配置。"""
"""EN: This module defines supported AI model providers and model configurations."""

from dataclasses import dataclass


@dataclass
class LLMModel:
    """单个模型配置。"""
    """EN: Single model configuration."""
    id: str                    # 模型ID
    name: str                  # 显示名称
    supports_vision: bool      # 是否支持视觉


@dataclass
class LLMProvider:
    """模型提供商配置。"""
    """EN: Model provider configuration."""
    id: str                    # 唯一标识
    name: str                  # 显示名称
    base_url: str              # API端点
    default_model: str         # 默认模型ID
    models: list[LLMModel]     # 可用模型列表
    api_key_env: str           # 环境变量名
    api_key_hint: str          # 获取密钥提示链接

    @property
    def supports_vision(self) -> bool:
        """当前默认模型是否支持视觉。"""
        """EN: Whether the current default model supports vision."""
        for m in self.models:
            if m.id == self.default_model:
                return m.supports_vision
        return False

    def get_model(self, model_id: str) -> LLMModel | None:
        """获取指定模型配置。"""
        """EN: Get the specified model configuration."""
        for m in self.models:
            if m.id == model_id:
                return m
        return None


# 预定义所有支持的模型（2026年3月最新）
# EN: Predefined all supported models (March 2026 latest)
PROVIDERS: dict[str, LLMProvider] = {
    "openai": LLMProvider(
        id="openai", name="ChatGPT",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5.4",
        models=[
            LLMModel("gpt-5.4", "GPT-5.4 (推荐)", True),
            LLMModel("gpt-5.4-pro", "GPT-5.4 Pro", True),
            LLMModel("o3", "o3", True),
            LLMModel("o4-mini", "o4-mini", True),
            LLMModel("gpt-4o", "GPT-4o", True),
        ],
        api_key_env="OPENAI_API_KEY",
        api_key_hint="https://platform.openai.com/api-keys"
    ),
    "gemini": LLMProvider(
        id="gemini", name="Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-3.1-flash",
        models=[
            LLMModel("gemini-3.1-flash", "Gemini 3.1 Flash (推荐)", True),
            LLMModel("gemini-3.1-pro", "Gemini 3.1 Pro", True),
            LLMModel("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite", True),
            LLMModel("gemini-2.5-flash", "Gemini 2.5 Flash", True),
        ],
        api_key_env="GEMINI_API_KEY",
        api_key_hint="https://aistudio.google.com/apikey"
    ),
    "claude": LLMProvider(
        id="claude", name="Claude",
        base_url="https://api.anthropic.com/v1",
        default_model="claude-sonnet-4-6-20260217",
        models=[
            LLMModel("claude-sonnet-4-6-20260217", "Claude Sonnet 4.6 (推荐)", True),
            LLMModel("claude-opus-4-6-20260217", "Claude Opus 4.6", True),
            LLMModel("claude-sonnet-4-20250514", "Claude Sonnet 4", True),
        ],
        api_key_env="CLAUDE_API_KEY",
        api_key_hint="https://console.anthropic.com/"
    ),
    "grok": LLMProvider(
        id="grok", name="Grok",
        base_url="https://api.x.ai/v1",
        default_model="grok-4",
        models=[
            LLMModel("grok-4", "Grok 4 (推荐)", True),
            LLMModel("grok-4-20-beta", "Grok 4.20 Beta", True),
            LLMModel("grok-2-vision-1212", "Grok 2 Vision", True),
            LLMModel("grok-2-1212", "Grok 2", False),
        ],
        api_key_env="GROK_API_KEY",
        api_key_hint="https://console.x.ai/"
    ),
    "qwen": LLMProvider(
        id="qwen", name="通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen3-vl",
        models=[
            LLMModel("qwen3-vl", "Qwen3-VL 视觉版 (推荐)", True),
            LLMModel("qwen3-max", "Qwen3-Max", False),
            LLMModel("qwen3-235b-a22b", "Qwen3-235B", False),
            LLMModel("qwen-vl-plus", "Qwen-VL-Plus", True),
        ],
        api_key_env="QWEN_API_KEY",
        api_key_hint="https://bailian.console.aliyun.com/"
    ),
    "doubao": LLMProvider(
        id="doubao", name="豆包",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model="seed-2.0-pro",
        models=[
            LLMModel("seed-2.0-pro", "Seed 2.0 Pro (推荐)", True),
            LLMModel("seed-2.0-lite", "Seed 2.0 Lite", True),
            LLMModel("seed-2.0-mini", "Seed 2.0 Mini", True),
            LLMModel("doubao-pro-32k", "Doubao Pro 32K", False),
        ],
        api_key_env="DOUBAO_API_KEY",
        api_key_hint="https://console.volcengine.com/ark"
    ),
    "glm": LLMProvider(
        id="glm", name="智谱GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4.5v",
        models=[
            LLMModel("glm-5", "GLM-5 (最新)", False),
            LLMModel("glm-4.5v", "GLM-4.5V 视觉版 (推荐)", True),
            LLMModel("glm-4.6", "GLM-4.6", False),
            LLMModel("glm-4-flash", "GLM-4 Flash", False),
        ],
        api_key_env="GLM_API_KEY",
        api_key_hint="https://open.bigmodel.cn/"
    ),
    "minimax": LLMProvider(
        id="minimax", name="Minimax",
        base_url="https://api.minimax.chat/v1",
        default_model="abab7-preview",
        models=[
            LLMModel("abab7-preview", "abab7-preview (推荐)", False),
            LLMModel("abab6.5s-chat", "abab6.5s-chat", False),
        ],
        api_key_env="MINIMAX_API_KEY",
        api_key_hint="https://platform.minimax.io/"
    ),
    "kimi": LLMProvider(
        id="kimi", name="Kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2.5",
        models=[
            LLMModel("kimi-k2.5", "Kimi K2.5 (推荐)", True),
            LLMModel("moonshot-v1-8k", "Moonshot V1 8K", False),
        ],
        api_key_env="KIMI_API_KEY",
        api_key_hint="https://platform.moonshot.cn/"
    ),
    "deepseek": LLMProvider(
        id="deepseek", name="DeepSeek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        models=[
            LLMModel("deepseek-chat", "DeepSeek V3.2 (推荐)", False),
            LLMModel("deepseek-coder", "DeepSeek Coder", False),
        ],
        api_key_env="DEEPSEEK_API_KEY",
        api_key_hint="https://platform.deepseek.com/"
    ),
}


def get_provider(provider_id: str) -> LLMProvider | None:
    """获取指定提供商配置。"""
    """EN: Get the specified provider configuration."""
    return PROVIDERS.get(provider_id)


def get_all_providers() -> list[LLMProvider]:
    """获取所有提供商列表。"""
    """EN: Get all providers list."""
    return list(PROVIDERS.values())
