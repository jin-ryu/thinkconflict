"""트레이스 파서: Qwen/Olmo `<think>` · gpt-oss Harmony analysis 채널 추출 (계획서 Phase 2-2).

서빙 스택이 reasoning을 이미 분리해 주는 경우(reasoning_content)를 1순위로 쓰고,
원문 텍스트의 <think> 태그 / Harmony 채널 마커를 폴백으로 파싱한다.
파싱 실패는 None이 아니라 ParsedTrace.ok=False로 기록해 **파싱 실패율 점검**
(go/no-go 게이트 이전의 인프라 점검 항목)이 가능하게 한다.

usage: python -m diagnosis.trace_parser results/raw/*.jsonl   # 파싱 실패율 리포트
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass

THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)
THINK_OPEN_RE = re.compile(r"<think>(.*)", re.DOTALL)  # 미종결 (max_tokens 절단 등)
# 여는 태그가 **프롬프트**에 있는 채팅 템플릿 (Qwen3.6 실측): 템플릿이 생성 프리픽스로
# '<think>\n'을 붙여 두므로 완성문에는 닫는 태그만 남는다. 여는 태그가 없다고 파싱
# 실패로 처리하면 전 건이 통째로 버려진다.
THINK_CLOSE_RE = re.compile(r"</think>")
# Harmony 포맷: <|channel|>analysis<|message|>...<|end|> / <|channel|>final<|message|>...
HARMONY_CH_RE = re.compile(
    r"<\|channel\|>(\w+)(?:\s[^<]*)?<\|message\|>(.*?)(?=<\|end\|>|<\|channel\|>|<\|return\|>|\Z)",
    re.DOTALL)


@dataclass
class ParsedTrace:
    ok: bool
    thinking: str | None   # 사고 채널 (분석 대상)
    answer: str | None     # 최종 답변 텍스트
    failure: str | None = None  # 실패 사유 (실패율 리포트용)


def parse_record(rec: dict) -> ParsedTrace:
    """serving/client.py가 기록한 생성 레코드 하나를 파싱한다."""
    text = rec.get("text")
    reasoning = rec.get("reasoning")
    if rec.get("error") or text is None:
        return ParsedTrace(False, None, None, failure="generation_error")
    if reasoning:  # 서빙 스택이 이미 분리 (vLLM reasoning parser)
        return ParsedTrace(True, reasoning, text.strip())
    if rec.get("model") == "gptoss" or "<|channel|>" in text:
        return parse_harmony(text)
    return parse_think(text, thinking_enabled=rec.get("thinking", True))


def parse_think(text: str, *, thinking_enabled: bool = True) -> ParsedTrace:
    m = THINK_RE.search(text)
    if m:
        answer = (text[:m.start()] + text[m.end():]).strip()
        return ParsedTrace(True, m.group(1).strip(), answer)
    if not thinking_enabled:  # 레짐 통제(no-thinking): 사고 부재가 정상
        return ParsedTrace(True, None, text.strip())
    m = THINK_CLOSE_RE.search(text)
    if m:  # 닫는 태그만 존재 — 여는 태그는 프롬프트 프리픽스였다
        thinking, answer = text[:m.start()].strip(), text[m.end():].strip()
        if not answer:
            # 닫는 태그 직후 절단 — 답변 미도달. 빈 문자열로 넘기면 grade()가 이를
            # 기권으로 세어 기권율(의무 병기 지표)을 오염시킨다.
            return ParsedTrace(False, thinking, None, failure="empty_answer")
        return ParsedTrace(True, thinking, answer)
    m = THINK_OPEN_RE.search(text)
    if m:  # <think> 열리고 안 닫힘 — 답변 미도달
        return ParsedTrace(False, m.group(1).strip(), None, failure="unclosed_think")
    return ParsedTrace(False, None, text.strip(), failure="no_think_tag")


def parse_harmony(text: str) -> ParsedTrace:
    channels: dict[str, list[str]] = {}
    for name, content in HARMONY_CH_RE.findall(text):
        channels.setdefault(name, []).append(content.strip())
    analysis = "\n".join(channels.get("analysis", [])) or None
    final = "\n".join(channels.get("final", [])) or None
    if final is None and analysis is None:
        return ParsedTrace(False, None, text.strip(), failure="no_harmony_channels")
    if final is None:
        return ParsedTrace(False, analysis, None, failure="no_final_channel")
    return ParsedTrace(True, analysis, final)


def main() -> None:
    ap = argparse.ArgumentParser(description="생성 JSONL 파싱 실패율 리포트")
    ap.add_argument("paths", nargs="+")
    args = ap.parse_args()
    for path in args.paths:
        total, fails = 0, {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                total += 1
                p = parse_record(json.loads(line))
                if not p.ok:
                    fails[p.failure] = fails.get(p.failure, 0) + 1
        n_fail = sum(fails.values())
        rate = n_fail / total if total else 0.0
        print(f"{path}: N={total} 실패={n_fail} ({rate:.2%}) {fails or ''}")


if __name__ == "__main__":
    main()
