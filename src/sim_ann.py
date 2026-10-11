"""
Masalahnya MAKSIMASI, jadi:
    dE = objective(neighbor) - objective(current)
    dE >= 0 -> selalu diterima
    dE <  0 -> diterima dengan probabilitas e^(dE / T)
"""
import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from foundation import Package, PackagePlacement, State, Truck, generate_random_state

ORIENTATIONS = [
    ('w', 'l', 'h'), ('w', 'h', 'l'),
    ('l', 'w', 'h'), ('l', 'h', 'w'),
    ('h', 'w', 'l'), ('h', 'l', 'w'),
]
MOVE_TYPES = ("swap", "move", "rotate", "insert")

ObjectiveFn = Callable[[State], float]


@dataclass
class SAResult:
    start_state: State
    final_state: State
    best_state: State
    final_value: float
    final_base_value: int
    best_value: float
    iterations: int
    duration: float
    history: List[float]
    prob_history: List[Tuple[int, float]]
    temp_history: List[float]
    stuck_count: int
    accepted_worse: int
    no_neighbor_count: int


def suggest_t0(catalog: Dict[str, Package]) -> float:
    return sum(p.value for p in catalog.values()) / len(catalog)


def _support_levels(state: State, truck: Truck, catalog: Dict[str, Package], exclude: str = None) -> List[int]:
    levels = {0}
    for pid, pos in state.placements.items():
        if pos is None or pid == exclude:
            continue
        _, _, ez = pos.get_effective_dimensions(catalog[pid])
        if pos.z + ez < truck.h:
            levels.add(pos.z + ez)
    return list(levels)


def random_neighbor(state: State, truck: Truck, catalog: Dict[str, Package],
                    max_shift: int = 2, max_tries: int = 30) -> Optional[State]:
    # Ambil SATU neighbor valid secara acak
    ids = list(state.placements.keys())
    for _ in range(max_tries):
        kind = random.choice(MOVE_TYPES)
        new_p = state.copy_state().placements

        if kind == "swap":
            if len(ids) < 2:
                continue
            a, b = random.sample(ids, 2)
            if new_p[a] is None and new_p[b] is None:
                continue
            new_p[a], new_p[b] = new_p[b], new_p[a]

        elif kind == "move":
            inside = [i for i in ids if new_p[i] is not None]
            if not inside:
                continue
            pid = random.choice(inside)
            pos = new_p[pid]
            nx = pos.x + random.randint(-max_shift, max_shift)
            ny = pos.y + random.randint(-max_shift, max_shift)
            nz = random.choice(_support_levels(state, truck, catalog, exclude=pid))
            if (nx, ny, nz) == (pos.x, pos.y, pos.z):
                continue
            new_p[pid] = PackagePlacement(nx, ny, nz, pos.orientation)

        elif kind == "rotate":
            inside = [i for i in ids if new_p[i] is not None]
            if not inside:
                continue
            pid = random.choice(inside)
            pos = new_p[pid]
            ori = random.choice([o for o in ORIENTATIONS if o != pos.orientation])
            new_p[pid] = PackagePlacement(pos.x, pos.y, pos.z, ori)

        else:  # insert: paket di luar masuk ke truk
            outside = [i for i in ids if new_p[i] is None]
            if not outside:
                continue
            pid = random.choice(outside)
            ori = random.choice(ORIENTATIONS)
            ex, ey, ez = PackagePlacement(0, 0, 0, ori).get_effective_dimensions(catalog[pid])
            if ex > truck.w or ey > truck.l or ez > truck.h:
                continue
            nx = random.randint(0, truck.w - ex)
            ny = random.randint(0, truck.l - ey)
            nz = random.choice(_support_levels(state, truck, catalog))
            new_p[pid] = PackagePlacement(nx, ny, nz, ori)

        candidate = State(placements=new_p)
        if candidate.is_valid(truck, catalog):
            return candidate
    return None


class SimulatedAnnealing:
    def __init__(self, truck: Truck, catalog: Dict[str, Package], objective_fn: ObjectiveFn = None):
        self.truck = truck
        self.catalog = catalog
        # default: objective dasar (total value paket di dalam truk). Untuk bonus 1 berbeda
        self.objective_fn = objective_fn or (lambda s: s.get_objective_value(catalog))

    def run(self, initial_state: State = None, t0: float = None, alpha: float = 0.999,
            t_min: float = 0.1, max_iter: int = 20000, max_shift: int = 2) -> SAResult:
        """
        Definisi 'stuck': iterasi di mana neighbor yang LEBIH BURUK (dE < 0) ditolak,
        yaitu SA bertahan di state yang sama
        karena tidak ada jalan naik.
        Frekuensi = stuck_count / iterations.
        """
        start = time.perf_counter()
        current = initial_state if initial_state is not None else generate_random_state(self.truck, self.catalog)
        start_state = current.copy_state()
        cur_val = self.objective_fn(current)
        best_state, best_val = current.copy_state(), cur_val

        T = t0 if t0 is not None else suggest_t0(self.catalog)
        history = [cur_val]
        temp_history: List[float] = []
        prob_history: List[Tuple[int, float]] = []
        stuck = accepted_worse = no_neighbor = 0
        it = 0

        while it < max_iter and T > t_min:
            it += 1
            neighbor = random_neighbor(current, self.truck, self.catalog, max_shift=max_shift)

            if neighbor is None:
                no_neighbor += 1
            else:
                nb_val = self.objective_fn(neighbor)
                delta = nb_val - cur_val
                accept = delta >= 0
                if not accept:
                    p = math.exp(delta / T)
                    prob_history.append((it, p))
                    if random.random() < p:
                        accept = True
                        accepted_worse += 1
                    else:
                        stuck += 1
                if accept:
                    current, cur_val = neighbor, nb_val
                    if cur_val > best_val:
                        best_state, best_val = current.copy_state(), cur_val

            history.append(cur_val)
            temp_history.append(T)
            T *= alpha

        return SAResult(
            start_state=start_state, final_state=current, best_state=best_state,
            final_value=cur_val, final_base_value=current.get_objective_value(self.catalog),
            best_value=best_val, iterations=it, duration=time.perf_counter() - start,
            history=history, prob_history=prob_history, temp_history=temp_history,
            stuck_count=stuck, accepted_worse=accepted_worse, no_neighbor_count=no_neighbor,
        )