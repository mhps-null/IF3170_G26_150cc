"""
Runner eksperimen Simulated Annealing.
"""

import argparse
import json
import os
import random

from src import visualization as viz
from src.foundation import generate_random_state, parse_input
from src.SA.objectives import OBJECTIVES
from src.SA.simulated_annealing import (
    SimulatedAnnealing,
    suggest_t0,
)


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
                "truck_id": pos.truck_id,
            }
        )
        for pid, pos in state.placements.items()
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("input")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--t0", type=float, default=None)
    parser.add_argument("--alpha", type=float, default=0.999)
    parser.add_argument("--t-min", type=float, default=0.1)
    parser.add_argument("--max-iter", type=int, default=20000)
    parser.add_argument(
        "--objective",
        choices=list(OBJECTIVES),
        default="base",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="./output")
    parser.add_argument("--show", action="store_true")

    args = parser.parse_args()

    if args.runs <= 0:
        parser.error("--runs harus lebih besar dari 0.")

    truck, catalog = parse_input(args.input)
    objective_fn = OBJECTIVES[args.objective](catalog)

    sa = SimulatedAnnealing(truck, catalog, objective_fn)

    t0 = (
        args.t0
        if args.t0 is not None
        else suggest_t0(catalog)
    )

    out_dir = os.path.join(args.out, f"sa_{args.objective}")
    os.makedirs(out_dir, exist_ok=True)

    histories = {}
    probs = {}
    summary = []

    print(
        f"SA | objective={args.objective} "
        f"T0={t0:.2f} alpha={args.alpha} "
        f"T_min={args.t_min} max_iter={args.max_iter}"
    )

    for run_number in range(1, args.runs + 1):
        random.seed(args.seed + run_number)

        initial_state = generate_random_state(truck, catalog)

        result = sa.run(
            initial_state,
            t0=t0,
            alpha=args.alpha,
            t_min=args.t_min,
            max_iter=args.max_iter,
        )

        label = f"Run {run_number}"

        histories[label] = result.history
        probs[label] = result.prob_history

        viz.plot_initial_final(
            result.start_state,
            result.final_state,
            truck,
            catalog,
            suptitle=(
                f"Simulated Annealing - {label} "
                f"(objective: {args.objective})"
            ),
            save_path=os.path.join(
                out_dir, f"run{run_number}_initial_final.png"
            ),
            show=args.show,
        )

        worse_candidate_count = (
            result.rejected_worse_count + result.accepted_worse
        )

        rejection_rate = (
            result.rejected_worse_count / worse_candidate_count
            if worse_candidate_count > 0
            else None
        )

        non_improving_frequency = (
            result.non_improving_iteration_count / result.iterations
            if result.iterations > 0
            else 0.0
        )

        summary.append({
            "run": run_number,
            "iterations": result.iterations,
            "duration_s": round(result.duration, 3),
            "initial_base_value": (
                result.start_state.get_objective_value(catalog)
            ),
            "final_objective": result.final_value,
            "final_base_value": result.final_base_value,
            "best_objective": result.best_value,

            "non_improving_iteration_count": (
                result.non_improving_iteration_count
            ),
            "non_improving_iteration_frequency": round(
                non_improving_frequency, 4
            ),

            "rejected_worse_count": result.rejected_worse_count,
            "accepted_worse": result.accepted_worse,
            "worse_neighbor_candidate_count": worse_candidate_count,
            "worse_neighbor_rejection_rate": (
                round(rejection_rate, 4)
                if rejection_rate is not None
                else None
            ),

            "no_neighbor": result.no_neighbor_count,

            "initial_state": placements_to_dict(result.start_state),
            "final_state": placements_to_dict(result.final_state),
            "best_state": placements_to_dict(result.best_state),
        })

        record = summary[-1]
        rate = record["worse_neighbor_rejection_rate"]
        rate_text = f"{rate:.1%}" if rate is not None else "N/A"

        print(
            f"{label}: "
            f"awal={record['initial_base_value']} "
            f"akhir(base)={record['final_base_value']} "
            f"terbaik={record['best_objective']} "
            f"iter={record['iterations']} "
            f"durasi={record['duration_s']}s "
            f"non-improving="
            f"{record['non_improving_iteration_count']} "
            f"({record['non_improving_iteration_frequency']:.1%}) "
            f"worse-rejected={record['rejected_worse_count']} "
            f"worse-accepted={record['accepted_worse']} "
            f"worse-rejection-rate={rate_text}"
        )

    viz.plot_objective(
        histories,
        f"SA: objective ({args.objective}) vs iterasi",
        save_path=os.path.join(out_dir, "objective_vs_iter.png"),
        show=args.show,
    )

    # Plot probabilitas hanya jika ada kandidat lebih buruk.
    # Ini menghindari grafik kosong dan warning legend.
    nonempty_probs = {
        label: values
        for label, values in probs.items()
        if values
    }

    if nonempty_probs:
        viz.plot_sa_prob(
            nonempty_probs,
            save_path=os.path.join(out_dir, "sa_probability.png"),
            show=args.show,
        )
    else:
        print(
            "Plot probabilitas dilewati: tidak ada kandidat "
            "dengan objective lebih rendah yang ditemukan."
        )

    summary_path = os.path.join(out_dir, "summary.json")

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "params": {
                    "objective": args.objective,
                    "t0": t0,
                    "alpha": args.alpha,
                    "t_min": args.t_min,
                    "max_iter": args.max_iter,
                    "seed": args.seed,
                },
                "runs": summary,
            },
            file,
            indent=2,
        )

    print(f"Hasil disimpan di {out_dir}")


if __name__ == "__main__":
    main()