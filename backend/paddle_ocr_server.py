from __future__ import annotations

import base64
import dataclasses
import io
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / ".runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(RUNTIME_DIR / "paddlex"))
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_DIR / "matplotlib"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

app = FastAPI(title="Local PaddleOCR Service", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_engine = None
ocr_import_error: str | None = None


class OCRRequest(BaseModel):
    image_base64: str
    lang: str = "ch"


def get_ocr_engine(lang: str = "ch") -> Any:
    global ocr_engine, ocr_import_error
    if ocr_engine is not None:
        return ocr_engine
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:  # pragma: no cover
        ocr_import_error = str(exc)
        raise RuntimeError(
            "PaddleOCR 未安装或导入失败。请先安装 paddleocr 和 paddlepaddle。"
        ) from exc
    ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang)
    return ocr_engine


def ocr_result_to_plain(obj: Any) -> Any:
    """将 PaddleOCR 3.x / PaddleX 的 predict 结果转为可遍历的 dict/list。"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): ocr_result_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [ocr_result_to_plain(x) for x in obj]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return ocr_result_to_plain(dataclasses.asdict(obj))
        except Exception:
            pass
    if hasattr(obj, "json") and callable(getattr(obj, "json")):
        try:
            data = obj.json()
            if isinstance(data, str):
                return json.loads(data)
            return ocr_result_to_plain(data)
        except Exception:
            pass
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return ocr_result_to_plain(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return ocr_result_to_plain(vars(obj))
        except Exception:
            pass
    return str(obj)


def collect_ocr_items(node: Any, output: list[dict[str, Any]]) -> None:
    if node is None:
        return

    if isinstance(node, dict):
        # PaddleX：rec_texts；部分版本写作 rec_text
        texts = node.get("rec_texts")
        if texts is None and isinstance(node.get("rec_text"), list):
            texts = node.get("rec_text")
        if isinstance(texts, list):
            scores = node.get("rec_scores") or node.get("rec_score") or []
            polys = node.get("dt_polys") or node.get("rec_polys") or node.get("dt_boxes") or []
            for index, text in enumerate(texts):
                if not text:
                    continue
                score = scores[index] if index < len(scores) else None
                box = polys[index] if index < len(polys) else None
                output.append(
                    {
                        "text": str(text),
                        "score": float(score) if score is not None else None,
                        "box": box,
                    }
                )
            return
        text = node.get("text") or node.get("rec_text") or node.get("transcription")
        score = node.get("score") or node.get("rec_score") or node.get("confidence")
        box = node.get("box") or node.get("points") or node.get("bbox") or node.get("poly")
        if text:
            output.append(
                {
                    "text": str(text),
                    "score": float(score) if score is not None else None,
                    "box": box,
                }
            )
            return
        for value in node.values():
            collect_ocr_items(value, output)
        return

    if isinstance(node, (list, tuple)):
        if (
            len(node) == 2
            and isinstance(node[1], (list, tuple))
            and len(node[1]) >= 1
            and isinstance(node[1][0], str)
        ):
            text = node[1][0]
            score = node[1][1] if len(node[1]) > 1 else None
            output.append(
                {
                    "text": text,
                    "score": float(score) if score is not None else None,
                    "box": node[0],
                }
            )
            return
        for item in node:
            collect_ocr_items(item, output)
        return


def to_json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json_safe(val) for key, val in value.items()}
    return value


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "cache_home": os.environ.get("PADDLE_PDX_CACHE_HOME"),
        "matplotlib_home": os.environ.get("MPLCONFIGDIR"),
        "import_error": ocr_import_error,
    }


@app.post("/ocr")
def ocr_endpoint(payload: OCRRequest) -> dict[str, Any]:
    image_data = base64.b64decode(payload.image_base64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    image_array = np.array(image)
    engine = get_ocr_engine(payload.lang)
    result = engine.ocr(image_array)
    # PaddleOCR 3.x / PaddleX 返回对象或嵌套结构，先规范化为 dict/list 再解析
    plain = ocr_result_to_plain(result)

    raw_items: list[dict[str, Any]] = []
    collect_ocr_items(plain, raw_items)
    lines = [item["text"] for item in raw_items if item.get("text")]

    return {
        "text": "\n".join(lines).strip(),
        "items": to_json_safe(raw_items),
        "count": len(raw_items),
    }
