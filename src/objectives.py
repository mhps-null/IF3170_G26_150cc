# Bonus 1 : objective function alternatif
from typing import Callable, Dict
from foundation import Package, State

ObjectiveFn = Callable[[State], float]


def make_base_objective(catalog: Dict[str, Package]) -> ObjectiveFn:
    """Objective dasar: total value paket di dalam truk."""
    return lambda s: s.get_objective_value(catalog)


def make_eta_weighted_objective(catalog: Dict[str, Package]) -> ObjectiveFn:
    """
    Memprioritaskan paket mendesak: sum( value * (1 + 1/(1+ETA)) ).
    ETA kecil (hampir sampai) -> bobot mendekati 2x; ETA besar -> mendekati 1x.
    """
    def objective(state: State) -> float:
        total = 0.0
        for pid, pos in state.placements.items():
            if pos is not None:
                pkg = catalog[pid]
                total += pkg.value * (1 + 1 / (1 + pkg.eta))
        return total
    return objective


def make_light_objective(catalog: Dict[str, Package], lam: float = 0.1) -> ObjectiveFn:
    """
    Value dikurangi penalti berat kecil: sum( value - lam * weight ).
    Di antara solusi dengan value sama, memilih yang lebih ringan. Efek samping
    penting: memecah plateau (banyak move ber-dE = 0 pada objective dasar).
    """
    def objective(state: State) -> float:
        total = 0.0
        for pid, pos in state.placements.items():
            if pos is not None:
                pkg = catalog[pid]
                total += pkg.value - lam * pkg.weight
        return total
    return objective


OBJECTIVES = {
    "base": make_base_objective,
    "eta": make_eta_weighted_objective,
    "light": make_light_objective,
}