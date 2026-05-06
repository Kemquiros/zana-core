import datetime
import os
import sys

# Add zana-core to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from economy.inventory import InventoryService
from economy.models import Weapon


def test_durability_decay():
    service = InventoryService()
    
    # Create a weapon with 100 durability
    # Interaction was 24 hours ago.
    one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    weapon = Weapon(
        name="Steel Sword",
        durability=100.0,
        last_interaction=one_day_ago
    )
    
    # Process decay
    service.process_decay(weapon)
    
    # We expect some decay. 
    assert weapon.durability < 100.0
    assert weapon.durability >= 0

def test_no_decay_on_recent_interaction():
    service = InventoryService()
    
    # Interaction just now
    now = datetime.datetime.now()
    weapon = Weapon(
        name="New Dagger",
        durability=100.0,
        last_interaction=now
    )
    
    service.process_decay(weapon, now=now)
    
    assert weapon.durability == 100.0
