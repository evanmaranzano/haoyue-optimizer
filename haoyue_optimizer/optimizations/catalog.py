from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.optimizations import display
from haoyue_optimizer.optimizations import disk
from haoyue_optimizer.optimizations import experimental
from haoyue_optimizer.optimizations import gaming
from haoyue_optimizer.optimizations import gpu
from haoyue_optimizer.optimizations import input as input_mod
from haoyue_optimizer.optimizations import memory
from haoyue_optimizer.optimizations import network
from haoyue_optimizer.optimizations import power
from haoyue_optimizer.optimizations import privacy
from haoyue_optimizer.optimizations import scheduling
from haoyue_optimizer.optimizations import scheduled_tasks
from haoyue_optimizer.optimizations import services
from haoyue_optimizer.optimizations import system


def get_optimizations() -> list[Optimization]:
    items: list[Optimization] = []
    items.extend(gaming.get_optimizations())
    items.extend(privacy.get_optimizations())
    items.extend(services.get_optimizations())
    items.extend(input_mod.get_optimizations())
    items.extend(display.get_optimizations())
    items.extend(system.get_optimizations())
    items.extend(power.get_optimizations())
    items.extend(scheduled_tasks.get_optimizations())
    items.extend(experimental.get_optimizations())
    items.extend(network.get_optimizations())
    items.extend(scheduling.get_optimizations())
    items.extend(gpu.get_optimizations())
    items.extend(memory.get_optimizations())
    items.extend(disk.get_optimizations())
    return items
