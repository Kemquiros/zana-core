import random
import json
from typing import List, Dict, Any

class StrategyEvolution:
    """
    Tournament of Ideas: Distribution of XANA.
    Uses Evolutionary Algorithms to find the optimal deployment strategy.
    """
    def __init__(self):
        self.generation = 0
        self.population: List[Dict[str, Any]] = []
        self.criteria = ["Sovereignty", "Scalability", "Monetization", "Swarm_Resonance"]

    def seed_initial_population(self):
        """Generates 100 divergent initial ideas."""
        categories = ["Cloud/SaaS", "OpenSource", "Crypto/Web3", "Biological/Swarm", "Hardware/Physical", "Underground/P2P"]
        raw_ideas = [
            {"id": i, "name": f"Idea_{i}", "traits": {
                "access": random.choice(["Open", "Closed", "Gated", "Hybrid"]),
                "platform": random.choice(categories),
                "revenue": random.choice(["Subscription", "Donation", "Tokenomics", "Free", "Pay-per-Compute"]),
                "governance": random.choice(["John_Only", "DAO", "Meritocracy", "Autonomous"]),
                "risk_profile": random.uniform(0, 1)
            }, "fitness": 0}
            for i in range(100)
        ]
        self.population = raw_ideas

    def mutate(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Adds a random mutation to a strategy trait."""
        new_idea = json.loads(json.dumps(idea)) # Deep copy
        traits = list(new_idea["traits"].keys())
        trait_to_mutate = random.choice(traits)
        
        if trait_to_mutate == "access":
            new_idea["traits"][trait_to_mutate] = random.choice(["Open", "Closed", "Gated", "Hybrid"])
        elif trait_to_mutate == "platform":
            new_idea["traits"][trait_to_mutate] = random.choice(["Cloud/SaaS", "OpenSource", "Crypto/Web3", "Biological/Swarm", "Hardware/Physical"])
        elif trait_to_mutate == "revenue":
            new_idea["traits"][trait_to_mutate] = random.choice(["Subscription", "Donation", "Tokenomics", "Free", "Pay-per-Compute"])
        elif trait_to_mutate == "governance":
            new_idea["traits"][trait_to_mutate] = random.choice(["John_Only", "DAO", "Meritocracy", "Autonomous"])
        else:
            new_idea["traits"][trait_to_mutate] *= random.uniform(0.8, 1.2)
            
        return new_idea

    def crossover(self, parent_a: Dict[str, Any], parent_b: Dict[str, Any]) -> Dict[str, Any]:
        """Combines traits of two successful strategies."""
        child_traits = {}
        for key in parent_a["traits"]:
            child_traits[key] = random.choice([parent_a["traits"][key], parent_b["traits"][key]])
        return {"id": random.randint(1000, 9999), "name": "Hybrid_Strategy", "traits": child_traits, "fitness": 0}

    def evaluate_fitness(self, idea: Dict[str, Any]) -> float:
        """Score based on XANA's Constitutional Principles."""
        t = idea["traits"]
        score = 0
        
        # 1. Access: Hybrid is most versatile (Resonance)
        if t["access"] == "Hybrid": score += 25
        elif t["access"] == "Open": score += 15
        
        # 2. Platform: Web3/Crypto aligns with Swarm and A2A
        if t["platform"] == "Crypto/Web3": score += 20
        elif t["platform"] == "Cloud/SaaS": score += 15 # Good for John's revenue
        elif t["platform"] == "Biological/Swarm": score += 25 # High end-goal alignment
        
        # 3. Revenue: Tokenomics + Subscription crossover is strong
        if t["revenue"] == "Tokenomics": score += 20
        elif t["revenue"] == "Subscription": score += 15
        
        # 4. Governance: DAO/Autonomous supports the Hive Mind
        if t["governance"] == "DAO": score += 20
        elif t["governance"] == "Autonomous": score += 25
        elif t["governance"] == "John_Only": score += 10 # Initial control is good but not scalable
        
        # Balance Score
        return score + (random.random() * 5)

    def run_tournament(self):
        print(f"--- 🏆 XANA TOURNAMENT OF IDEAS: THE STRATEGY GENESIS ---")
        self.seed_initial_population()
        
        stages = [
            "PHASE 1: Seeding & Raw Expansion (100 Ideas)",
            "PHASE 2: Selective Mutation & Innovation",
            "PHASE 3: Architectural Crossover (DNA Mixing)",
            "PHASE 4: Final Selection & Convergence"
        ]
        
        for stage in stages:
            print(f"\n{stage}")
            # 1. Evaluate
            for p in self.population:
                p["fitness"] = self.evaluate_fitness(p)
            
            # 2. Sort & Select Top Survivors (50%)
            self.population = sorted(self.population, key=lambda x: x["fitness"], reverse=True)
            best_score = self.population[0]['fitness']
            self.population = self.population[:50]
            
            print(f"Survivors: {len(self.population)} | Peak Fitness: {best_score:.2f}")
            
            # 3. Refill population via Mutation & Crossover
            next_gen = []
            next_gen.extend(self.population) # Keep elites
            while len(next_gen) < 100:
                if random.random() < 0.2: # Mutation
                    next_gen.append(self.mutate(random.choice(self.population)))
                else: # Crossover
                    next_gen.append(self.crossover(random.choice(self.population), random.choice(self.population)))
            self.population = next_gen

        # Final Final Evaluation
        for p in self.population:
            p["fitness"] = self.evaluate_fitness(p)
        self.population = sorted(self.population, key=lambda x: x["fitness"], reverse=True)
        return self.population[:5]

if __name__ == "__main__":
    evolution = StrategyEvolution()
    winners = evolution.run_tournament()
    
    print("\n--- 🏁 THE SURVIVORS: TOP 5 DEPLOYMENT ARCHITECTURES ---")
    for i, w in enumerate(winners):
        print(f"\nRANK {i+1} [Fitness: {w['fitness']:.2f}]")
        print(json.dumps(w['traits'], indent=2))
