"""
Milestone 8.3 — Distributed Swarm Reasoning.

If the local Aeon has no rule for a given fact, it queries the swarm
via the Registry Server (registry/src/main.rs).

Flow:
  1. ReasoningEngine cannot deduce anything for `fact_key`.
  2. RemoteQuery asks the Registry: "does anyone have rules for this fact?"
  3. Peer nodes respond with matching WisdomRules.
  4. RemoteQuery returns the best candidate rule (highest vote score).
  5. That rule passes through LLMGuard before being assimilated locally.
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

sys.path.append(str(Path(__file__).parent.parent))

REGISTRY_URL = "http://localhost:54445"  # Registry server port


@dataclass
class RemoteRule:
    """Candidate rule received from the swarm."""
    rule_id: str
    creator_node: str
    rule_data: dict
    votes: int


@dataclass
class QueryResult:
    found: bool
    rule: Optional[RemoteRule] = None
    error: Optional[str] = None


class RemoteQuery:
    """
    Queries the swarm when the local engine cannot deduce
    anything about a given structured fact.
    """

    def __init__(self, node_id: str, registry_url: str = REGISTRY_URL):
        self.node_id = node_id
        self.registry_url = registry_url

    def query_swarm(self, fact_key: str, context: dict | None = None) -> QueryResult:
        """
        Asks the swarm: "who can reason about `fact_key`?"
        Returns the highest-voted rule that mentions that fact in its conditions.
        """
        print(f"📡 [REMOTE QUERY] Node '{self.node_id}' asking swarm about fact: '{fact_key}'")
        try:
            resp = requests.get(
                f"{self.registry_url}/wisdom",
                timeout=5,
            )
            if resp.status_code != 200:
                return QueryResult(found=False, error=f"Registry returned {resp.status_code}")

            rules: list[dict] = resp.json()
            candidates = [r for r in rules if self._rule_covers_fact(r, fact_key)]

            if not candidates:
                print(f"   ↳ No peers have rules for '{fact_key}'")
                return QueryResult(found=False)

            # Select the rule with the most community votes
            best = max(candidates, key=lambda r: r.get("votes", 0))
            result = RemoteRule(
                rule_id=best.get("id", "unknown"),
                creator_node=best.get("creator_node", "unknown"),
                rule_data=best.get("rule_data", {}),
                votes=best.get("votes", 0),
            )
            print(f"   ↳ Best candidate: '{result.rule_data.get('name', '?')}' "
                  f"from '{result.creator_node}' ({result.votes} votes)")
            return QueryResult(found=True, rule=result)

        except requests.exceptions.ConnectionError:
            # Registry unavailable — silent failure, system continues locally
            print(f"   ↳ Registry offline. Continuing with local reasoning only.")
            return QueryResult(found=False, error="registry_offline")
        except Exception as e:
            return QueryResult(found=False, error=str(e))

    def _rule_covers_fact(self, raw_rule: dict, fact_key: str) -> bool:
        """Returns True if a WisdomRule from the registry covers the target fact_key."""
        rule_data = raw_rule.get("rule_data", {})
        conditions = rule_data.get("conditions", [])
        return any(c.get("fact_key") == fact_key for c in conditions)


if __name__ == "__main__":
    rq = RemoteQuery("ZANA_LOCAL_TEST")
    result = rq.query_swarm("machine_health_avg", context={"value": 0.3})
    if result.found and result.rule:
        print(f"\n✅ Swarm returned: {result.rule.rule_data.get('name')}")
    else:
        print(f"\n⚠️  No swarm result: {result.error}")
