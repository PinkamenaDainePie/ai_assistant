# -*- coding: utf-8 -*-
"""人物 AI 入口：启动 API 或单轮对话（支持多角色）。"""
import argparse
import sys
from pathlib import Path

from .config import DEFAULT_DATA_DIR
from .characters import get_character
from .persona import reply


def _configure_windows_console_utf8() -> None:
    """Ensure readable Chinese logs/output on Windows terminals."""
    if sys.platform != "win32":
        return
    try:
        # Switch Windows console code page to UTF-8.
        import ctypes
        ctypes.windll.kernel32.SetConsoleCP(65001)
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except (AttributeError, OSError):
        pass
    try:
        # Python 3.7+: force UTF-8 streams for print/log output.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        # Best-effort only; startup should never fail due to console encoding.
        pass


def run_single(query: str, character_id: str, data_dir: Path) -> None:
    """单轮对话：打印陛下所问与人物 AI 的回复。"""
    character = get_character(character_id)
    print(f"角色：{character.dynasty}{character.name}（ID：{character.id}）")
    print("陛下所问:", query)
    print()
    result = reply(user_message=query, character_id=character_id, data_dir=data_dir)
    print(f"{character.name}:", result["reply"])
    if result.get("references"):
        print()
        print("参考史料条数:", result["retrieved_count"])
        for i, ref in enumerate(result["references"][:3], 1):
            print(f"  [{i}] {ref.get('source')} | {ref.get('section', '')}")


def run_api(host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 FastAPI 服务。"""
    try:
        import uvicorn
    except ImportError:
        print("请安装 uvicorn：pip install uvicorn", file=sys.stderr)
        sys.exit(1)
    from .api import app
    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        # Windows: WinError 10048；Linux: errno 98 EADDRINUSE
        text = str(e).lower()
        if (
            getattr(e, "winerror", None) == 10048
            or e.errno == 98
            or "10048" in str(e)
            or "address already in use" in text
            or "只允许使用一次" in str(e)
        ):
            print(
                f"错误：端口 {port} 已被占用，本 API 进程未启动。"
                f"请结束占用该端口的旧进程（例如之前的 uvicorn），或改用 --port 其它端口；"
                f"否则前端会 Failed to fetch 或仍连到旧代码进程。",
                file=sys.stderr,
            )
            sys.exit(1)
        raise


def main() -> None:
    _configure_windows_console_utf8()
    parser = argparse.ArgumentParser(description="历史人物 AI（皇帝咨询场景）")
    parser.add_argument("--mode", choices=["api", "chat"], default="api", help="api=启动HTTP服务, chat=单轮对话")
    parser.add_argument("--character", type=str, default="wang_anshi", help="角色ID，如 wang_anshi / zhang_juzheng")
    parser.add_argument("--query", type=str, help="单轮对话时的陛下提问（仅 mode=chat 时使用）")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="史料目录路径")
    parser.add_argument("--host", default="0.0.0.0", help="API 监听地址")
    parser.add_argument("--port", type=int, default=8000, help="API 端口")
    args = parser.parse_args()

    if args.mode == "chat":
        if not args.query:
            print("请提供 --query 作为陛下提问内容。", file=sys.stderr)
            sys.exit(1)
        run_single(args.query, args.character, args.data_dir)
    else:
        run_api(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
