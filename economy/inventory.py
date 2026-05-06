import datetime
from economy.models import SemanticItem

class InventoryService:
    def __init__(self, decay_rate: float = 1.0):
        # Default decay rate: 1.0 durability points per hour
        self.decay_rate = decay_rate

    def process_decay(self, item: SemanticItem, now: datetime.datetime = None):
        if now is None:
            now = datetime.datetime.now()
        time_diff = now - item.last_interaction
        hours_passed = time_diff.total_seconds() / 3600
        
        if hours_passed > 0:
            # Simple linear decay
            decay_amount = self.decay_rate * hours_passed
            item.durability = max(0.0, item.durability - decay_amount)
