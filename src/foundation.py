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
    """Class to store coordinate and orientation of a single package inside the truck"""
    x: int
    y: int
    z: int
    orientation: Tuple[str, str, str] 

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
    
    # Constraint Checking
    def is_valid(self, truck: Truck, package_catalog: Dict[str, Package]) -> bool:
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
    
        placed = []
        total_weight = 0
        
        # Extract all package data inside the truck
        for pkg_id, pos in self.placements.items():
            if pos is not None:
                pkg = package_catalog[pkg_id]
                eff_x, eff_y, eff_z = pos.get_effective_dimensions(pkg)
                placed.append({
                    'id': pkg_id,
                    'x1': pos.x, 'x2': pos.x + eff_x,
                    'y1': pos.y, 'y2': pos.y + eff_y,
                    'z1': pos.z, 'z2': pos.z + eff_z,
                    'is_fragile': pkg.is_fragile
                })
                total_weight += pkg.weight
                
        # Check weight capacity
        if total_weight > truck.maxCapacity:
            return False
            
        for i, p1 in enumerate(placed):
            # Check truck boundaries (Out of bounds)
            if p1['x1'] < 0 or p1['x2'] > truck.w: return False
            if p1['y1'] < 0 or p1['y2'] > truck.l: return False
            if p1['z1'] < 0 or p1['z2'] > truck.h: return False
            
            # Check for overlapping packages
            for j in range(i + 1, len(placed)):
                p2 = placed[j]
                overlap_x = max(p1['x1'], p2['x1']) < min(p1['x2'], p2['x2'])
                overlap_y = max(p1['y1'], p2['y1']) < min(p1['y2'], p2['y2'])
                overlap_z = max(p1['z1'], p2['z1']) < min(p1['z2'], p2['z2'])
                
                if overlap_x and overlap_y and overlap_z:
                    return False
                    
            # Check floating and fragile support
            if p1['z1'] > 0:
                has_valid_support = False
                for p2 in placed:
                    if p1['id'] != p2['id']:
                        if p2['z2'] == p1['z1']:
                            # Check 2D base intersection
                            overlap_x = max(p1['x1'], p2['x1']) < min(p1['x2'], p2['x2'])
                            overlap_y = max(p1['y1'], p2['y1']) < min(p1['y2'], p2['y2'])
                            
                            if overlap_x and overlap_y:
                                # If a fragile item is used as support, INVALID!
                                if p2['is_fragile']:
                                    return False 
                                has_valid_support = True
                                
                if not has_valid_support:
                    return False # Floating without valid support
                    
        return True
    
    # Neighbor Generation
    def generate_neighbors(
        self,
        truck: Truck,
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
        """
        keys = list(self.placements.keys())
        inside_keys = [k for k in keys if self.placements[k] is not None]
        outside_keys = [k for k in keys if self.placements[k] is None]

        valid_z = {0}
        for pkg_id in inside_keys:
            pos = self.placements[pkg_id]
            pkg = package_catalog[pkg_id]
            _, _, eff_z = pos.get_effective_dimensions(pkg)
            if pos.z + eff_z <= truck.h:
                valid_z.add(pos.z + eff_z)
        z_list = list(valid_z)

        possible_orientations = [
            ('w', 'l', 'h'), ('w', 'h', 'l'), 
            ('l', 'w', 'h'), ('l', 'h', 'w'), 
            ('h', 'w', 'l'), ('h', 'l', 'w')
        ]

        # Random sampling (for Stochastic HC)
        if sample_size is not None:
            available_actions = []
            if len(keys) >= 2 and not (len(inside_keys) == 0 and len(outside_keys) >= 2):
                available_actions.append('swap')
            if inside_keys:
                available_actions.append('move')
                available_actions.append('rotate')
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
                    pkg = package_catalog[pkg_id]
                    eff_x, eff_y, eff_z = pos.get_effective_dimensions(pkg)
                    max_x = max(0, truck.w - eff_x)
                    max_y = max(0, truck.l - eff_y)
                    nx = max(0, min(max_x, pos.x + random.randint(-max_shift, max_shift)))
                    ny = max(0, min(max_y, pos.y + random.randint(-max_shift, max_shift)))
                    nz = random.choice(z_list)
                    if (nx, ny, nz) == (pos.x, pos.y, pos.z):
                        continue
                    new_p[pkg_id] = PackagePlacement(x=nx, y=ny, z=nz, orientation=pos.orientation)

                elif action == 'rotate':
                    pkg_id = random.choice(inside_keys)
                    pos = new_p[pkg_id]
                    ori = random.choice(get_90deg_rotations(pos.orientation))
                    new_p[pkg_id] = PackagePlacement(x=pos.x, y=pos.y, z=pos.z, orientation=ori)

                elif action == 'insert':
                    pkg_id = random.choice(outside_keys)
                    pkg = package_catalog[pkg_id]
                    ori = random.choice(possible_orientations)
                    ex, ey, ez = PackagePlacement(0, 0, 0, ori).get_effective_dimensions(pkg)
                    if ex > truck.w or ey > truck.l or ez > truck.h:
                        continue
                    nx = random.randint(0, truck.w - ex)
                    ny = random.randint(0, truck.l - ey)
                    nz = random.choice(z_list)
                    new_p[pkg_id] = PackagePlacement(x=nx, y=ny, z=nz, orientation=ori)

                candidate = State(placements=new_p)
                if candidate.is_valid(truck, package_catalog):
                    neighbors.append(candidate)

            return neighbors

        # Exhaustive/semi-exhaustive neighborhood (for Steepest & Sideways)
        candidates = []
        
        # SWAP
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                p1, p2 = keys[i], keys[j]
                if self.placements[p1] is None and self.placements[p2] is None:
                    continue # Both outside, no state change
                
                candidates.append(('swap', p1, p2))
                
        for pkg_id in inside_keys:
            pos = self.placements[pkg_id]
            # MOVE 
            for nx in range(max(0, pos.x - max_shift), min(truck.w, pos.x + max_shift + 1)):
                for ny in range(max(0, pos.y - max_shift), min(truck.l, pos.y + max_shift + 1)):
                    for nz in valid_z:
                        if nx != pos.x or ny != pos.y or nz != pos.z:
                            candidates.append(('move', pkg_id, nx, ny, nz, pos.orientation))
                            
            # ROTATE
            for ori in get_90deg_rotations(pos.orientation):
                candidates.append(('rotate', pkg_id, pos.x, pos.y, pos.z, ori))

        # INSERT
        for pkg_id in outside_keys:
            pkg = package_catalog[pkg_id]
            seen_inserts = set()
            for _ in range(insert_tries):
                ori = random.choice(possible_orientations)
                ex, ey, ez = PackagePlacement(0, 0, 0, ori).get_effective_dimensions(pkg)
                if ex > truck.w or ey > truck.l or ez > truck.h:
                    continue
                nx = random.randint(0, truck.w - ex)
                ny = random.randint(0, truck.l - ey)
                nz = random.choice(z_list)
                key = (pkg_id, nx, ny, nz, ori)
                if key not in seen_inserts:
                    seen_inserts.add(key)
                    candidates.append(('insert', pkg_id, nx, ny, nz, ori))
                    
        neighbors = []
        for instruction in candidates:
            new_p = self.copy_state().placements
            
            if instruction[0] == 'swap':
                _, p1, p2 = instruction
                new_p[p1], new_p[p2] = new_p[p2], new_p[p1]
            elif instruction[0] == 'move':
                _, pkg_id, nx, ny, nz, ori = instruction
                new_p[pkg_id] = PackagePlacement(x=nx, y=ny, z=nz, orientation=ori)
            elif instruction[0] == 'rotate':
                _, pkg_id, x, y, z, ori = instruction
                new_p[pkg_id] = PackagePlacement(x=x, y=y, z=z, orientation=ori)
            elif instruction[0] == 'insert':
                _, pkg_id, nx, ny, nz, ori = instruction
                new_p[pkg_id] = PackagePlacement(x=nx, y=ny, z=nz, orientation=ori)
                
            new_state = State(placements=new_p)
            if new_state.is_valid(truck, package_catalog):
                neighbors.append(new_state)
                
        return neighbors

def generate_random_state(truck: Truck, package_catalog: Dict[str, Package]) -> State:
    """Random initial state (floor)"""
    # All package is outside of the truck
    placements = {}
    for pkg_id in package_catalog.keys(): 
        placements[pkg_id] = None 
    
    initial_state = State(placements=placements)
    
    all_pkg_ids = list(package_catalog.keys())
    random.shuffle(all_pkg_ids)
    
    # 6 possible orientations (w, l, h) mapped to X, Y, Z axes
    possible_orientations = [
        ('w', 'l', 'h'), ('w', 'h', 'l'), 
        ('l', 'w', 'h'), ('l', 'h', 'w'), 
        ('h', 'w', 'l'), ('h', 'l', 'w')
    ]
    
    # Try to place packages one by one randomly
    for pkg_id in all_pkg_ids:
        random_ori = random.choice(possible_orientations)

        pkg = package_catalog[pkg_id]
        temp_placement = PackagePlacement(x=0, y=0, z=0, orientation=random_ori)
        eff_x, eff_y, eff_z = temp_placement.get_effective_dimensions(pkg)
            
        if eff_z > truck.h:
            continue
        max_x = max(0, truck.w - eff_x)
        max_y = max(0, truck.l - eff_y)
        
        random_x = random.randint(0, max_x)
        random_y = random.randint(0, max_y)
        
        # Create placement object
        test_placement = PackagePlacement(
            x=random_x, 
            y=random_y, 
            z=0, 
            orientation=random_ori
        )
        
        initial_state.placements[pkg_id] = test_placement
        # Check if the placement is valid
        if not initial_state.is_valid(truck, package_catalog):
            initial_state.placements[pkg_id] = None
            
    return initial_state


def parse_input(filepath: str) -> Tuple[Truck, Dict[str, Package]]:
    """
    Format:
    {
        "truck": {"w": 10, "l": 20, "h": 10, "maxCapacity": 100},
        "packages": [
            {"id": "P_A", "w": 5, "l": 5, "h": 5, "value": 100, "weight": 10, "is_fragile": false, "eta": 0},
            {"id": "P_B", "w": 5, "l": 5, "h": 5, "value": 150, "weight": 10, "is_fragile": true, "eta": 0}
        ]
    }
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    t_data = data['truck']
    truck = Truck(w=t_data['w'], l=t_data['l'], h=t_data['h'], maxCapacity=t_data['maxCapacity'])
    
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
        
    return truck, catalog

