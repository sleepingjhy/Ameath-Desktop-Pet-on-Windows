"""该模块负责应用设置持久化。统一读写用户偏好到本地 JSON 文件。"""
# EN: This module persists application settings by reading and writing user preferences to a local JSON file.

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import (
    APP_NAME,
    DISPLAY_MODE_ALWAYS_ON_TOP,
    DISPLAY_MODE_DESKTOP_ONLY,
    DISPLAY_MODE_FULLSCREEN_HIDE,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    OPACITY_DEFAULT_PERCENT,
    OPACITY_PERCENT_MAX,
    OPACITY_PERCENT_MIN,
    ROOT_DIR,
    SCALE_MAX,
    SCALE_MIN,
)
from .i18n import normalize_language
from .llm_providers import get_all_providers, get_provider


class SettingsStore:
    """应用设置存储。提供读取、更新和保存能力。"""
    """EN: App Settings Store. Provides read, update, and save capabilities."""

    def __init__(self):
        """初始化设置路径并加载已有配置。"""
        """EN: Initialize the setup path and load the existing configuration."""
        self.settings_path = self._build_settings_path()
        self.data: dict[str, Any] = {
            "close_behavior": "ask",
            "display_mode": DISPLAY_MODE_ALWAYS_ON_TOP,
            "instance_count": INSTANCE_COUNT_MIN,
            "opacity_percent": OPACITY_DEFAULT_PERCENT,
            "follow_mouse": False,
            "scale_factor": 1.0,
            "language": "zh-CN",
            "autostart_show_window": True,
        }
        self.project_config_path = Path(ROOT_DIR) / "config.yaml"
        # 本地密钥文件统一存到用户目录，确保 EXE 场景可写。
        # EN: Store local keys in user profile path to keep EXE scenario writable.
        self.local_config_path = self.settings_path.parent / "config_local.yaml"
        # 兼容旧位置（项目根目录）。仅用于迁移，不再作为默认写入路径。
        # EN: Legacy root path (project root), used only for migration.
        self.legacy_local_config_path = Path(ROOT_DIR) / "config_local.yaml"
        self._load()
        self._ensure_api_key_config_files()
        self._migrate_api_keys_to_local_config()
        self._sync_provider_api_keys_to_env()

    def _build_settings_path(self) -> Path:
        """构建设置文件路径。Windows 放在 AppData/Roaming 下。"""
        """EN: Constructs the path to the setup file. Windows is under AppData/Roaming."""
        appdata = os.getenv("APPDATA")
        if appdata:
            base_dir = Path(appdata) / APP_NAME
        else:
            base_dir = Path.home() / f".{APP_NAME.lower()}"

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "settings.json"

    def _load(self):
        """从磁盘加载设置。失败时使用默认值。"""
        """EN: Load settings from disk. Use default value on failure."""
        if not self.settings_path.exists():
            return

        try:
            loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            return

    def save(self):
        """将当前设置写回磁盘。"""
        """EN: Write the current settings back to disk."""
        self.settings_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _provider_ids(self) -> list[str]:
        """返回全部模型提供商ID。"""
        """EN: Returns all model provider IDs."""
        return [provider.id for provider in get_all_providers()]

    def _yaml_quote(self, value: str) -> str:
        """对 YAML 标量字符串进行最小转义。"""
        """EN: Minimal escaping for YAML scalar strings."""
        text = str(value or "")
        text = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{text}"'

    def _yaml_unquote(self, value: str) -> str:
        """解析简化 YAML 字符串值。"""
        """EN: Parse simplified YAML string value."""
        text = str(value or "").strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            text = text[1:-1]
        text = text.replace('\\"', '"').replace("\\\\", "\\")
        return text

    def _render_api_key_yaml(self, key_map: dict[str, str], hidden: bool) -> str:
        """渲染 API Key 配置为简化 YAML 文本。"""
        """EN: Render API key config to simplified YAML text."""
        lines = ["version: 1", "api_keys:"]
        for provider_id in self._provider_ids():
            if hidden:
                value = "<hidden: set in config_local.yaml>"
            else:
                value = str(key_map.get(provider_id, "") or "")
            lines.append(f"  {provider_id}: {self._yaml_quote(value)}")
        return "\n".join(lines) + "\n"

    def _parse_api_key_yaml(self, content: str) -> dict[str, str]:
        """解析简化 YAML 中的 api_keys 节点。"""
        """EN: Parse api_keys node from simplified YAML."""
        result: dict[str, str] = {}
        in_api_keys = False

        for raw_line in str(content or "").splitlines():
            line = raw_line.rstrip("\r\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("api_keys:"):
                in_api_keys = True
                continue

            if not in_api_keys:
                continue

            # 跳出 api_keys 缩进块。
            # EN: Exit api_keys indentation block.
            if not line.startswith("  "):
                break

            item = stripped
            if ":" not in item:
                continue

            provider_id, raw_value = item.split(":", 1)
            provider_id = str(provider_id).strip()
            value = self._yaml_unquote(raw_value)
            if provider_id:
                result[provider_id] = value

        return result

    def _load_api_keys_from_path(self, path: Path) -> dict[str, str]:
        """从指定 YAML 文件加载 API Key 映射。"""
        """EN: Load API key map from the specified YAML file."""
        if path is None or not Path(path).exists():
            return {}

        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError:
            return {}

        parsed = self._parse_api_key_yaml(content)
        return {k: str(v).strip() for k, v in parsed.items() if str(k).strip()}

    def _load_local_api_keys(self) -> dict[str, str]:
        """加载 config_local.yaml 中的 API Key 映射。"""
        """EN: Load API key map from config_local.yaml."""
        return self._load_api_keys_from_path(self.local_config_path)

    def _load_project_api_keys(self) -> dict[str, str]:
        """加载 config.yaml 中的 API Key 映射。"""
        """EN: Load API key map from config.yaml."""
        return self._load_api_keys_from_path(self.project_config_path)

    def _is_effective_api_key(self, value: str) -> bool:
        """判断字符串是否为可用 API Key（排除模板占位值）。"""
        """EN: Determine whether a string is an effective API key (exclude template placeholders)."""
        text = str(value or "").strip()
        if not text:
            return False

        lowered = text.lower()
        if lowered.startswith("<hidden:"):
            return False
        if lowered.startswith("your_") and lowered.endswith("_api_key"):
            return False
        return True

    def _save_local_api_keys(self, key_map: dict[str, str]):
        """保存 API Key 映射到 config_local.yaml。"""
        """EN: Save API key map to config_local.yaml."""
        normalized: dict[str, str] = {}
        for provider_id in self._provider_ids():
            normalized[provider_id] = str(key_map.get(provider_id, "") or "").strip()

        try:
            self.local_config_path.parent.mkdir(parents=True, exist_ok=True)
            self.local_config_path.write_text(
                self._render_api_key_yaml(normalized, hidden=False),
                encoding="utf-8",
            )
        except OSError:
            return

    def _ensure_api_key_config_files(self):
        """确保 config.yaml 与 config_local.yaml 存在。"""
        """EN: Ensure config.yaml and config_local.yaml exist."""
        default_keys = {provider_id: "" for provider_id in self._provider_ids()}

        if not self.project_config_path.exists():
            try:
                self.project_config_path.write_text(
                    self._render_api_key_yaml(default_keys, hidden=True),
                    encoding="utf-8",
                )
            except OSError:
                pass

        if not self.local_config_path.exists():
            try:
                self.local_config_path.write_text(
                    self._render_api_key_yaml(default_keys, hidden=False),
                    encoding="utf-8",
                )
            except OSError:
                pass

    def _migrate_api_keys_to_local_config(self):
        """将旧 settings.json 中的 API Key 迁移到 config_local.yaml。"""
        """EN: Migrate legacy API keys from settings.json to config_local.yaml."""
        local_keys = self._load_local_api_keys()
        legacy_local_keys = self._load_api_keys_from_path(self.legacy_local_config_path)
        project_keys = self._load_project_api_keys()
        local_changed = False
        settings_changed = False

        # 从旧版根目录 config_local.yaml 迁移到用户目录。
        # EN: Migrate keys from legacy root config_local.yaml to user path.
        for provider_id in self._provider_ids():
            local_value = str(local_keys.get(provider_id, "") or "").strip()
            legacy_value = str(legacy_local_keys.get(provider_id, "") or "").strip()
            if not self._is_effective_api_key(local_value) and self._is_effective_api_key(legacy_value):
                local_keys[provider_id] = legacy_value
                local_changed = True

        # 若本地缺失 deepseek 密钥，尝试从 config.yaml 回填。
        # EN: If deepseek key is missing in local config, backfill from config.yaml.
        local_deepseek = str(local_keys.get("deepseek", "") or "").strip()
        project_deepseek = str(project_keys.get("deepseek", "") or "").strip()
        if not self._is_effective_api_key(local_deepseek) and self._is_effective_api_key(project_deepseek):
            local_keys["deepseek"] = project_deepseek
            local_changed = True

        legacy_deepseek = str(self.data.get("api_key", "") or "").strip()
        if self._is_effective_api_key(legacy_deepseek) and not self._is_effective_api_key(local_keys.get("deepseek", "")):
            local_keys["deepseek"] = legacy_deepseek
            local_changed = True

        if "api_key" in self.data:
            self.data.pop("api_key", None)
            settings_changed = True

        for provider_id in self._provider_ids():
            storage_key = f"api_key_{provider_id}"
            legacy_value = str(self.data.get(storage_key, "") or "").strip()
            if self._is_effective_api_key(legacy_value) and not self._is_effective_api_key(local_keys.get(provider_id, "")):
                local_keys[provider_id] = legacy_value
                local_changed = True

            if storage_key in self.data:
                self.data.pop(storage_key, None)
                settings_changed = True

        if local_changed:
            self._save_local_api_keys(local_keys)

        if settings_changed:
            self.save()

    def _sync_provider_api_keys_to_env(self):
        """将本地 API Key 同步到进程环境变量。"""
        """EN: Sync local API keys to process environment variables."""
        for provider in get_all_providers():
            key = self.get_api_key_for_provider(provider.id)
            if key:
                os.environ[provider.api_key_env] = key
            else:
                os.environ.pop(provider.api_key_env, None)

    def get_close_behavior(self) -> str:
        """读取关闭行为配置。返回 ask、quit 或 tray。"""
        """EN: Read the close behavior configuration. Returns ask, quit, or tray."""
        value = self.data.get("close_behavior", "ask")
        if value in {"ask", "quit", "tray"}:
            return value
        return "ask"

    def set_close_behavior(self, behavior: str):
        """更新关闭行为配置并保存。"""
        """EN: Update the close behavior configuration and save."""
        if behavior not in {"ask", "quit", "tray"}:
            return
        self.data["close_behavior"] = behavior
        self.save()

    def get_display_mode(self) -> str:
        """读取显示模式配置。返回 always_on_top、fullscreen_hide 或 desktop_only。"""
        """EN: Read the display mode configuration. Returns always_on_top, fullscreen_hide, or desktop_only."""
        value = self.data.get("display_mode", DISPLAY_MODE_ALWAYS_ON_TOP)
        if value in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            return value
        return DISPLAY_MODE_ALWAYS_ON_TOP

    def set_display_mode(self, mode: str):
        """更新显示模式配置并保存。非法值自动回退到默认模式。"""
        """EN: Update the display mode configuration and save. Illegal value automatically falls back to default mode."""
        if mode not in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            mode = DISPLAY_MODE_ALWAYS_ON_TOP
        self.data["display_mode"] = mode
        self.save()

    def get_instance_count(self) -> int:
        """读取实例数量配置。返回范围限制在 1~50。"""
        """EN: Read the number of instances configuration. The return range is limited to 1 ~ 50."""
        value = self.data.get("instance_count", INSTANCE_COUNT_MIN)
        try:
            count = int(value)
        except (TypeError, ValueError):
            return INSTANCE_COUNT_MIN
        return max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, count))

    def set_instance_count(self, count: int):
        """更新实例数量配置并保存。保存前会裁剪到允许范围。"""
        """EN: Update the instance count configuration and save. Crop to allowed range before saving."""
        try:
            normalized = int(count)
        except (TypeError, ValueError):
            normalized = INSTANCE_COUNT_MIN
        normalized = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, normalized))
        self.data["instance_count"] = normalized
        self.save()

    def get_opacity_percent(self) -> int:
        """读取透明度配置。返回范围限制在 0~100。"""
        """EN: Read the transparency configuration. The return range is limited to 0 ~ 100."""
        value = self.data.get("opacity_percent", OPACITY_DEFAULT_PERCENT)
        try:
            percent = int(value)
        except (TypeError, ValueError):
            percent = OPACITY_DEFAULT_PERCENT
        return max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, percent))

    def set_opacity_percent(self, percent: int):
        """更新透明度配置并保存。保存前会裁剪到允许范围。"""
        """EN: Update the transparency configuration and save. Crop to allowed range before saving."""
        try:
            normalized = int(percent)
        except (TypeError, ValueError):
            normalized = OPACITY_DEFAULT_PERCENT
        normalized = max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, normalized))
        self.data["opacity_percent"] = normalized
        self.save()

    def get_follow_mouse(self) -> bool:
        """读取跟随鼠标配置。"""
        """EN: Reads the following mouse configuration."""
        return bool(self.data.get("follow_mouse", False))

    def set_follow_mouse(self, enabled: bool):
        """更新跟随鼠标配置并保存。"""
        """EN: Updates follow the mouse configuration and are saved."""
        self.data["follow_mouse"] = bool(enabled)
        self.save()

    def get_scale_factor(self) -> float:
        """读取缩放配置。返回范围限制在允许区间。"""
        """EN: Read the zoom configuration. The return range is limited to the allowed range."""
        value = self.data.get("scale_factor", 1.0)
        try:
            scale = float(value)
        except (TypeError, ValueError):
            scale = 1.0
        return max(SCALE_MIN, min(SCALE_MAX, scale))

    def set_scale_factor(self, scale: float):
        """更新缩放配置并保存。保存前会裁剪到允许范围。"""
        """EN: Update the zoom configuration and save. Crop to allowed range before saving."""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            normalized = 1.0
        normalized = max(SCALE_MIN, min(SCALE_MAX, normalized))
        self.data["scale_factor"] = normalized
        self.save()

    def get_language(self) -> str:
        """读取界面语言配置。"""
        """EN: Read interface language configuration."""
        return normalize_language(self.data.get("language", "zh-CN"))

    def set_language(self, language: str):
        """更新界面语言配置并保存。"""
        """EN: Update the interface language configuration and save."""
        self.data["language"] = normalize_language(language)
        self.save()

    def get_api_key(self) -> str:
        """读取 DeepSeek API Key。"""
        """EN: Read the DeepSeek API key."""
        return self.get_api_key_for_provider("deepseek")

    def set_api_key(self, api_key: str):
        """更新 DeepSeek API Key 并保存。"""
        """EN: Update DeepSeek API key and save."""
        self.set_api_key_for_provider("deepseek", api_key)

    def get_autostart_show_window(self) -> bool:
        """读取开机自启时是否显示窗口的配置。"""
        """EN: Read the configuration for showing window on autostart."""
        return bool(self.data.get("autostart_show_window", True))

    def set_autostart_show_window(self, enabled: bool):
        """更新开机自启时是否显示窗口的配置并保存。"""
        """EN: Update the configuration for showing window on autostart and save."""
        self.data["autostart_show_window"] = bool(enabled)
        self.save()

    # === 多模型配置存储 ===
    # EN: === Multi-model configuration storage ===

    def get_llm_provider(self) -> str:
        """获取当前选择的模型提供商ID，未设置返回空字符串。"""
        """EN: Get the currently selected model provider ID, returns empty string if not set."""
        value = self.data.get("llm_provider", "")
        return str(value) if value else ""

    def set_llm_provider(self, provider_id: str):
        """设置当前模型提供商。"""
        """EN: Set the current model provider."""
        self.data["llm_provider"] = str(provider_id)
        self.save()

    def get_llm_model(self, provider_id: str) -> str:
        """获取特定提供商的模型，未设置返回空字符串。"""
        """EN: Get the model for a specific provider, returns empty string if not set."""
        key = f"llm_model_{provider_id}"
        value = self.data.get(key, "")
        return str(value) if value else ""

    def set_llm_model(self, provider_id: str, model: str):
        """设置特定提供商的模型。"""
        """EN: Set the model for a specific provider."""
        key = f"llm_model_{provider_id}"
        self.data[key] = str(model)
        self.save()

    def get_api_key_for_provider(self, provider_id: str) -> str:
        """获取特定提供商的API密钥。"""
        """EN: Get the API key for a specific provider."""
        normalized_provider = str(provider_id or "").strip()
        if not normalized_provider:
            return ""

        # 优先读取本地私密配置。
        # EN: Prefer local secret config.
        local_keys = self._load_local_api_keys()
        local_value = str(local_keys.get(normalized_provider, "") or "").strip()
        if self._is_effective_api_key(local_value):
            return local_value

        # 本地缺失时回退读取项目配置。
        # EN: Fallback to project config when local key is missing.
        project_keys = self._load_project_api_keys()
        project_value = str(project_keys.get(normalized_provider, "") or "").strip()
        if self._is_effective_api_key(project_value):
            return project_value

        return ""

    def set_api_key_for_provider(self, provider_id: str, key: str):
        """设置特定提供商的API密钥。"""
        """EN: Set the API key for a specific provider."""
        normalized_provider = str(provider_id or "").strip()
        if not normalized_provider:
            return

        normalized_key = str(key or "").strip()
        local_keys = self._load_local_api_keys()
        local_keys[normalized_provider] = normalized_key
        self._save_local_api_keys(local_keys)

        storage_key = f"api_key_{normalized_provider}"
        changed = False
        if storage_key in self.data:
            self.data.pop(storage_key, None)
            changed = True
        if normalized_provider == "deepseek" and "api_key" in self.data:
            self.data.pop("api_key", None)
            changed = True
        if changed:
            self.save()

        provider = get_provider(normalized_provider)
        if provider is not None:
            if normalized_key:
                os.environ[provider.api_key_env] = normalized_key
            else:
                os.environ.pop(provider.api_key_env, None)

    def migrate_legacy_deepseek_key(self):
        """迁移旧版DeepSeek密钥到新格式。"""
        """EN: Migrate legacy DeepSeek key to new format."""
        self._migrate_api_keys_to_local_config()
        self._sync_provider_api_keys_to_env()
