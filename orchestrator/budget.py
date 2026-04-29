"""
Iteration Budget — prevents runaway LangGraph loops and uncontrolled API spend.

Design principles (from Hermes Agent):
  - Separate limits per agent tier (orchestrator vs swarm Aeon)
  - Warn at 80% utilization before hard stop
  - Refundable operations don't consume budget (cheap ops like memory reads)
  - budget_exhausted recorded in trajectory for training signal quality

Configuration via environment variables:
  ZANA_MAX_ITERATIONS        — orchestrator budget (default: 10)
  ZANA_SWARM_MAX_ITERATIONS  — per-Aeon swarm budget  (default: 5)
"""
import os
from dataclasses import dataclass, field
from typing import FrozenSet


# Operations that are too cheap to count against the budget.
# Add op names here as new tools are introduced.
REFUNDABLE_OPS: FrozenSet[str] = frozenset({
    "memory_read",
    "semantic_search",
    "context_recall",
})


@dataclass(frozen=True)
class BudgetConfig:
    """Immutable budget configuration. One instance per process, loaded from env."""

    orchestrator: int = 10
    swarm_aeon: int = 5
    warn_ratio: float = 0.8       # log WARNING at this fraction of budget
    refundable: FrozenSet[str] = field(default_factory=lambda: REFUNDABLE_OPS)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "BudgetConfig":
        return cls(
            orchestrator=int(os.getenv("ZANA_MAX_ITERATIONS", "10")),
            swarm_aeon=int(os.getenv("ZANA_SWARM_MAX_ITERATIONS", "5")),
        )

    # ------------------------------------------------------------------
    # Query helpers (pure functions — no mutable state)
    # ------------------------------------------------------------------

    def limit(self, tier: str = "orchestrator") -> int:
        return self.orchestrator if tier == "orchestrator" else self.swarm_aeon

    def is_exhausted(self, iterations: int, tier: str = "orchestrator") -> bool:
        return iterations >= self.limit(tier)

    def should_warn(self, iterations: int, tier: str = "orchestrator") -> bool:
        threshold = int(self.limit(tier) * self.warn_ratio)
        return iterations == threshold

    def is_refundable(self, op: str) -> bool:
        return op in self.refundable

    def remaining(self, iterations: int, tier: str = "orchestrator") -> int:
        return max(0, self.limit(tier) - iterations)

    def utilization(self, iterations: int, tier: str = "orchestrator") -> float:
        return min(1.0, iterations / self.limit(tier))

    def status_line(self, iterations: int, tier: str = "orchestrator") -> str:
        rem = self.remaining(iterations, tier)
        pct = int(self.utilization(iterations, tier) * 100)
        return f"[Budget:{tier}] {iterations}/{self.limit(tier)} ({pct}%) — {rem} remaining"


# Module-level singleton — loaded once at import time.
BUDGET = BudgetConfig.from_env()


if __name__ == "__main__":
    cfg = BudgetConfig(orchestrator=10, swarm_aeon=5)

    assert not cfg.is_exhausted(0)
    assert not cfg.is_exhausted(9)
    assert cfg.is_exhausted(10)
    assert cfg.is_exhausted(11)
    print("is_exhausted: OK")

    assert not cfg.should_warn(7)
    assert cfg.should_warn(8)   # 80% of 10
    assert not cfg.should_warn(9)
    print("should_warn (80%): OK")

    assert cfg.is_refundable("memory_read")
    assert not cfg.is_refundable("executor_step")
    print("refundable ops: OK")

    assert cfg.remaining(3) == 7
    assert cfg.remaining(10) == 0
    print("remaining: OK")

    assert abs(cfg.utilization(5) - 0.5) < 1e-9
    assert cfg.utilization(10) == 1.0
    print("utilization: OK")

    print(cfg.status_line(7))
    print(cfg.status_line(3, tier="swarm_aeon"))

    swarm = BudgetConfig(orchestrator=10, swarm_aeon=5)
    assert swarm.is_exhausted(5, tier="swarm_aeon")
    assert not swarm.is_exhausted(4, tier="swarm_aeon")
    print("swarm tier: OK")

    from_env = BudgetConfig.from_env()
    print(f"from_env: orchestrator={from_env.orchestrator}, swarm={from_env.swarm_aeon}")

    print("\nBudgetConfig: all tests passed.")
