"""Minimal open-world forward chaining for ProofWriter atom/rule representations."""
from __future__ import annotations

import re
from typing import Any, Iterable

TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|->|[()]|[^\s()]+')
VARIABLES = {"someone", "something"}
Atom = tuple[str, str, str, str]
Rule = tuple[tuple[Atom, ...], Atom]


def parse_sexpr(text: str) -> Any:
    tokens = TOKEN_RE.findall(text)
    position = 0

    def parse_one() -> Any:
        nonlocal position
        if position >= len(tokens):
            raise ValueError("Unexpected end of S-expression")
        token = tokens[position]
        position += 1
        if token == "(":
            values = []
            while position < len(tokens) and tokens[position] != ")":
                values.append(parse_one())
            if position >= len(tokens):
                raise ValueError("Unclosed S-expression")
            position += 1
            return values
        if token == ")":
            raise ValueError("Unexpected closing parenthesis")
        if token.startswith('"'):
            return bytes(token[1:-1], "utf-8").decode("unicode_escape")
        return token

    value = parse_one()
    if position != len(tokens):
        raise ValueError(f"Trailing tokens in S-expression: {tokens[position:]}")
    return value


def as_atom(value: Any) -> Atom:
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(x, str) for x in value):
        raise ValueError(f"Not a ProofWriter atom: {value!r}")
    return tuple(value)  # type: ignore[return-value]


def parse_atom(text: str) -> Atom:
    return as_atom(parse_sexpr(text))


def parse_rule(text: str) -> Rule:
    value = parse_sexpr(text)
    if not isinstance(value, list) or len(value) != 3 or value[1] != "->":
        raise ValueError(f"Not a ProofWriter rule: {value!r}")
    premises_value = value[0]
    if not isinstance(premises_value, list):
        raise ValueError(f"Invalid premises: {premises_value!r}")
    premises = tuple(as_atom(item) for item in premises_value)
    return premises, as_atom(value[2])


def opposite(atom: Atom) -> Atom:
    if atom[3] not in {"+", "-"}:
        raise ValueError(f"Invalid polarity: {atom!r}")
    return atom[:3] + (("-" if atom[3] == "+" else "+"),)


def match_atom(pattern: Atom, fact: Atom, binding: dict[str, str]) -> dict[str, str] | None:
    result = dict(binding)
    for expected, actual in zip(pattern, fact):
        if expected in VARIABLES:
            bound = result.get(expected)
            if bound is not None and bound != actual:
                return None
            result[expected] = actual
        elif expected != actual:
            return None
    return result


def ground(atom: Atom, binding: dict[str, str]) -> Atom:
    return tuple(binding.get(term, term) for term in atom)  # type: ignore[return-value]


def rule_conclusions(rule: Rule, facts: set[Atom]) -> set[Atom]:
    premises, conclusion = rule
    bindings = [dict()]
    for premise in premises:
        next_bindings = []
        for binding in bindings:
            for fact in facts:
                matched = match_atom(premise, fact, binding)
                if matched is not None:
                    next_bindings.append(matched)
        bindings = next_bindings
        if not bindings:
            break
    return {ground(conclusion, binding) for binding in bindings}


def closure(facts: Iterable[Atom], rules: Iterable[Rule]) -> set[Atom]:
    known = set(facts)
    rules = list(rules)
    while True:
        derived = set()
        for rule in rules:
            derived.update(rule_conclusions(rule, known))
        new = derived - known
        if not new:
            return known
        known.update(new)


def contradictions(facts: Iterable[Atom]) -> set[tuple[Atom, Atom]]:
    values = set(facts)
    return {
        tuple(sorted((atom, opposite(atom))))  # type: ignore[arg-type]
        for atom in values
        if opposite(atom) in values
    }
