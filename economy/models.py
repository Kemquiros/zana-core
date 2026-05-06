from dataclasses import dataclass
import datetime

@dataclass
class SemanticItem:
    name: str
    durability: float
    last_interaction: datetime.datetime

@dataclass
class Relic(SemanticItem):
    pass

@dataclass
class Weapon(SemanticItem):
    pass

@dataclass
class Armor(SemanticItem):
    pass
