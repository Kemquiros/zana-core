#!/usr/bin/env python3
"""
ZANA Orchestrator — Multi-Agent Coordinator
============================================

Coordinates parallel and sequential execution across:
  - NotebookLM (retrieval)
  - Gemini CLI (general knowledge)
  - Pi + Claude Haiku/Sonnet/Opus (reasoning)

Patterns supported:
  1. Single route    → one agent handles the task
  2. Fan-out         → multiple agents in parallel, results aggregated
  3. Pipeline        → output of agent A feeds agent B
  4. Retrieve+Reason → NotebookLM retrieves, Claude reasons over output

Usage:
  python3 orchestrator.py "task description"
  python3 orchestrator.py --pattern fan-out "task"
  python3 orchestrator.py --pattern pipeline "task"
  python3 orchestrator.py --retrieve-then-reason "task"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from zana_router import route as _route
from classify import ClaudeModel, Route


# ─── Agent Result ─────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    agent: str          # "notebooklm" | "gemini" | "claude:haiku" | etc.
    query: str
    result: str
    latency_ms: float
    error: bool = False

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "query": self.query[:80] + "..." if len(self.query) > 80 else self.query,
            "result": self.result,
            "latency_ms": round(self.latency_ms),
            "error": self.error,
        }


# ─── Single Agent Execution ───────────────────────────────────────────────────

def run_agent(
    query: str,
    force_backend: str | None = None,
    force_model: str | None = None,
    notebook_id: str | None = None,
) -> AgentResult:
    """Run a single agent and return the result with timing."""
    t0 = time.time()
    out = _route(
        query=query,
        force_backend=force_backend,
        force_model=force_model,
        notebook_id=notebook_id,
        use_pi=True,
    )
    latency = (time.time() - t0) * 1000

    agent_label = out["route"]
    if out["claude_model"]:
        agent_label = f"claude:{out['claude_model']}"

    result_text = out.get("result") or ""
    is_error = result_text.startswith("[ERROR]")

    return AgentResult(
        agent=agent_label,
        query=query,
        result=result_text,
        latency_ms=latency,
        error=is_error,
    )


# ─── Orchestration Patterns ───────────────────────────────────────────────────

def pattern_auto(query: str, notebook_id: str | None = None) -> list[AgentResult]:
    """Default: route to single best agent."""
    return [run_agent(query, notebook_id=notebook_id)]


def pattern_fan_out(
    query: str,
    agents: list[tuple[str | None, str | None]],
    notebook_id: str | None = None,
    max_workers: int = 4,
) -> list[AgentResult]:
    """
    Fan out to multiple agents in parallel. Aggregate all results.

    agents: list of (backend, model) tuples, e.g.:
      [("gemini", None), ("claude", "sonnet"), ("notebooklm", None)]
    """
    results: list[AgentResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_agent, query, backend, model, notebook_id): (backend, model)
            for backend, model in agents
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                backend, model = futures[future]
                results.append(AgentResult(
                    agent=f"{backend}:{model}" if model else backend or "unknown",
                    query=query,
                    result=f"[ERROR] {exc}",
                    latency_ms=0,
                    error=True,
                ))
    return sorted(results, key=lambda r: r.latency_ms)


def pattern_pipeline(steps: list[str], initial_context: str = "") -> list[AgentResult]:
    """
    Sequential pipeline: output of step N feeds into step N+1 as context.

    steps: list of query templates, where {context} is replaced with prev output.
    initial_context: context for first step.
    """
    results: list[AgentResult] = []
    context = initial_context
    for i, query_template in enumerate(steps):
        query = query_template.format(context=context) if "{context}" in query_template else query_template
        result = run_agent(query)
        results.append(result)
        context = result.result  # feed output to next step
        if result.error:
            break  # abort pipeline on error
    return results


def pattern_retrieve_then_reason(
    retrieval_query: str,
    reasoning_prompt_template: str,
    claude_model: str = "sonnet",
    notebook_id: str | None = None,
) -> list[AgentResult]:
    """
    Retrieve from NotebookLM → reason with Claude.

    retrieval_query: what to ask NotebookLM
    reasoning_prompt_template: template with {context} for Claude
    """
    # Step 1: Retrieve
    retrieval = run_agent(retrieval_query, force_backend="notebooklm", notebook_id=notebook_id)
    if retrieval.error:
        return [retrieval]

    # Step 2: Reason
    reasoning_query = reasoning_prompt_template.format(context=retrieval.result)
    reasoning = run_agent(reasoning_query, force_backend="claude", force_model=claude_model)
    return [retrieval, reasoning]


def pattern_gemini_then_claude(
    research_query: str,
    synthesis_template: str,
    claude_model: str = "sonnet",
) -> list[AgentResult]:
    """
    Research with Gemini (0 tokens) → synthesize with Claude.

    Useful for: research a topic with Gemini, then Claude writes code/plan.
    """
    research = run_agent(research_query, force_backend="gemini")
    if research.error:
        return [research]

    synthesis_query = synthesis_template.format(context=research.result)
    synthesis = run_agent(synthesis_query, force_backend="claude", force_model=claude_model)
    return [research, synthesis]


# ─── Output Formatting ────────────────────────────────────────────────────────

def format_results(results: list[AgentResult], fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"\n{'─' * 60}")
        lines.append(f"[{i}] Agent: {r.agent}  ({r.latency_ms:.0f}ms)")
        lines.append(f"{'─' * 60}")
        lines.append(r.result)

    # Append synthesized summary for multi-agent results
    if len(results) > 1:
        non_error = [r for r in results if not r.error]
        lines.append(f"\n{'═' * 60}")
        lines.append(f"[SYNTHESIS] {len(non_error)}/{len(results)} agents responded successfully.")
        if non_error:
            lines.append(f"Fastest: {non_error[0].agent} ({non_error[0].latency_ms:.0f}ms)")

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zana_orchestrator",
        description="ZANA Orchestrator — multi-agent coordination.",
    )
    p.add_argument("query", nargs="?", help="Task/query (reads stdin if omitted)")
    p.add_argument(
        "--pattern",
        choices=["auto", "fan-out", "pipeline", "retrieve-reason", "research-synthesize"],
        default="auto",
        help="Orchestration pattern (default: auto)",
    )
    p.add_argument(
        "--agents",
        default="gemini,claude:sonnet",
        help="Comma-separated agents for fan-out: gemini,claude:haiku,notebooklm,claude:opus",
    )
    p.add_argument("--notebook-id", metavar="ID", help="NotebookLM notebook ID")
    p.add_argument("--model", default="sonnet",
                   choices=["haiku", "sonnet", "opus"],
                   help="Claude model for synthesis step")
    p.add_argument("-j", "--json", action="store_true", help="JSON output")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def _parse_agents(agents_str: str) -> list[tuple[str | None, str | None]]:
    """Parse "gemini,claude:sonnet,notebooklm" → [(backend, model), ...]"""
    result = []
    for a in agents_str.split(","):
        a = a.strip()
        if ":" in a:
            backend, model = a.split(":", 1)
            result.append((backend.strip(), model.strip()))
        else:
            result.append((a, None))
    return result


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.query:
        query = args.query
    elif not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not query:
        print("[ERROR] Empty query.", file=sys.stderr)
        sys.exit(1)

    pattern = args.pattern

    if pattern == "auto":
        results = pattern_auto(query, args.notebook_id)

    elif pattern == "fan-out":
        agents = _parse_agents(args.agents)
        if args.verbose:
            print(f"[Orchestrator] Fan-out to {len(agents)} agents: {agents}", file=sys.stderr)
        results = pattern_fan_out(query, agents, args.notebook_id)

    elif pattern == "retrieve-reason":
        results = pattern_retrieve_then_reason(
            retrieval_query=query,
            reasoning_prompt_template=(
                "Based on this retrieved information:\n\n{context}\n\n"
                "Now answer the original question thoroughly: " + query
            ),
            claude_model=args.model,
            notebook_id=args.notebook_id,
        )

    elif pattern == "research-synthesize":
        results = pattern_gemini_then_claude(
            research_query=query,
            synthesis_template=(
                "Research context from Gemini:\n\n{context}\n\n"
                "Now synthesize and provide a comprehensive response to: " + query
            ),
            claude_model=args.model,
        )

    elif pattern == "pipeline":
        # For pipeline, treat query as step 1; user can chain via script
        results = pattern_pipeline([query])

    else:
        results = pattern_auto(query)

    print(format_results(results, "json" if args.json else "text"))


if __name__ == "__main__":
    main()
