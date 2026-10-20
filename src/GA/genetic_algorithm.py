# This file depends on @foundation.py

import src.foundation as foundation

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable
import random
import copy
import json
import time


@dataclass
class GAResult:
    start_state: foundation.State
    final_state: foundation.State
    final_value: float
    final_base_value: int
    population_size: int
    iterations: int
    duration: float
    max_history: List[float]
    avg_history: List[float]


class GeneticAlgorithm:
    @dataclass
    class Individual:
        state: foundation.State
        fitness: float

    fleet: foundation.Fleet
    catalog: Dict[str, foundation.Package]
    objective_fn: Callable[[foundation.State], float]
    population_size: int
    mutation_rate: float
    max_generations: int

    def _evaluate_fitness(self, state: foundation.State) -> float:
        """Evaluasi fitness hanya untuk state yang valid."""
    
        if set(state.placements.keys()) != set(self.catalog.keys()):
            raise ValueError(
                "State harus memetakan seluruh paket dalam catalog."
            )
    
        if not state.is_valid(self.fleet, self.catalog):
            raise ValueError(
                "GA tidak boleh mengevaluasi state yang melanggar constraint."
            )
    
        return float(self.objective_fn(state))

    def __init__(
        self,
        fleet: foundation.Fleet,
        catalog: Dict[str, foundation.Package],
        objective_fn: Callable[[foundation.State], float],
        initial_population: List[foundation.State] = None,
        population_size: int = 200,
        mutation_rate: float = 0.01,  # Probability of mutating an individual
        max_generations: int = 200,
    ):

        self.fleet = fleet
        self.catalog = catalog
        self.objective_fn = objective_fn

        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.max_generations = max_generations

        if initial_population is not None:
            if not initial_population:
                raise ValueError("Initial population tidak boleh kosong.")
        
            self.population = [
                self.Individual(
                    state=state.copy_state(),
                    fitness=self._evaluate_fitness(state),
                )
                for state in initial_population
            ]
        else:
            self.population = []
        
            for _ in range(self.population_size):
                state = foundation.generate_random_state(
                    self.fleet, self.catalog
                )
        
                self.population.append(
                    self.Individual(
                        state=state,
                        fitness=self._evaluate_fitness(state),
                    )
                )

    def roulette_wheel_selection(
        self, selection_probabilities: Optional[List[float]]
    ) -> Tuple[Individual, Individual]:
        if selection_probabilities is None:
            return tuple(random.choices(self.population, k=2))
        return tuple(random.choices(self.population, selection_probabilities, k=2))

    def selected_parents(self) -> List[Tuple[Individual, Individual]]:
        # assuming fitness is always already computed beforehand
        lowest_fitness = min(individual.fitness for individual in self.population)
        shifted_fitness = [
            individual.fitness + abs(lowest_fitness) for individual in self.population
        ]
        total_fitness = sum(shifted_fitness)
        selection_probabilities = (
            None
            if total_fitness == 0
            else [fitness / total_fitness for fitness in shifted_fitness]
        )
        return [
            self.roulette_wheel_selection(selection_probabilities)
            for _ in range(self.population_size)
        ]

    def crossover(
        self,
        parent1: Individual,
        parent2: Individual,
    ) -> Individual:
        """Single-point crossover dengan perbaikan state yang tidak valid."""
    
        ids = list(self.catalog)
    
        if not ids:
            raise ValueError("Catalog paket tidak boleh kosong.")
    
        # Jika hanya ada satu paket, crossover tidak dapat membagi gen.
        if len(ids) == 1:
            chosen_parent = random.choice([parent1, parent2])
            state = chosen_parent.state.copy_state()
    
            return self.Individual(
                state=state,
                fitness=self._evaluate_fitness(state),
            )
    
        # Single-point crossover.
        cut_point = random.randrange(1, len(ids))
    
        placements = {
            pid: copy.copy(
                (parent1 if i < cut_point else parent2)
                .state.placements[pid]
            )
            for i, pid in enumerate(ids)
        }
    
        child_state = foundation.State(placements=placements)
    
        # Jika hasil crossover valid, gunakan langsung.
        if child_state.is_valid(self.fleet, self.catalog):
            return self.Individual(
                state=child_state,
                fitness=self._evaluate_fitness(child_state),
            )
    
        # Jika tidak valid, bangun ulang state secara bertahap.
        # None berarti paket berada di luar truk.
        repaired_placements = {
            pid: None for pid in ids
        }
    
        # Paket di bagian bawah diproses lebih dahulu agar
        # paket di atasnya hanya diterima jika mempunyai support.
        ordered_ids = sorted(
            (
                pid
                for pid in ids
                if placements[pid] is not None
            ),
            key=lambda pid: (placements[pid].z, pid),
        )
    
        for pid in ordered_ids:
            repaired_placements[pid] = copy.copy(placements[pid])
    
            partial_state = foundation.State(
                placements=repaired_placements.copy()
            )
    
            # Tolak paket yang menyebabkan pelanggaran constraint.
            if not partial_state.is_valid(self.fleet, self.catalog):
                repaired_placements[pid] = None
    
        repaired_state = foundation.State(
            placements=repaired_placements
        )
    
        # Pemeriksaan akhir untuk menjaga invariant GA.
        if not repaired_state.is_valid(self.fleet, self.catalog):
            raise RuntimeError(
                "Perbaikan crossover menghasilkan state tidak valid."
            )
    
        return self.Individual(
            state=repaired_state,
            fitness=self._evaluate_fitness(repaired_state),
        )

    def mutate(self, individual: Individual) -> Individual:
        neighbors = individual.state.generate_neighbors(
            self.fleet, self.catalog, sample_size=15
        )
        if not neighbors:
            return self.Individual(
                state=individual.state.copy_state(),
                fitness=individual.fitness,
            )
        
        state = random.choice(neighbors)
        
        return self.Individual(
            state=state,
            fitness=self._evaluate_fitness(state),
        )

    def _record_population(self, max_history: List[float], avg_history: List[float]):
        fitnesses = [individual.fitness for individual in self.population]
        max_history.append(max(fitnesses))
        avg_history.append(sum(fitnesses) / len(fitnesses))

    def run(self) -> GAResult:
        start_time = time.perf_counter()
        start_state = max(
            self.population, key=lambda individual: individual.fitness
        ).state.copy_state()
        max_history: List[float] = []
        avg_history: List[float] = []
        self._record_population(max_history, avg_history)

        for generation in range(self.max_generations):
            # Select
            # default: roulette wheel selection
            selected_parents = self.selected_parents()

            # Mate :D & Mutate
            children = [
                self.mutate(child) if random.random() < self.mutation_rate else child
                for parent1, parent2 in selected_parents
                for child in [self.crossover(parent1, parent2)]
            ]

            # Replace
            # default: mu + lambda replacement
            new_population = self.population + children
            new_population.sort(key=lambda x: x.fitness, reverse=True)
            self.population = new_population[: self.population_size]
            self._record_population(max_history, avg_history)

        best = self.population[0]
        return GAResult(
            start_state=start_state,
            final_state=best.state.copy_state(),
            final_value=best.fitness,
            final_base_value=best.state.get_objective_value(self.catalog),
            population_size=self.population_size,
            iterations=self.max_generations,
            duration=time.perf_counter() - start_time,
            max_history=max_history,
            avg_history=avg_history,
        )
