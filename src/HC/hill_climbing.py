import time
import random
from typing import Dict, Tuple, List, Optional

try:
    from src.foundation import Fleet, State, Package, generate_random_state
except ModuleNotFoundError:
    from foundation import Fleet, State, Package, generate_random_state


class HillClimbing:
    def __init__(self, fleet: Fleet, catalog: Dict[str, Package]):
        self.fleet = fleet
        self.catalog = catalog

    def steepest_ascent(
        self,
        initial_state: State = None,
        insert_tries: int = 50,
        max_resamples: int = 3
    ) -> Tuple[State, State, int, float, List[int]]:
        """
        Steepest Ascent HC with random INSERT sampling (not exhaustive), retries up to `max_resamples`
        if no improvement found which the local optimum not guaranteed.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.fleet, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        resample_count = 0
        
        while True:
            iterations += 1
            neighbors = current_state.generate_neighbors(
                self.fleet,
                self.catalog,
                max_shift=2,
                insert_tries=insert_tries
            )
            
            if not neighbors:
                history.append(current_value)

                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value <= current_value:
                history.append(current_value)
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
        HC with Sideways Move, up to `max_sideways` plateau moves, terminating immediately at the limit.
        When`consecutive=True` resets the counter on improvement, `consecutive=False` counts cumulatively.
        """
        if max_sideways < 0:
            raise ValueError(f"max_sideways cannot be negative, got: {max_sideways}")

        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.fleet, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        sideways_count = 0
        resample_count = 0
        
        while True:
            iterations += 1
            neighbors = current_state.generate_neighbors(
                self.fleet,
                self.catalog,
                max_shift=2,
                insert_tries=insert_tries
            )
            
            if not neighbors:
                history.append(current_value)

                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            scored = [(n, n.get_objective_value(self.catalog)) for n in neighbors]
            best_value = max(v for _, v in scored)
            best_neighbors = [n for n, v in scored if v == best_value]
            best_neighbor = random.choice(best_neighbors)
            
            if best_value < current_value:
                history.append(current_value)

                if resample_count < max_resamples:
                    resample_count += 1
                    continue
                break
                
            elif best_value == current_value:
                if sideways_count >= max_sideways:
                    history.append(current_value)
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
        Samples neighbors immediately with balanced action type probabilities, then picks randomly among strictly better neighbors.
        """
        start_time = time.perf_counter()
        current_state = initial_state if initial_state else generate_random_state(self.fleet, self.catalog)
        start_state = current_state.copy_state()
        current_value = current_state.get_objective_value(self.catalog)
        
        history = [current_value]
        iterations = 0
        no_improve = 0
        
        while no_improve < max_no_improve:
            iterations += 1
            # Generate neighbors directly on-the-fly with balanced action types
            neighbors = current_state.generate_neighbors(
                self.fleet,
                self.catalog,
                max_shift=2,
                sample_size=sample_size,
                max_sample_attempts=max_sample_attempts
            )
            
            better_neighbors = [n for n in neighbors if n.get_objective_value(self.catalog) > current_value]
            
            if not better_neighbors:
                no_improve += 1
                history.append(current_value)
                continue 
        
            current_state = random.choice(better_neighbors)
            current_value = current_state.get_objective_value(self.catalog)
            history.append(current_value)
            no_improve = 0
            
        duration = time.perf_counter() - start_time
        return current_state, start_state, iterations, duration, history

