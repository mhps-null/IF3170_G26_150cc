from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import random
import copy
import json


@dataclass
class Package:
    id: str
    w: int
    l: int
    h: int
    value: int
    weight: int
    is_fragile: bool
    eta: int

@dataclass
class Truck:
    w: int
    l: int
    h: int
    maxCapacity: int
    id: str = "T1"


@dataclass
class Fleet:
    """Satu atau beberapa truk. Satu truk tetap dinyatakan sebagai fleet."""

    trucks: Dict[str, Truck]

    def __post_init__(self):
        if not self.trucks:
            raise ValueError("Fleet harus berisi minimal satu truk.")

    @classmethod
    def from_list(cls, trucks: List[Truck]) -> "Fleet":
        ids = [truck.id for truck in trucks]
        if len(ids) != len(set(ids)):
            raise ValueError("ID truk dalam satu fleet harus unik.")
        return cls({truck.id: truck for truck in trucks})

    def ids(self) -> List[str]:
        return list(self.trucks)

    def truck_for(self, pos: "PackagePlacement") -> Optional[Truck]:
        """Truk pemilik sebuah penempatan. Fleet satu truk boleh tanpa truck_id."""
        if pos.truck_id is not None:
            return self.trucks.get(pos.truck_id)
        if len(self.trucks) == 1:
            return next(iter(self.trucks.values()))
        return None

def get_90deg_rotations(orientation: Tuple[str, str, str]) -> List[Tuple[str, str, str]]:
    """
    Generate 3 orientations resulting from a 90-degree rotation around a single axis (x, y, or z).
    """
    ox, oy, oz = orientation
    return [
        (oy, ox, oz),  # z-axis
        (ox, oz, oy),  # x-axis
        (oz, oy, ox),  # y-axis
    ]

@dataclass
class PackagePlacement:
    """Class to store coordinate and orientation of a single package inside a truck"""
    x: int
    y: int
    z: int
    orientation: Tuple[str, str, str]
    truck_id: Optional[str] = None 

    def get_effective_dimensions(self, pkg: Package) -> Tuple[int, int, int]:
        dims = {'w': pkg.w, 'l': pkg.l, 'h': pkg.h}
        eff_x = dims[self.orientation[0]]
        eff_y = dims[self.orientation[1]]
        eff_z = dims[self.orientation[2]]
        return eff_x, eff_y, eff_z

@dataclass
class State:
    """Class for each state condition of the truck at a certain time"""
    
    # Dictionary for package_id -> its placement
    placements: Dict[str, Optional[PackagePlacement]]
    
    def copy_state(self) -> 'State':
        return State(placements={
            pkg_id: copy.copy(placement) if placement is not None else None
            for pkg_id, placement in self.placements.items()
        })
        
    # Objective Function
    def get_objective_value(self, package_catalog: Dict[str, Package]) -> int:
        """Assumption: Only called on a valid state (is_valid() == True)"""
        total = 0
        for pkg_id, placement in self.placements.items():
            if placement is not None:
                total += package_catalog[pkg_id].value
        return total
    
    def _boxes_in(self, fleet: Fleet, package_catalog: Dict[str, Package]):
        """Kelompokkan paket yang sudah dimuat menurut truk. None jika ada truck_id asing."""
        grouped = {truck_id: [] for truck_id in fleet.trucks}
        for pkg_id, pos in self.placements.items():
            if pos is None:
                continue
            truck = fleet.truck_for(pos)
            if truck is None:
                return None
            pkg = package_catalog[pkg_id]
            eff_x, eff_y, eff_z = pos.get_effective_dimensions(pkg)
            grouped[truck.id].append({
                'id': pkg_id,
                'x1': pos.x, 'x2': pos.x + eff_x,
                'y1': pos.y, 'y2': pos.y + eff_y,
                'z1': pos.z, 'z2': pos.z + eff_z,
                'is_fragile': pkg.is_fragile,
                'weight': pkg.weight,
            })
        return grouped

    def _support_levels(self, fleet: Fleet, package_catalog: Dict[str, Package], truck_id: str) -> List[int]:
        truck = fleet.trucks[truck_id]
        levels = {0}
        for pkg_id, pos in self.placements.items():
            if pos is None:
                continue
            owner = fleet.truck_for(pos)
            if owner is None or owner.id != truck_id:
                continue
            _, _, eff_z = pos.get_effective_dimensions(package_catalog[pkg_id])
            if pos.z + eff_z <= truck.h:
                levels.add(pos.z + eff_z)
        return list(levels)

    # Constraint Checking
    def is_valid(self, fleet: Fleet, package_catalog: Dict[str, Package]) -> bool:
        # Representasi harus mencakup semua paket, tanpa ID asing.
        if set(self.placements) != set(package_catalog):
            return False
        
        for pkg_id, pos in self.placements.items():
            if pos is None:
                continue
            
            # Koordinat wajib bilangan bulat.
            if any(
                type(coord) is not int
                for coord in (pos.x, pos.y, pos.z)
            ):
                return False
        
            # Orientasi wajib permutasi valid dari w, l, h.
            try:
                orientation = tuple(pos.orientation)
            except TypeError:
                return False
        
            if (
                len(orientation) != 3
                or set(orientation) != {"w", "l", "h"}
            ):
                return False
    
        grouped = self._boxes_in(fleet, package_catalog)
        if grouped is None:
            return False

        for truck_id, placed in grouped.items():
            truck = fleet.trucks[truck_id]
            total_weight = sum(box['weight'] for box in placed)
            if total_weight > truck.maxCapacity:
                return False

            for i, p1 in enumerate(placed):
                if p1['x1'] < 0 or p1['x2'] > truck.w: return False
                if p1['y1'] < 0 or p1['y2'] > truck.l: return False
                if p1['z1'] < 0 or p1['z2'] > truck.h: return False

                for j in range(i + 1, len(placed)):
                    p2 = placed[j]
                    overlap_x = max(p1['x1'], p2['x1']) < min(p1['x2'], p2['x2'])
                    overlap_y = max(p1['y1'], p2['y1']) < min(p1['y2'], p2['y2'])
                    overlap_z = max(p1['z1'], p2['z1']) < min(p1['z2'], p2['z2'])
                    if overlap_x and overlap_y and overlap_z:
                        return False

                if p1['z1'] > 0:
                    has_valid_support = False
                    for p2 in placed:
                        if p1['id'] == p2['id'] or p2['z2'] != p1['z1']:
                            continue
                        overlap_x = max(p1['x1'], p2['x1']) < min(p1['x2'], p2['x2'])
                        overlap_y = max(p1['y1'], p2['y1']) < min(p1['y2'], p2['y2'])
                        if overlap_x and overlap_y:
                            if p2['is_fragile']:
                                return False
                            has_valid_support = True
                    if not has_valid_support:
                        return False

        return True
    
    def _place(self, x, y, z, orientation, truck_id: str) -> PackagePlacement:
        return PackagePlacement(x=x, y=y, z=z, orientation=orientation, truck_id=truck_id)

    # Neighbor Generation
    def generate_neighbors(
        self,
        fleet: Fleet,
        package_catalog: Dict[str, Package],
        max_shift: int = 2,
        sample_size: int = None,
        insert_tries: int = 50,
        max_sample_attempts: int = 100
    ) -> List['State']:
        """
        if `sample_size` is given (Stochastic HC), samples actions randomly,
        otherwise (Steepest Ascent / Sideways Move), exhaustively enumerates all swaps, moves,
        single-axis 90° rotations, and up to `insert_tries` insert candidates per outside package.
        A fleet of several trucks also samples a transfer into another truck.
        """
        keys = list(self.placements.keys())
        inside_keys = [k for k in keys if self.placements[k] is not None]
        outside_keys = [k for k in keys if self.placements[k] is None]
        truck_ids = fleet.ids()

        possible_orientations = [
            ('w', 'l', 'h'), ('w', 'h', 'l'),
            ('l', 'w', 'h'), ('l', 'h', 'w'),
            ('h', 'w', 'l'), ('h', 'l', 'w')
        ]

        def owner_of(pkg_id: str) -> Optional[Truck]:
            pos = self.placements[pkg_id]
            if pos is None:
                return None
            return fleet.truck_for(pos)

        def random_slot(truck: Truck, pkg: Package, orientation):
            ex, ey, ez = PackagePlacement(0, 0, 0, orientation).get_effective_dimensions(pkg)
            if ex > truck.w or ey > truck.l or ez > truck.h:
                return None
            levels = self._support_levels(fleet, package_catalog, truck.id)
            return (
                random.randint(0, truck.w - ex),
                random.randint(0, truck.l - ey),
                random.choice(levels),
            )

        # Random sampling (for Stochastic HC and GA mutation)
        if sample_size is not None:
            available_actions = []
            if len(keys) >= 2 and not (len(inside_keys) == 0 and len(outside_keys) >= 2):
                available_actions.append('swap')
            if inside_keys:
                available_actions.append('move')
                available_actions.append('rotate')
                if len(truck_ids) > 1:
                    available_actions.append('transfer')
            if outside_keys:
                available_actions.append('insert')

            if not available_actions:
                return []

            neighbors = []
            attempts = 0
            while len(neighbors) < sample_size and attempts < max_sample_attempts:
                attempts += 1
                action = random.choice(available_actions)
                new_p = self.copy_state().placements

                if action == 'swap':
                    p1, p2 = random.sample(keys, 2)
                    if new_p[p1] is None and new_p[p2] is None:
                        continue
                    new_p[p1], new_p[p2] = new_p[p2], new_p[p1]

                elif action == 'move':
                    pkg_id = random.choice(inside_keys)
                    pos = new_p[pkg_id]
                    truck = owner_of(pkg_id)
                    if truck is None:
                        continue
                    pkg = package_catalog[pkg_id]
                    eff_x, eff_y, _ = pos.get_effective_dimensions(pkg)
                    max_x = max(0, truck.w - eff_x)
                    max_y = max(0, truck.l - eff_y)
                    nx = max(0, min(max_x, pos.x + random.randint(-max_shift, max_shift)))
                    ny = max(0, min(max_y, pos.y + random.randint(-max_shift, max_shift)))
                    nz = random.choice(self._support_levels(fleet, package_catalog, truck.id))
                    if (nx, ny, nz) == (pos.x, pos.y, pos.z):
                        continue
                    new_p[pkg_id] = self._place(nx, ny, nz, pos.orientation, truck.id)

                elif action == 'rotate':
                    pkg_id = random.choice(inside_keys)
                    pos = new_p[pkg_id]
                    truck = owner_of(pkg_id)
                    if truck is None:
                        continue
                    ori = random.choice(get_90deg_rotations(pos.orientation))
                    new_p[pkg_id] = self._place(pos.x, pos.y, pos.z, ori, truck.id)

                elif action == 'insert':
                    pkg_id = random.choice(outside_keys)
                    truck = fleet.trucks[random.choice(truck_ids)]
                    ori = random.choice(possible_orientations)
                    slot = random_slot(truck, package_catalog[pkg_id], ori)
                    if slot is None:
                        continue
                    nx, ny, nz = slot
                    new_p[pkg_id] = self._place(nx, ny, nz, ori, truck.id)

                else:
                    pkg_id = random.choice(inside_keys)
                    origin = owner_of(pkg_id)
                    if origin is None:
                        continue
                    destinations = [tid for tid in truck_ids if tid != origin.id]
                    truck = fleet.trucks[random.choice(destinations)]
                    ori = random.choice(possible_orientations)
                    slot = random_slot(truck, package_catalog[pkg_id], ori)
                    if slot is None:
                        continue
                    nx, ny, nz = slot
                    new_p[pkg_id] = self._place(nx, ny, nz, ori, truck.id)

                candidate = State(placements=new_p)
                if candidate.is_valid(fleet, package_catalog):
                    neighbors.append(candidate)

            return neighbors

        # Exhaustive/semi-exhaustive neighborhood (for Steepest & Sideways)
        candidates = []

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                p1, p2 = keys[i], keys[j]
                if self.placements[p1] is None and self.placements[p2] is None:
                    continue
                candidates.append(('swap', p1, p2))

        for pkg_id in inside_keys:
            pos = self.placements[pkg_id]
            truck = owner_of(pkg_id)
            if truck is None:
                continue
            levels = self._support_levels(fleet, package_catalog, truck.id)
            for nx in range(max(0, pos.x - max_shift), min(truck.w, pos.x + max_shift + 1)):
                for ny in range(max(0, pos.y - max_shift), min(truck.l, pos.y + max_shift + 1)):
                    for nz in levels:
                        if nx != pos.x or ny != pos.y or nz != pos.z:
                            candidates.append(('move', pkg_id, nx, ny, nz, pos.orientation, truck.id))
            for ori in get_90deg_rotations(pos.orientation):
                candidates.append(('rotate', pkg_id, pos.x, pos.y, pos.z, ori, truck.id))

        def queue_loads(pkg_id: str, destinations: List[str], kind: str):
            pkg = package_catalog[pkg_id]
            seen = set()
            for truck_id in destinations:
                truck = fleet.trucks[truck_id]
                for _ in range(insert_tries):
                    ori = random.choice(possible_orientations)
                    slot = random_slot(truck, pkg, ori)
                    if slot is None:
                        continue
                    key = (pkg_id, truck_id, slot, ori)
                    if key in seen:
                        continue
                    seen.add(key)
                    nx, ny, nz = slot
                    candidates.append((kind, pkg_id, nx, ny, nz, ori, truck_id))

        for pkg_id in outside_keys:
            queue_loads(pkg_id, truck_ids, 'insert')
        if len(truck_ids) > 1:
            for pkg_id in inside_keys:
                origin = owner_of(pkg_id)
                if origin is None:
                    continue
                queue_loads(pkg_id, [tid for tid in truck_ids if tid != origin.id], 'transfer')

        neighbors = []
        for instruction in candidates:
            new_p = self.copy_state().placements
            if instruction[0] == 'swap':
                _, p1, p2 = instruction
                new_p[p1], new_p[p2] = new_p[p2], new_p[p1]
            else:
                _, pkg_id, x, y, z, ori, truck_id = instruction
                new_p[pkg_id] = self._place(x, y, z, ori, truck_id)
            new_state = State(placements=new_p)
            if new_state.is_valid(fleet, package_catalog):
                neighbors.append(new_state)
        return neighbors

def generate_random_state(fleet: Fleet, package_catalog: Dict[str, Package]) -> State:
    """Random initial state. Setiap paket dicoba ke lantai salah satu truk."""
    placements = {pkg_id: None for pkg_id in package_catalog}
    initial_state = State(placements=placements)

    all_pkg_ids = list(package_catalog.keys())
    random.shuffle(all_pkg_ids)
    possible_orientations = [
        ('w', 'l', 'h'), ('w', 'h', 'l'),
        ('l', 'w', 'h'), ('l', 'h', 'w'),
        ('h', 'w', 'l'), ('h', 'l', 'w')
    ]

    for pkg_id in all_pkg_ids:
        pkg = package_catalog[pkg_id]
        truck_order = fleet.ids()
        random.shuffle(truck_order)
        for truck_id in truck_order:
            truck = fleet.trucks[truck_id]
            random_ori = random.choice(possible_orientations)
            eff_x, eff_y, eff_z = PackagePlacement(0, 0, 0, random_ori).get_effective_dimensions(pkg)
            if eff_x > truck.w or eff_y > truck.l or eff_z > truck.h:
                continue
            test_placement = PackagePlacement(
                x=random.randint(0, truck.w - eff_x),
                y=random.randint(0, truck.l - eff_y),
                z=0,
                orientation=random_ori,
                truck_id=truck_id,
            )
            initial_state.placements[pkg_id] = test_placement
            if initial_state.is_valid(fleet, package_catalog):
                break
            initial_state.placements[pkg_id] = None

    return initial_state


def _truck_from_data(data: dict, index: int) -> Truck:
    return Truck(
        id=str(data.get("id", f"T{index}")),
        w=data["w"],
        l=data["l"],
        h=data["h"],
        maxCapacity=data["maxCapacity"],
    )


def parse_input(filepath: str) -> Tuple[Fleet, Dict[str, Package]]:
    """
    Satu truk:
        {"truck": {"w": 10, "l": 20, "h": 10, "maxCapacity": 100}, "packages": [...]}
    Beberapa truk:
        {"trucks": [{"id": "T1", "w": 10, "l": 20, "h": 5, "maxCapacity": 500}, ...], "packages": [...]}
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    if "trucks" in data:
        trucks = [_truck_from_data(item, i + 1) for i, item in enumerate(data["trucks"])]
    elif "truck" in data:
        trucks = [_truck_from_data(data["truck"], 1)]
    else:
        raise ValueError("Input harus memuat 'truck' atau 'trucks'.")

    catalog = {}
    for p_data in data['packages']:
        pkg = Package(
            id=p_data['id'],
            w=p_data['w'],
            l=p_data['l'],
            h=p_data['h'],
            value=p_data['value'],
            weight=p_data['weight'],
            is_fragile=p_data['is_fragile'],
            eta=p_data.get('eta', 0)
        )
        catalog[pkg.id] = pkg

    return Fleet.from_list(trucks), catalog

