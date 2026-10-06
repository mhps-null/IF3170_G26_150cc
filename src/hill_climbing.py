import time
import random
from typing import Dict, Tuple, List
from foundation import State, Truck, Package, generate_random_state

class HillClimbing:
    def __init__(self, truck: Truck, catalog: Dict[str, Package]):
        self.truck = truck
        self.catalog = catalog

    def steepest_ascent(self, initial_state: State = None) -> Tuple[State, State, int, float, List[int]]:
        """
        Steepest Ascent Hill-Climbing
        Evaluates all neighbors and strictly picks the best one.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        
        while True:
            neighbors = current_state.generate_neighbors(self.truck, self.catalog, max_shift=2)
            if not neighbors:
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value <= current_value:
                break
                
            current_state = best_neighbor
            current_value = best_value
            history.append(current_value)
            iterations += 1
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history
    
    def sideways_move(self, max_sideways: int, initial_state: State = None) -> Tuple[State, State, int, float, List[int]]:
        """
        Hill-Climbing with Sideways Move
        Allows the search to move to a neighbor with the same score, up to a max_sideways limit.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        sideways_count = 0
        
        while True:
            neighbors = current_state.generate_neighbors(self.truck, self.catalog, max_shift=2)
            if not neighbors:
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value < current_value:
                break
                
            elif best_value == current_value:
                if sideways_count >= max_sideways:
                    break
                sideways_count += 1
            else:
                sideways_count = 0 
                
            current_state = best_neighbor
            current_value = best_value
            history.append(current_value)
            iterations += 1
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history

    def random_restart(self, max_restart: int) -> Tuple[State, State, int, float, List[int], List[int], List[int]]:
        """
        Random Restart Hill-Climbing
        Executes Steepest Ascent multiple times from entirely randomized starting positions.
        """
        start_time = time.perf_counter()
        
        global_best_state = None
        global_best_start_state = None
        global_best_value = -1
        global_history = []
        restart_iterations = []
        restart_indices = []
        total_iterations = 0
        
        for i in range(max_restart):
            restart_indices.append(len(global_history))
            
            state, start_state, iters, _, history = self.steepest_ascent(initial_state=None)
            val = state.get_objective_value(self.catalog)
            
            restart_iterations.append(iters)
            total_iterations += iters
            global_history.extend(history)
            
            if val > global_best_value:
                global_best_value = val
                global_best_state = state
                global_best_start_state = start_state
                
        duration = time.perf_counter() - start_time
        return global_best_state, global_best_start_state, total_iterations, duration, global_history, restart_iterations, restart_indices

    def stochastic(self, initial_state: State = None, max_no_improve: int = 50, sample_size: int = 15) -> Tuple[State, State, int, float, List[int]]:
        """
        Stochastic Hill-Climbing
        Randomly picks from the better neighbors without evaluating all combinations.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        
        no_improve = 0
        
        while no_improve < max_no_improve:
            neighbors = current_state.generate_neighbors(self.truck, self.catalog, max_shift=2, sample_size=sample_size)
            
            better_neighbors = []
            for n in neighbors:
                if n.get_objective_value(self.catalog) > current_value:
                    better_neighbors.append(n)
            
            if not better_neighbors:
                no_improve += 1
                continue 
        
            current_state = random.choice(better_neighbors)
            current_value = current_state.get_objective_value(self.catalog)
            history.append(current_value)
            iterations += 1
            no_improve = 0
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history
