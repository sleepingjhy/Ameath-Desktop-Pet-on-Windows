"""聊天 Agent API 适配层。"""

from __future__ import annotations

import base64
import os
import re
import warnings
from pathlib import Path

from pet.config import ROOT_DIR
from pet.llm_providers import get_provider, LLMProvider
from pet.search import SearchRetriever, build_search_context

try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - 新包未安装时回退旧包
    try:
        from duckduckgo_search import DDGS
    except ImportError:  # pragma: no cover - 运行环境未安装时降级
        DDGS = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - 运行环境未安装时降级
    OpenAI = None

# 图片大小限制常量
# EN: Image size limit constants
MAX_SINGLE_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB


class ChatAgentApi:
    """桌宠聊天 API 客户端。"""

    _SEED_TERMS = ("鸣潮", "爱弥斯", "设定", "背景")
    _ROLE_HINT_TERMS = {
        "爱弥斯",
        "鸣潮",
        "角色",
        "人设",
        "设定",
        "背景",
        "世界观",
        "身份",
        "经历",
        "关系",
        "性格",
        "故事",
        "档案",
        "传记",
        "台词",
        "喜好",
        "能力",
        "技能",
    }
    _TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,}")

    _SYSTEM_PROMPT = (
        "你是爱弥斯。请使用温柔、自然、简洁的中文对话。"
        "请优先依据给出的本地资料与联网搜索结果回答角色设定相关问题；"
        "若检索结果不足或不确定，请明确说明不确定。"
    )

    _DDG_RENAME_WARNING_PATTERN = r".*duckduckgo_search.*renamed to `ddgs`.*"
    _TIMELY_KEYWORDS = ("最新", "最近", "今天", "本周", "本月", "更新", "版本", "公告")
    _LOCAL_CONTEXT_MAX_CHARS = 1200
    _ONLINE_CONTEXT_MAX_CHARS = 1200
    _HISTORY_CONTEXT_MAX_CHARS = 800

    def __init__(self, provider_id: str = "deepseek", model: str = "", timeout_seconds: float = 20.0, top_k: int = 3):
        self._provider_id = provider_id
        self._model = model  # 空字符串表示使用提供商默认模型
        self._timeout_seconds = float(timeout_seconds)
        self._top_k = max(1, int(top_k))
        self._retriever = SearchRetriever(Path(ROOT_DIR) / "pet" / "search" / "data")
        self._client = None
        self._client_api_key = ""
        self._client_provider_id = ""

    def set_provider(self, provider_id: str, model: str = ""):
        """切换模型提供商。"""
        """EN: Switch model provider."""
        self._provider_id = provider_id
        self._model = model
        # 重置客户端以使用新提供商
        self._client = None
        self._client_provider_id = ""

    def _get_provider(self) -> LLMProvider | None:
        """获取当前提供商配置。"""
        """EN: Get current provider configuration."""
        return get_provider(self._provider_id)

    def _get_current_model(self, provider: LLMProvider) -> str:
        """获取当前使用的模型ID。"""
        """EN: Get the current model ID."""
        if self._model:
            return self._model
        return provider.default_model

    def _encode_image_to_base64(self, image_path: str) -> tuple[str, str]:
        """将图片编码为base64，返回(mime_type, base64_string)。"""
        """EN: Encode image to base64, returns (mime_type, base64_string)."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        # 检查文件大小
        size = path.stat().st_size
        if size > MAX_SINGLE_IMAGE_SIZE:
            raise ValueError(f"图片过大: {size / 1024 / 1024:.1f}MB > 10MB")

        # 识别MIME类型
        suffix = path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(suffix, "image/jpeg")

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return mime_type, b64

    def _validate_images(self, image_paths: list[str]) -> None:
        """验证图片列表，检查总大小。"""
        """EN: Validate image list, check total size."""
        total_size = 0
        for path in image_paths:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"图片不存在: {path}")
            size = p.stat().st_size
            if size > MAX_SINGLE_IMAGE_SIZE:
                raise ValueError(f"单张图片超过10MB: {path}")
            total_size += size
        if total_size > MAX_TOTAL_SIZE:
            raise ValueError(f"图片总大小超过100MB: {total_size / 1024 / 1024:.1f}MB")

    def _build_vision_content(self, text: str, image_paths: list[str]) -> list:
        """构建多模态消息内容。"""
        """EN: Build multimodal message content."""
        content = [{"type": "text", "text": text}]
        for path in image_paths:
            mime_type, b64 = self._encode_image_to_base64(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"}
            })
        return content

    def _encode_file_to_base64(self, file_path: str) -> tuple[str, str, str]:
        """将文件编码为base64，返回(mime_type, base64_string, file_name)。"""
        """EN: Encode file to base64, returns (mime_type, base64_string, file_name)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件大小
        size = path.stat().st_size
        if size > MAX_SINGLE_IMAGE_SIZE:
            raise ValueError(f"文件过大: {size / 1024 / 1024:.1f}MB > 10MB")

        # 识别MIME类型
        suffix = path.suffix.lower()
        mime_map = {
            # 文档
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".xml": "application/xml",
            ".csv": "text/csv",
            # 代码
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".ts": "text/typescript",
            ".java": "text/x-java",
            ".cpp": "text/x-c++",
            ".c": "text/x-c",
            ".h": "text/x-c",
            ".cs": "text/x-csharp",
            ".go": "text/x-go",
            ".rs": "text/x-rust",
            ".rb": "text/x-ruby",
            ".php": "text/x-php",
            ".swift": "text/x-swift",
            ".kt": "text/x-kotlin",
            # 压缩包
            ".zip": "application/zip",
            ".rar": "application/vnd.rar",
            ".7z": "application/x-7z-compressed",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
            # 音频
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        mime_type = mime_map.get(suffix, "application/octet-stream")

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return mime_type, b64, path.name

    def _validate_files(self, file_paths: list[str]) -> None:
        """验证文件列表，检查总大小。"""
        """EN: Validate file list, check total size."""
        total_size = 0
        for path in file_paths:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"文件不存在: {path}")
            size = p.stat().st_size
            if size > MAX_SINGLE_IMAGE_SIZE:
                raise ValueError(f"单个文件超过10MB: {path}")
            total_size += size
        if total_size > MAX_TOTAL_SIZE:
            raise ValueError(f"文件总大小超过100MB: {total_size / 1024 / 1024:.1f}MB")

    def _is_image_file(self, file_path: str) -> bool:
        """检查是否为图片文件。"""
        """EN: Check if it's an image file."""
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        return Path(file_path).suffix.lower() in image_extensions

    def reply(self, user_message: str, images: list[str] | None = None, history_records: list[str] | None = None) -> str:
        """发送消息并获取回复，支持图片和文件。"""
        """EN: Send message and get reply, supports images and files."""
        clean_user_message = str(user_message).strip()
        if not clean_user_message:
            return "你还没有输入内容。"

        # 获取提供商配置
        provider = self._get_provider()
        if not provider:
            return "未知的模型提供商，请在设置中选择模型。"

        # 获取当前模型配置
        model_id = self._get_current_model(provider)
        model_config = provider.get_model(model_id)

        # 分离图片和非图片文件
        # EN: Separate image and non-image files
        image_paths: list[str] = []
        file_paths: list[str] = []
        if images:
            for path in images:
                if self._is_image_file(path):
                    image_paths.append(path)
                else:
                    file_paths.append(path)

        # 检查视觉支持（仅对图片）
        if image_paths and (not model_config or not model_config.supports_vision):
            return f"{provider.name} 的当前模型不支持图片输入，请切换到支持视觉的模型。"

        # 获取API密钥
        api_key = os.environ.get(provider.api_key_env, "").strip()
        if not api_key:
            return f"未设置 {provider.name} API密钥，请在设置中配置。"
        if OpenAI is None:
            return "当前环境缺少 openai 依赖，请先执行 `pip install openai`。"

        # 验证图片
        if image_paths:
            try:
                self._validate_images(image_paths)
            except (FileNotFoundError, ValueError) as e:
                return f"图片验证失败: {e}"

        # 验证文件
        if file_paths:
            try:
                self._validate_files(file_paths)
            except (FileNotFoundError, ValueError) as e:
                return f"文件验证失败: {e}"

        # 构建文件信息上下文
        # EN: Build file info context
        file_context = ""
        if file_paths:
            file_info_parts = []
            for path in file_paths:
                try:
                    mime_type, b64, file_name = self._encode_file_to_base64(path)
                    file_size = Path(path).stat().st_size
                    file_info_parts.append(
                        f"- 文件名: {file_name}\n"
                        f"  类型: {mime_type}\n"
                        f"  大小: {file_size / 1024:.1f}KB\n"
                        f"  Base64内容:\n{b64[:500]}{'...' if len(b64) > 500 else ''}"
                    )
                except Exception as e:
                    file_info_parts.append(f"- 文件 {Path(path).name}: 读取失败 - {e}")
            file_context = "\n\n以下为用户上传的文件内容：\n" + "\n\n".join(file_info_parts)

        retrieval_query = self._build_search_query(clean_user_message)
        local_context = self._build_local_search_context(retrieval_query, clean_user_message)
        local_context = self._truncate_text(local_context, self._LOCAL_CONTEXT_MAX_CHARS)

        should_use_online = self._should_use_online_search(clean_user_message, local_context)
        search_context = ""
        if should_use_online:
            search_context = self._build_online_search_context(retrieval_query, clean_user_message)
            search_context = self._truncate_text(search_context, self._ONLINE_CONTEXT_MAX_CHARS)

        messages = [{"role": "system", "content": self._SYSTEM_PROMPT}]
        if local_context:
            messages.append({"role": "system", "content": local_context})
        if search_context:
            messages.append({"role": "system", "content": search_context})

        if history_records:
            history_text = "\n".join(str(item).strip() for item in history_records if str(item).strip())
            if history_text:
                history_text = self._truncate_text(history_text, self._HISTORY_CONTEXT_MAX_CHARS)
                messages.append(
                    {
                        "role": "system",
                        "content": f"以下是最近对话历史与摘要，请保持语义连续：\n{history_text}",
                    }
                )

        # 构建用户消息（支持图片和文件）
        # EN: Build user message (supports images and files)
        user_text = clean_user_message + file_context

        if image_paths:
            user_content = self._build_vision_content(user_text, image_paths)
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": user_text})

        try:
            client = self._get_client(api_key, provider)
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                stream=False,
            )
        except Exception as exc:  # pragma: no cover - 依赖外部网络
            return f"调用 {provider.name} 失败：{exc}"

        if not response.choices:
            return "模型未返回有效结果，请稍后重试。"
        message = response.choices[0].message
        content = getattr(message, "content", "")
        if isinstance(content, list):
            merged_parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = str(part.get("text", "")).strip()
                    if text:
                        merged_parts.append(text)
                else:
                    text = str(part).strip()
                    if text:
                        merged_parts.append(text)
            content = "\n".join(merged_parts)

        final_text = str(content).strip()
        if not final_text:
            return "模型返回为空，请稍后再试。"
        return final_text

    def _build_search_query(self, user_message: str) -> str:
        user_keywords = self._extract_user_role_keywords(user_message)
        parts: list[str] = [*self._SEED_TERMS, *user_keywords, user_message]
        deduplicated: list[str] = []
        for item in parts:
            clean = str(item).strip()
            if not clean or clean in deduplicated:
                continue
            deduplicated.append(clean)
        return " ".join(deduplicated)

    def _extract_user_role_keywords(self, user_message: str) -> list[str]:
        tokens = [token.lower() for token in self._TOKEN_RE.findall(str(user_message))]
        keywords: list[str] = []
        for token in tokens:
            clean = token.strip()
            if not clean:
                continue

            if clean in self._ROLE_HINT_TERMS:
                keywords.append(clean)
                continue

            if any(hint in clean for hint in ("设定", "背景", "角色", "人设", "经历", "身份", "世界观", "性格", "关系", "故事")):
                keywords.append(clean)

        unique_keywords: list[str] = []
        for item in keywords:
            if item not in unique_keywords:
                unique_keywords.append(item)
        return unique_keywords[:8]

    def _should_use_online_search(self, user_message: str, local_context: str) -> bool:
        if not local_context:
            return True
        clean_message = str(user_message).strip()
        if not clean_message:
            return False
        return any(keyword in clean_message for keyword in self._TIMELY_KEYWORDS)

    @staticmethod
    def _truncate_text(text: str, max_chars: int) -> str:
        raw = str(text).strip()
        if not raw:
            return ""
        if len(raw) <= max_chars:
            return raw
        return raw[:max_chars] + "\n...(已截断)"

    def _get_client(self, api_key: str, provider: LLMProvider):
        """根据provider配置创建OpenAI兼容客户端。"""
        """EN: Create OpenAI compatible client based on provider configuration."""
        if self._client is not None and self._client_api_key == api_key and self._client_provider_id == provider.id:
            return self._client
        self._client = OpenAI(
            api_key=api_key,
            base_url=provider.base_url,
            timeout=self._timeout_seconds
        )
        self._client_api_key = api_key
        self._client_provider_id = provider.id
        return self._client

    def _build_local_search_context(self, retrieval_query: str, user_message: str) -> str:
        try:
            search_hits = self._retriever.search(retrieval_query, top_k=self._top_k)
        except Exception as exc:  # pragma: no cover - 本地IO兜底
            return f"本地资料检索失败：{exc}"

        if not search_hits:
            return ""

        context = build_search_context(user_message, search_hits)
        if not context:
            return ""
        return f"以下为本地角色设定资料检索结果，请优先参考：\n{context}"

    def _build_online_search_context(self, retrieval_query: str, user_message: str) -> str:
        if DDGS is None:
            return "联网搜索不可用：缺少 duckduckgo-search 依赖。"

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=self._DDG_RENAME_WARNING_PATTERN,
                    category=RuntimeWarning,
                )
                with DDGS() as ddgs:
                    results = list(
                        ddgs.text(
                            keywords=retrieval_query,
                            region="cn-zh",
                            safesearch="moderate",
                            max_results=self._top_k,
                        )
                    )
        except Exception as exc:  # pragma: no cover - 依赖外网
            return f"联网搜索失败：{exc}"

        if not results:
            return f"用户问题：{user_message}\n检索词：{retrieval_query}\n未检索到有效网页结果。"

        lines: list[str] = [
            f"用户问题：{user_message}",
            f"检索词：{retrieval_query}",
            "以下为联网搜索结果，请优先基于这些结果回答：",
        ]
        for index, item in enumerate(results, start=1):
            title = str(item.get("title", "")).strip()
            body = str(item.get("body", "")).strip()
            if not (title or body):
                continue
            lines.append(f"[{index}] 标题：{title}")
            if body:
                lines.append(f"[{index}] 摘要：{body}")
        return "\n".join(lines)
