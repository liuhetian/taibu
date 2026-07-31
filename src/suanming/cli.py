from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .assets import load_asset_manifest, verify_asset_manifest
from .errors import InputDecodeError, SuanmingError
from .runtime import describe_pipelines, pipeline_schema, run_pipeline


def _json_dump(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )


def _load_request(spec: str | None) -> dict[str, Any]:
    if spec is None or spec == "-":
        text = sys.stdin.read()
        if not text.strip():
            return {}
    elif spec.startswith("@"):
        path = Path(spec[1:])
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise InputDecodeError(f"无法读取输入文件：{path}") from exc
    else:
        text = spec

    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputDecodeError(
            "输入不是有效 JSON。",
            details=[
                {
                    "line": exc.lineno,
                    "column": exc.colno,
                    "message": exc.msg,
                }
            ],
        ) from exc
    if not isinstance(value, dict):
        raise InputDecodeError("管线输入必须是 JSON object。")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suanming",
        description="自包含算命内核：所有成功结果仅输出 JSON。",
    )
    parser.add_argument("--pretty", action="store_true", help="格式化 JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出已注册管线")
    list_parser.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )

    schema_parser = subparsers.add_parser("schema", help="输出 JSON Schema")
    schema_parser.add_argument("pipeline")
    schema_parser.add_argument(
        "--kind",
        choices=("input", "output", "both"),
        default="both",
    )
    schema_parser.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )

    run_parser = subparsers.add_parser("run", help="执行管线")
    run_parser.add_argument("pipeline")
    run_parser.add_argument(
        "--input",
        help="内联 JSON、@文件路径；省略或 '-' 时从 stdin 读取",
    )
    run_parser.add_argument("--seed", help="可复现随机种子")
    run_parser.add_argument("--locale", default="zh-CN")
    run_parser.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )

    assets_parser = subparsers.add_parser("assets", help="输出或校验素材清单")
    assets_parser.add_argument("--verify", action="store_true")
    assets_parser.add_argument("--root", help="项目根目录")
    assets_parser.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            payload: Any = {"pipelines": describe_pipelines()}
        elif args.command == "schema":
            payload = pipeline_schema(args.pipeline, args.kind)
        elif args.command == "assets":
            payload = (
                verify_asset_manifest(args.root) if args.verify else load_asset_manifest(args.root)
            )
        else:
            request = _load_request(args.input)
            payload = run_pipeline(
                args.pipeline,
                request,
                seed=args.seed,
                locale=args.locale,
            ).model_dump(mode="json", exclude_none=True)
        sys.stdout.write(_json_dump(payload, pretty=args.pretty) + "\n")
        return 0
    except SuanmingError as exc:
        sys.stderr.write(_json_dump(exc.as_dict(), pretty=True) + "\n")
        return 2
    except Exception as exc:  # pragma: no cover - final CLI safety net
        payload = {
            "error": {
                "code": "internal_error",
                "message": str(exc),
                "details": [],
            }
        }
        sys.stderr.write(_json_dump(payload, pretty=True) + "\n")
        return 1
