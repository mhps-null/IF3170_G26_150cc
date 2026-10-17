import time
import random
from typing import Dict, Tuple, List, Optional

try:
    from src.foundation import State, Truck, Package, generate_random_state
except ModuleNotFoundError:
    from foundation import State, Truck, Package, generate_random_state


class HillClimbing:
    def __init__(self, truck: Truck, catalog: Dict[str, Package]):
        self.truck = truck
        self.catalog = catalog

    def steepest_ascent(
        self,
        initial_state: State = None,
        insert_tries: int = 50,
        max_resamples: int = 3
    ) -> Tuple[State, State, int, float, List[int]]:
        """
        Steepest Ascent Hill-Climbing with candidate INSERT sampling.
        
        Documentation & Theoretical Limitations:
        - INSERT candidates are generated via random sampling of `insert_tries` per package
          outside the truck (avoiding exhaustive container coordinate grid enumeration for computational efficiency).
        - If in any iteration all generated neighbors have value <= current_value, the algorithm
          attempts resampling up to `max_resamples` times to ensure no viable placement spot
          was missed due to unlucky random sampling.
        - Consequently, termination does NOT guarantee finding an absolute local optimum
          over all possible container placement combinations.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        resample_count = 0
        
        while True:
            neighbors = current_state.generate_neighbors(
                self.truck,
                self.catalog,
                max_shift=2,
                insert_tries=insert_tries
            )
            
            if not neighbors:
                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value <= current_value:
                # Try resampling before deciding to stop
                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
            
            # Successfully found an improving neighbor
            resample_count = 0
            current_state = best_neighbor
            current_value = best_value
            history.append(current_value)
            iterations += 1
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history
    
    def sideways_move(
        self,
        max_sideways: int,
        initial_state: State = None,
        consecutive: bool = True,
        insert_tries: int = 50,
        max_resamples: int = 3
    ) -> Tuple[State, State, int, float, List[int]]:
        """
        Hill-Climbing with Sideways Move.
        
        Allows the search to move to a neighbor with the same objective value (plateau)
        up to a max_sideways limit. The search terminates immediately once the number of
        sideways moves reaches max_sideways.
        
        Sideways Counter Explanation (consecutive vs cumulative):
        - consecutive = True (AIMA standard / consecutive moves):
          sideways_count counts consecutive moves on a plateau. If a strictly better neighbor
          is found (best_value > current_value), sideways_count resets to 0.
        - consecutive = False (cumulative / total):
          sideways_count counts the total sideways moves across the entire search without resetting.
        
        In both modes, as soon as the max_sideways-th sideways move is executed,
        the search terminates IMMEDIATELY (does not continue to the next iteration).
        """
        if max_sideways < 0:
            raise ValueError(f"max_sideways cannot be negative, got: {max_sideways}")

        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        sideways_count = 0
        resample_count = 0
        
        while True:
            if max_sideways == 0 and sideways_count >= max_sideways:
                break

            neighbors = current_state.generate_neighbors(
                self.truck,
                self.catalog,
                max_shift=2,
                insert_tries=insert_tries
            )
            
            if not neighbors:
                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value < current_value:
                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            elif best_value == current_value:
                if sideways_count >= max_sideways:
                    break
                sideways_count += 1
                is_sideways = True
            else:
                if consecutive:
                    sideways_count = 0  # reset for consecutive count
                is_sideways = False

            resample_count = 0
            current_state = best_neighbor
            current_value = best_value
            history.append(current_value)
            iterations += 1

            # Terminate immediately once the max_sideways move limit is reached
            if is_sideways and sideways_count >= max_sideways:
                break
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history

    def random_restart(
        self,
        max_restart: int,
        insert_tries: int = 50,
        max_resamples: int = 3
    ) -> Tuple[State, State, int, float, List[int], List[int], List[int]]:
        """
        Random Restart Hill-Climbing
        Executes Steepest Ascent multiple times from entirely randomized starting positions.
        """
        if max_restart <= 0:
            raise ValueError(f"max_restart must be a positive integer (> 0), got: {max_restart}")

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
            
            state, start_state, iters, _, history = self.steepest_ascent(
                initial_state=None,
                insert_tries=insert_tries,
                max_resamples=max_resamples
            )
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

    def stochastic(
        self,
        initial_state: State = None,
        max_no_improve: int = 50,
        sample_size: int = 15,
        max_sample_attempts: int = 100
    ) -> Tuple[State, State, int, float, List[int]]:
        """
        Stochastic Hill-Climbing
        
        Generates random neighbor samples directly on-the-fly without building
        the full candidate list in memory. Action type probabilities (swap, move, rotate, insert)
        are balanced so samples are not dominated by move and rotate which have Delta = 0.
        Randomly picks among strictly better neighbors.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.truck, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        no_improve = 0
        
        while no_improve < max_no_improve:
            # Generate neighbors directly on-the-fly with balanced action types
            neighbors = current_state.generate_neighbors(
                self.truck,
                self.catalog,
                max_shift=2,
                sample_size=sample_size,
                max_sample_attempts=max_sample_attempts
            )
            
            better_neighbors = [n for n in neighbors if n.get_objective_value(self.catalog) > current_value]
            
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

