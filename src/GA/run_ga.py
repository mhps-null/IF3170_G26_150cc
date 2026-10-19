"""
Runner eksperimen Genetic Algorithm: jalankan N kali, simpan visualisasi dan
ringkasan ke folder output.

Contoh, dari root repositori:
    python src/GA/run_ga.py input/sample_input.json --runs 3 --out output
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import visualization as viz
from src.foundation import parse_input
from src.GA.genetic_algorithm import GeneticAlgorithm
from src.GA.objectives import make_base_objective, make_violation_objective


def placements_to_dict(state):
    return {
        pid: (
            None
            if pos is None
            else {
                "x": pos.x,
                "y": pos.y,
                "z": pos.z,
                "orientation": list(pos.orientation),
            }
        )
        for pid, pos in state.placements.items()
    }


def make_objective(name, truck, catalog):
    if name == "violation":
        return make_violation_objective(truck, catalog)
    return make_base_objective(catalog)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--population-size", type=int, default=200)
    ap.add_argument("--mutation-rate", type=float, default=0.01)
    ap.add_argument("--max-generations", type=int, default=200)
    ap.add_argument("--objective", choices=("base", "violation"), default="violation")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="./output")
    ap.add_argument("--show", action="store_true", help="tampilkan jendela plot")
    args = ap.parse_args()

    truck, catalog = parse_input(args.input)
    out_dir = os.path.join(args.out, f"ga_{args.objective}")
    os.makedirs(out_dir, exist_ok=True)

    summary = []
    print(
        f"GA | objective={args.objective} populasi={args.population_size} "
        f"mutasi={args.mutation_rate} generasi={args.max_generations}"
    )
    for r in range(1, args.runs + 1):
        random.seed(args.seed + r)
        ga = GeneticAlgorithm(
            truck,
            catalog,
            make_objective(args.objective, truck, catalog),
            population_size=args.population_size,
            mutation_rate=args.mutation_rate,
            max_generations=args.max_generations,
        )
        res = ga.run()
        label = f"Run {r}"

        viz.plot_initial_final(
            res.start_state,
            res.final_state,
            truck,
            catalog,
            suptitle=f"Genetic Algorithm - {label} (objective: {args.objective})",
            save_path=os.path.join(out_dir, f"run{r}_initial_final.png"),
            show=args.show,
        )
        viz.plot_ga_progress(
            res.max_history,
            res.avg_history,
            title=f"GA: objective populasi - {label}",
            save_path=os.path.join(out_dir, f"run{r}_objective_vs_iter.png"),
            show=args.show,
        )

        summary.append(
            {
                "run": r,
                "population_size": res.population_size,
                "iterations": res.iterations,
                "duration_s": round(res.duration, 3),
                "initial_base_value": res.start_state.get_objective_value(catalog),
                "final_objective": res.final_value,
                "final_base_value": res.final_base_value,
                "initial_state": placements_to_dict(res.start_state),
                "final_state": placements_to_dict(res.final_state),
            }
        )
        s = summary[-1]
        print(
            f"{label}: awal={s['initial_base_value']} akhir(base)={s['final_base_value']} "
            f"populasi={s['population_size']} iter={s['iterations']} durasi={s['duration_s']}s"
        )

    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(
            {
                "params": {
                    "objective": args.objective,
                    "population_size": args.population_size,
                    "mutation_rate": args.mutation_rate,
                    "max_generations": args.max_generations,
                    "seed": args.seed,
                },
                "runs": summary,
            },
            f,
            indent=2,
        )
    print(f"Hasil disimpan di {out_dir}")


if __name__ == "__main__":
    main()
