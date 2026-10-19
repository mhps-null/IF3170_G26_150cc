"""
Simulated Annealing untuk maksimisasi objective.

dE = objective(neighbor) - objective(current)

dE >= 0 : selalu diterima
dE < 0  : diterima dengan probabilitas exp(dE / T)

Metrik:
- non_improving_iteration_count:
  Iterasi ketika tidak ada neighbor valid atau objective neighbor
  tidak lebih tinggi daripada objective state saat ini.
- rejected_worse_count:
  Jumlah neighbor dengan objective lebih rendah yang ditolak.
- accepted_worse:
  Jumlah neighbor dengan objective lebih rendah yang diterima.
- no_neighbor_count:
  Jumlah iterasi ketika tidak ada neighbor valid yang berhasil dibuat.

non_improving_iteration_count bukan bukti bahwa state merupakan
local optimum. Algoritma hanya mengevaluasi satu neighbor acak
pada setiap iterasi.
"""

import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from src.foundation import (
    Package,
    PackagePlacement,
    State,
    Truck,
    generate_random_state,
    get_90deg_rotations,
)


ORIENTATIONS = [
    ("w", "l", "h"),
    ("w", "h", "l"),
    ("l", "w", "h"),
    ("l", "h", "w"),
    ("h", "w", "l"),
    ("h", "l", "w"),
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

    non_improving_iteration_count: int
    rejected_worse_count: int
    accepted_worse: int
    no_neighbor_count: int


def suggest_t0(catalog: Dict[str, Package]) -> float:
    """Menggunakan rata-rata value paket sebagai temperatur awal."""
    if not catalog:
        raise ValueError("Catalog paket tidak boleh kosong.")

    return sum(p.value for p in catalog.values()) / len(catalog)


def _support_levels(
    state: State,
    truck: Truck,
    catalog: Dict[str, Package],
    exclude: Optional[str] = None,
) -> List[int]:
    """Mengembalikan ketinggian dasar truk dan permukaan paket."""
    levels = {0}

    for pid, pos in state.placements.items():
        if pos is None or pid == exclude:
            continue

        _, _, effective_height = pos.get_effective_dimensions(catalog[pid])
        top_z = pos.z + effective_height

        if top_z < truck.h:
            levels.add(top_z)

    return list(levels)


def random_neighbor(
    state: State,
    truck: Truck,
    catalog: Dict[str, Package],
    max_shift: int = 2,
    max_tries: int = 30,
) -> Optional[State]:
    """Menghasilkan satu neighbor valid secara acak."""

    ids = list(state.placements.keys())

    for _ in range(max_tries):
        kind = random.choice(MOVE_TYPES)
        new_placements = state.copy_state().placements

        if kind == "swap":
            if len(ids) < 2:
                continue

            a, b = random.sample(ids, 2)

            if new_placements[a] is None and new_placements[b] is None:
                continue

            new_placements[a], new_placements[b] = (
                new_placements[b],
                new_placements[a],
            )

        elif kind == "move":
            inside = [
                pid for pid in ids
                if new_placements[pid] is not None
            ]

            if not inside:
                continue

            pid = random.choice(inside)
            pos = new_placements[pid]

            nx = pos.x + random.randint(-max_shift, max_shift)
            ny = pos.y + random.randint(-max_shift, max_shift)

            nz = random.choice(
                _support_levels(
                    state, truck, catalog, exclude=pid
                )
            )

            if (nx, ny, nz) == (pos.x, pos.y, pos.z):
                continue

            new_placements[pid] = PackagePlacement(
                nx, ny, nz, pos.orientation
            )

        elif kind == "rotate":
            inside = [
                pid for pid in ids
                if new_placements[pid] is not None
            ]

            if not inside:
                continue

            pid = random.choice(inside)
            pos = new_placements[pid]

            # Hanya rotasi 90 derajat pada satu sumbu.
            possible_orientations = get_90deg_rotations(
                pos.orientation
            )

            if not possible_orientations:
                continue

            orientation = random.choice(possible_orientations)

            new_placements[pid] = PackagePlacement(
                pos.x,
                pos.y,
                pos.z,
                orientation,
            )

        else:
            # Insert: memindahkan paket dari luar ke dalam truk.
            outside = [
                pid for pid in ids
                if new_placements[pid] is None
            ]

            if not outside:
                continue

            pid = random.choice(outside)
            orientation = random.choice(ORIENTATIONS)

            ex, ey, ez = PackagePlacement(
                0, 0, 0, orientation
            ).get_effective_dimensions(catalog[pid])

            if ex > truck.w or ey > truck.l or ez > truck.h:
                continue

            nx = random.randint(0, truck.w - ex)
            ny = random.randint(0, truck.l - ey)

            nz = random.choice(
                _support_levels(state, truck, catalog)
            )

            new_placements[pid] = PackagePlacement(
                nx, ny, nz, orientation
            )

        candidate = State(placements=new_placements)

        # Seluruh constraint harus dipenuhi.
        if candidate.is_valid(truck, catalog):
            return candidate

    return None


class SimulatedAnnealing:
    def __init__(
        self,
        truck: Truck,
        catalog: Dict[str, Package],
        objective_fn: Optional[ObjectiveFn] = None,
    ):
        self.truck = truck
        self.catalog = catalog

        # Default: memaksimalkan total value paket di dalam truk.
        self.objective_fn = (
            objective_fn
            if objective_fn is not None
            else lambda state: state.get_objective_value(catalog)
        )

    def run(
        self,
        initial_state: Optional[State] = None,
        t0: Optional[float] = None,
        alpha: float = 0.999,
        t_min: float = 0.1,
        max_iter: int = 20000,
        max_shift: int = 2,
    ) -> SAResult:
        if not 0 < alpha < 1:
            raise ValueError("alpha harus berada di antara 0 dan 1.")

        if t_min < 0:
            raise ValueError("t_min tidak boleh negatif.")

        if max_iter < 0:
            raise ValueError("max_iter tidak boleh negatif.")

        if max_shift < 0:
            raise ValueError("max_shift tidak boleh negatif.")

        start_time = time.perf_counter()

        initial = (
            initial_state
            if initial_state is not None
            else generate_random_state(self.truck, self.catalog)
        )

        if not initial.is_valid(self.truck, self.catalog):
            raise ValueError("Initial state melanggar constraint.")

        current = initial.copy_state()
        start_state = current.copy_state()

        current_value = self.objective_fn(current)

        best_state = current.copy_state()
        best_value = current_value

        temperature = t0 if t0 is not None else suggest_t0(self.catalog)

        if temperature <= 0:
            raise ValueError("Temperatur awal harus lebih besar dari 0.")

        history = [current_value]
        temp_history: List[float] = []
        prob_history: List[Tuple[int, float]] = []

        non_improving = 0
        rejected_worse = 0
        accepted_worse = 0
        no_neighbor = 0

        iteration = 0

        while iteration < max_iter and temperature > t_min:
            iteration += 1

            neighbor = random_neighbor(
                current,
                self.truck,
                self.catalog,
                max_shift=max_shift,
            )

            if neighbor is None:
                no_neighbor += 1
                non_improving += 1

            else:
                neighbor_value = self.objective_fn(neighbor)
                delta = neighbor_value - current_value

                # Metrik ini mengukur kandidat yang tidak meningkatkan
                # objective terhadap state saat ini.
                if delta <= 0:
                    non_improving += 1

                accept = delta >= 0

                if delta < 0:
                    probability = math.exp(delta / temperature)
                    prob_history.append((iteration, probability))

                    if random.random() < probability:
                        accept = True
                        accepted_worse += 1
                    else:
                        rejected_worse += 1

                if accept:
                    current = neighbor
                    current_value = neighbor_value

                    if current_value > best_value:
                        best_state = current.copy_state()
                        best_value = current_value

            history.append(current_value)
            temp_history.append(temperature)

            temperature *= alpha

        duration = time.perf_counter() - start_time

        return SAResult(
            start_state=start_state,
            final_state=current,
            best_state=best_state,
            final_value=current_value,
            final_base_value=current.get_objective_value(self.catalog),
            best_value=best_value,
            iterations=iteration,
            duration=duration,
            history=history,
            prob_history=prob_history,
            temp_history=temp_history,
            non_improving_iteration_count=non_improving,
            rejected_worse_count=rejected_worse,
            accepted_worse=accepted_worse,
            no_neighbor_count=no_neighbor,
        )