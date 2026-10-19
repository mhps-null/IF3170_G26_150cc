from typing import Callable, Dict
from src.foundation import Package, State, Truck

ObjectiveFn = Callable[[State], float]


def make_base_objective(catalog: Dict[str, Package]) -> ObjectiveFn:
    """Objective dasar: total value paket di dalam truk."""
    return lambda s: s.get_objective_value(catalog)

def make_violation_objective(truck: Truck, catalog: Dict[str, Package]) -> ObjectiveFn:
    """Fitness function computed with the formula:

    fitness = base_objective - violation_penalty * violation_number

    where:
    - base_objective is the fitness value computed from the base objective function
    - violation_penalty is the penalty for each violation, set to be the sum of the value of all the packages + 1
    - violation_number is the number of violations in the state
    """
    violation_penalty = sum(pkg.value for pkg in catalog.values()) + 1
    truck_w, truck_l, truck_h = truck.w, truck.l, truck.h
    max_capacity = truck.maxCapacity

    def axis_length(pkg: Package, axis: str) -> int:
        if axis == "w":
            return pkg.w
        if axis == "l":
            return pkg.l
        return pkg.h

    def objective(state: State) -> float:
        # id, x1, y1, z1, x2, y2, z2, is_fragile
        placed = []
        by_top = {}
        total_weight = 0
        total_value = 0
        for pkg_id, pos in state.placements.items():
            if pos is None:
                continue
            pkg = catalog[pkg_id]
            ori = pos.orientation
            x1, y1, z1 = pos.x, pos.y, pos.z
            x2 = x1 + axis_length(pkg, ori[0])
            y2 = y1 + axis_length(pkg, ori[1])
            z2 = z1 + axis_length(pkg, ori[2])
            box = (pkg_id, x1, y1, z1, x2, y2, z2, pkg.is_fragile)
            placed.append(box)
            by_top.setdefault(z2, []).append(box)
            total_weight += pkg.weight
            total_value += pkg.value

        violation = float(max(0, total_weight - max_capacity))
        for i, p1 in enumerate(placed):
            _, x1, y1, z1, x2, y2, z2, _ = p1
            inside_x = max(0, min(x2, truck_w) - max(x1, 0))
            inside_y = max(0, min(y2, truck_l) - max(y1, 0))
            inside_z = max(0, min(z2, truck_h) - max(z1, 0))
            violation += (x2 - x1) * (y2 - y1) * (z2 - z1) - inside_x * inside_y * inside_z

            for p2 in placed[i + 1:]:
                overlap_z = min(z2, p2[6]) - max(z1, p2[3])
                if overlap_z <= 0:
                    continue
                overlap_x = min(x2, p2[4]) - max(x1, p2[1])
                if overlap_x <= 0:
                    continue
                overlap_y = min(y2, p2[5]) - max(y1, p2[2])
                if overlap_y <= 0:
                    continue
                violation += overlap_x * overlap_y * overlap_z

            if z1 <= 0:
                continue
            has_support = False
            for p2 in by_top.get(z1, ()):
                if p1[0] == p2[0]:
                    continue
                contact_x = min(x2, p2[4]) - max(x1, p2[1])
                if contact_x <= 0:
                    continue
                contact_y = min(y2, p2[5]) - max(y1, p2[2])
                if contact_y <= 0:
                    continue
                has_support = True
                if p2[7]:
                    violation += contact_x * contact_y
            if not has_support:
                violation += (x2 - x1) * (y2 - y1)

        return float(total_value) - violation_penalty * violation

    return objective