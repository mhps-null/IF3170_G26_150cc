"""
Runner eksperimen Simulated Annealing: jalankan N kali, simpan visualisasi dan
ringkasan ke folder output.

Contoh:
    python -m src.SA.run_sa input/sample_input.json --runs 3 --out output
    python -m src.SA.run_sa input/sample_input.json --objective eta      # Bonus 1
"""
import argparse
import json
import os
import random

from src import visualization as viz
from src.foundation import generate_random_state, parse_input
from src.SA.objectives import OBJECTIVES
from src.SA.simulated_annealing import SimulatedAnnealing, suggest_t0


def placements_to_dict(state):
    return {pid: (None if pos is None else
                  {"x": pos.x, "y": pos.y, "z": pos.z, "orientation": list(pos.orientation)})
            for pid, pos in state.placements.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--t0", type=float, default=None, help="default: rata-rata value paket")
    ap.add_argument("--alpha", type=float, default=0.999)
    ap.add_argument("--t-min", type=float, default=0.1)
    ap.add_argument("--max-iter", type=int, default=20000)
    ap.add_argument("--objective", choices=list(OBJECTIVES), default="base")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="./output")
    ap.add_argument("--show", action="store_true", help="tampilkan jendela plot")
    args = ap.parse_args()

    truck, catalog = parse_input(args.input)
    objective_fn = OBJECTIVES[args.objective](catalog)
    sa = SimulatedAnnealing(truck, catalog, objective_fn)
    t0 = args.t0 if args.t0 is not None else suggest_t0(catalog)

    out_dir = os.path.join(args.out, f"sa_{args.objective}")
    os.makedirs(out_dir, exist_ok=True)

    histories, probs, summary = {}, {}, []
    print(f"SA | objective={args.objective} T0={t0:.2f} alpha={args.alpha} T_min={args.t_min} max_iter={args.max_iter}")
    for r in range(1, args.runs + 1):
        random.seed(args.seed + r)
        res = sa.run(generate_random_state(truck, catalog), t0=t0, alpha=args.alpha,
                     t_min=args.t_min, max_iter=args.max_iter)
        label = f"Run {r}"
        histories[label], probs[label] = res.history, res.prob_history

        viz.plot_initial_final(res.start_state, res.final_state, truck, catalog,
                               suptitle=f"Simulated Annealing - {label} (objective: {args.objective})",
                               save_path=os.path.join(out_dir, f"run{r}_initial_final.png"), show=args.show)
        summary.append({
            "run": r, "iterations": res.iterations, "duration_s": round(res.duration, 3),
            "initial_base_value": res.start_state.get_objective_value(catalog),
            "final_objective": res.final_value, "final_base_value": res.final_base_value,
            "best_objective": res.best_value,
            "stuck_count": res.stuck_count,
            "stuck_frequency": round(res.stuck_count / max(1, res.iterations), 4),
            "accepted_worse": res.accepted_worse, "no_neighbor": res.no_neighbor_count,
            "initial_state": placements_to_dict(res.start_state),
            "final_state": placements_to_dict(res.final_state),
        })
        s = summary[-1]
        print(f"{label}: awal={s['initial_base_value']} akhir(base)={s['final_base_value']} "
              f"iter={s['iterations']} durasi={s['duration_s']}s stuck={s['stuck_count']} "
              f"({s['stuck_frequency']:.1%}) worse-accepted={s['accepted_worse']}")

    viz.plot_objective(histories, f"SA: objective ({args.objective}) vs iterasi",
                       save_path=os.path.join(out_dir, "objective_vs_iter.png"), show=args.show)
    viz.plot_sa_prob(probs, save_path=os.path.join(out_dir, "sa_probability.png"), show=args.show)

    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump({"params": {"objective": args.objective, "t0": t0, "alpha": args.alpha,
                              "t_min": args.t_min, "max_iter": args.max_iter, "seed": args.seed},
                   "runs": summary}, f, indent=2)
    print(f"Hasil disimpan di {out_dir}")


if __name__ == "__main__":
    main()