"""공통 생성 클라이언트 (계획서 Phase 2-1, §3.3.1(2)).

vLLM OpenAI 호환 엔드포인트에 대해 디코딩을 고정(t=0.6, top-p 0.95)하고
시드 ≥5를 반복 관리한다. 생성 원문·셔플 순서·디코딩 설정을 전부 JSONL로
기록해 라벨링(diagnosis/)이 재현 가능하게 한다. raw 생성물은 git 미포함.

usage:
    python -m serving.client --data data/3_processed/ramdocs/ramdocs_a.jsonl \
        --model qwen --env standard --out results/raw/qwen_standard_ramdocs_a.jsonl
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from experiments.exp1_mitigation.envs import build_messages, ENVS
from preprocessing.schema import assert_reviewed, read_jsonl, render_documents

# 사전등록 디코딩 (계획서 §3.3.1(2)): 권장 디코딩 고정, 시드 최소 5회 반복
DECODING = {"temperature": 0.6, "top_p": 0.95}
SEEDS = (13, 42, 71, 108, 2026)

MODELS = {  # 논리명 → (기본 포트, 기본 model id) — launch_*.sh와 일치 (PPT 19p)
    "qwen": (8001, "Qwen/Qwen3.6-27B"),          # 주력 추론 모델, thinking 하드 토글
    "gemma": (8002, "google/gemma-3-27b-it"),    # 비추론 교차 계열 대조 (트레이스 없음)
    "gptoss": (8003, "openai/gpt-oss-20b"),      # MoE 추론 모델, Harmony 채널
}
NON_THINKING_MODELS = {"gemma"}  # 추론 채널 자체가 없는 모델 — thinking 라벨 강제 False


@dataclass
class GenConfig:
    model_key: str
    env: str = "standard"
    thinking: bool = True        # Qwen 하드 토글 (§3.3.3(b)); 타 모델은 무시됨
    effort: str | None = None    # gpt-oss reasoning effort (보조 신호 전용)
    max_tokens: int = 8192
    base_url: str | None = None

    def __post_init__(self) -> None:
        if self.model_key in NON_THINKING_MODELS:
            # 트레이스 부재를 파싱 실패로 오독하지 않도록 라벨을 강제한다
            self.thinking = False


def make_client(cfg: GenConfig) -> tuple[OpenAI, str]:
    port, model_id = MODELS[cfg.model_key]
    base = cfg.base_url or f"http://localhost:{port}/v1"
    return OpenAI(base_url=base, api_key="EMPTY"), model_id


def generate_one(client: OpenAI, model_id: str, cfg: GenConfig,
                 messages: list[dict], seed: int) -> dict:
    extra: dict = {}
    if cfg.model_key == "qwen":
        extra["chat_template_kwargs"] = {"enable_thinking": cfg.thinking}
    if cfg.model_key == "gptoss" and cfg.effort:
        extra["reasoning_effort"] = cfg.effort
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model_id, messages=messages, seed=seed,
                max_tokens=cfg.max_tokens, extra_body=extra or None, **DECODING)
            choice = resp.choices[0]
            return {"text": choice.message.content,
                    "reasoning": getattr(choice.message, "reasoning_content", None),
                    "finish_reason": choice.finish_reason,
                    "usage": resp.usage.model_dump() if resp.usage else None}
        except Exception as e:  # noqa: BLE001 — 서빙 일시 오류 재시도
            if attempt == 2:
                return {"text": None, "error": str(e)}
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def run(cfg: GenConfig, data_path: Path, out_path: Path,
        seeds: tuple[int, ...] = SEEDS, workers: int = 1) -> None:
    assert_reviewed(data_path)   # 검토 전 초안으로 생성하지 못하게 막는다
    client, model_id = make_client(cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():  # 중단 지점부터 재개
        with open(out_path, encoding="utf-8") as f:
            done = {(r["question_id"], r["seed"]) for r in map(json.loads, f) if "text" in r}
    todo = [(item, seed) for item in read_jsonl(data_path) for seed in seeds
            if (item.question_id, seed) not in done]

    def one(item, seed) -> dict:
        # 셔플 시드를 생성 시드에 결속 — 시드별로 문서 순서가 달라져
        # 위치 편향이 시드 반복에 걸쳐 평균화된다 (§3.1.1(4))
        docs_text, doc_order = render_documents(item, shuffle_seed=seed)
        messages = build_messages(cfg.env, item.question, docs_text)
        return {"question_id": item.question_id, "dataset": item.dataset,
                "model": cfg.model_key, "env": cfg.env, "seed": seed,
                "thinking": cfg.thinking, "effort": cfg.effort,
                "doc_order": doc_order, "decoding": DECODING,
                **generate_one(client, model_id, cfg, messages, seed)}

    lock = Lock()
    with open(out_path, "a", encoding="utf-8") as out:
        def emit(rec: dict) -> None:
            with lock:      # 워커가 여러 개면 한 줄이 섞여 쓰이지 않도록 직렬화
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
        if workers <= 1:
            for item, seed in todo:
                emit(one(item, seed))
        else:
            # 동시 요청은 **서빙 처리량**만 바꾼다 — 디코딩 설정(t·top_p)도 시드도
            # 요청마다 그대로 실려 나가므로 사전등록과 무관하다 (§3.3.1(2)).
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(one, item, seed) for item, seed in todo]
                for fut in as_completed(futs):
                    emit(fut.result())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--model", required=True, choices=list(MODELS))
    ap.add_argument("--env", default="standard", choices=list(ENVS))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-thinking", action="store_true",
                    help="Qwen 하드 토글: 사고 채널 차단 (레짐 통제, §3.3.3(b))")
    ap.add_argument("--effort", choices=["low", "medium", "high"],
                    help="gpt-oss reasoning effort (보조 신호 전용)")
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--workers", type=int, default=1,
                    help="동시 요청 수. 서빙 처리량만 바꾸며 디코딩·시드는 그대로다")
    args = ap.parse_args()
    cfg = GenConfig(model_key=args.model, env=args.env,
                    thinking=not args.no_thinking, effort=args.effort)
    run(cfg, args.data, args.out, tuple(args.seeds), workers=args.workers)


if __name__ == "__main__":
    main()
