from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class GraphState:
    node: str
    steps: int = 0
    done: bool = False


def run_state_graph(
    *,
    start_node: str,
    max_steps: int,
    run_node: Callable[[GraphState], str | None],
) -> None:
    state = GraphState(node=start_node)
    while not state.done:
        if state.steps >= max_steps:
            raise RuntimeError(f"State graph exceeded max_steps={max_steps}")
        next_node = run_node(state)
        state.steps += 1
        if next_node is None:
            state.done = True
        else:
            state.node = next_node
