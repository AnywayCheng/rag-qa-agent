import argparse
import sys
from pathlib import Path

from . import agent, ingest, topic


def _cmd_ingest(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"目錄不存在：{directory}", file=sys.stderr)
        return 1

    results = ingest.ingest_directory(directory)
    if not results:
        print("沒有找到支援的文件（.pdf/.txt/.md）")
        return 0

    for filename, count in results.items():
        print(f"{filename}: {count} chunks")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    result = agent.ask(args.question, force_refresh=args.refresh)
    print(result["answer"])

    if result["sources"]:
        print("\n來源：")
        for src in result["sources"]:
            print(f"- {src['source_title']}: {src['source_url']}")

    if result["searched_categories"]:
        print(f"\n（本次重新搜尋了：{', '.join(result['searched_categories'])}）")
    return 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    topic_key = topic.slugify(args.topic)
    categories = [args.category] if args.category else None
    refreshed = agent.refresh_topic(topic_key, categories=categories)
    print(
        f"已刷新主題「{args.topic}」（topic_key={topic_key}）：{', '.join(refreshed)}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag-qa")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="批次匯入本地文件目錄")
    ingest_parser.add_argument("directory", help="文件目錄路徑，例如 ./data/raw")
    ingest_parser.set_defaults(func=_cmd_ingest)

    ask_parser = subparsers.add_parser("ask", help="問問題，自動判斷是否需要重新搜尋")
    ask_parser.add_argument("question", help="要問的問題")
    ask_parser.add_argument(
        "--refresh", action="store_true", help="強制重新搜尋，不管 TTL"
    )
    ask_parser.set_defaults(func=_cmd_ask)

    refresh_parser = subparsers.add_parser("refresh", help="手動強制刷新某主題")
    refresh_parser.add_argument(
        "topic", help="主題文字（會被正規化成 topic_key 並當搜尋關鍵字）"
    )
    refresh_parser.add_argument(
        "--category",
        choices=["news", "paper", "github"],
        help="只刷新單一面向，不指定則三個面向都刷新",
    )
    refresh_parser.set_defaults(func=_cmd_refresh)

    return parser


def main() -> None:
    # Windows 主控台預設 codepage 常不是 UTF-8，中文輸出會亂碼，強制重設編碼
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
