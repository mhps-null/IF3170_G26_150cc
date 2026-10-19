"""
Experiment runner for Hill-Climbing algorithms:
Runs Steepest Ascent, Sideways Move, Random Restart, or Stochastic Hill-Climbing,
saves 3D visualizations and summary metrics to the output directory.

Usage examples:
    python HC/run_hc.py ../input/cek.json --variant steepest --runs 3 --out ../output
    python HC/run_hc.py ../input/cek.json --variant all --runs 3 --out ../output
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Any

# Ensure src and project root are in sys.path
_hc_dir = Path(__file__).resolve().parent
_src_dir = _hc_dir.parent
_root_dir = _src_dir.parent
for _p in [str(_src_dir), str(_root_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from src import visualization as viz
    from src.foundation import generate_random_state, parse_input
    from src.HC.hill_climbing import HillClimbing
except ModuleNotFoundError:
    import visualization as viz
    from foundation import generate_random_state, parse_input
    from HC.hill_climbing import HillClimbing


def placements_to_dict(state):
    return {
        pid: (None if pos is None else
              {"x": pos.x, "y": pos.y, "z": pos.z, "orientation": list(pos.orientation)})
        for pid, pos in state.placements.items()
    }


def run_variant(variant: str, hc: HillClimbing, truck, catalog, args, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    histories: Dict[str, List[float]] = {}
    summary: List[Dict[str, Any]] = []

    print(f"\nHC | variant={variant} runs={args.runs} insert_tries={args.insert_tries}")

    for r in range(1, args.runs + 1):
        random.seed(args.seed + r)
        initial_st = generate_random_state(truck, catalog)
        label = f"Run {r}"

        if variant == "steepest":
            final_st, start_st, iters, dur, hist = hc.steepest_ascent(
                initial_state=initial_st,
                insert_tries=args.insert_tries
            )
            extra_info = {}

        elif variant == "sideways":
            final_st, start_st, iters, dur, hist = hc.sideways_move(
                max_sideways=args.max_sideways,
                initial_state=initial_st,
                consecutive=not args.cumulative,
                insert_tries=args.insert_tries
            )
            extra_info = {"max_sideways": args.max_sideways, "consecutive": not args.cumulative}

        elif variant == "restart":
            final_st, start_st, iters, dur, hist, r_iters, r_idx = hc.random_restart(
                max_restart=args.max_restart,
                insert_tries=args.insert_tries
            )
            extra_info = {
                "max_restart": args.max_restart,
                "restart_iterations": r_iters,
                "restart_indices": r_idx
            }

        elif variant == "stochastic":
            final_st, start_st, iters, dur, hist = hc.stochastic(
                initial_state=initial_st,
                max_no_improve=args.max_no_improve,
                sample_size=args.sample_size
            )
            extra_info = {
                "sample_size": args.sample_size,
                "max_no_improve": args.max_no_improve
            }

        else:
            raise ValueError(f"Unknown variant: {variant}")

        histories[label] = [float(v) for v in hist]
        init_val = start_st.get_objective_value(catalog)
        final_val = final_st.get_objective_value(catalog)
        best_val = max(hist) if hist else final_val

        # Save 3D state visualization
        viz.plot_initial_final(
            start_st, final_st, truck, catalog,
            suptitle=f"Hill-Climbing ({variant.capitalize()}) - {label}",
            save_path=os.path.join(out_dir, f"run{r}_initial_final.png"),
            show=args.show
        )

        run_record = {
            "run": r,
            "iterations": iters,
            "duration_s": round(dur, 3),
            "initial_value": init_val,
            "final_value": final_val,
            "best_value": best_val,
            "initial_state": placements_to_dict(start_st),
            "final_state": placements_to_dict(final_st),
        }
        run_record.update(extra_info)
        summary.append(run_record)

        print(
            f"  {label}: awal={init_val} akhir={final_val} "
            f"iter={iters} durasi={round(dur, 3)}s"
        )

    # Plot objective function vs iteration across runs
    viz.plot_objective(
        histories,
        title=f"Hill-Climbing ({variant.capitalize()}): Objective vs Iterasi",
        save_path=os.path.join(out_dir, "objective_vs_iter.png"),
        show=args.show
    )

    # Save summary.json
    params = {
        "algorithm": "Hill-Climbing",
        "variant": variant,
        "runs": args.runs,
        "seed": args.seed,
        "insert_tries": args.insert_tries
    }
    if variant == "sideways":
        params.update({"max_sideways": args.max_sideways, "consecutive": not args.cumulative})
    elif variant == "restart":
        params.update({"max_restart": args.max_restart})
    elif variant == "stochastic":
        params.update({"sample_size": args.sample_size, "max_no_improve": args.max_no_improve})

    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump({"params": params, "runs": summary}, f, indent=2)

    print(f"Hasil {variant} disimpan di {out_dir}")
    return [s["final_value"] for s in summary]


def main():
    ap = argparse.ArgumentParser(description="Runner eksperimen Hill-Climbing")
    ap.add_argument("input", help="Path ke file input JSON (e.g., input/cek.json)")
    ap.add_argument(
        "--variant",
        choices=["steepest", "sideways", "restart", "stochastic", "all"],
        default="all",
        help="Varian HC yang ingin dijalankan (default: all)"
    )
    ap.add_argument("--runs", type=int, default=3, help="Jumlah percobaan/run per varian (default: 3)")
    ap.add_argument("--seed", type=int, default=42, help="Seed acak (default: 42)")
    ap.add_argument("--out", default="../output", help="Folder output (default: ../output)")
    ap.add_argument("--show", action="store_true", help="Tampilkan jendela plot secara interaktif")

    # Hyperparameters
    ap.add_argument("--insert-tries", type=int, default=50, help="Jumlah percobaan sampling INSERT (default: 50)")
    ap.add_argument("--max-sideways", type=int, default=50, help="Batas sideways move (default: 50)")
    ap.add_argument("--cumulative", action="store_true", help="Gunakan penghitung sideways kumulatif (default: consecutive)")
    ap.add_argument("--max-restart", type=int, default=3, help="Jumlah restart untuk Random Restart (default: 3)")
    ap.add_argument("--sample-size", type=int, default=15, help="Jumlah sampel per iterasi Stochastic HC (default: 15)")
    ap.add_argument("--max-no-improve", type=int, default=50, help="Batas no-improve Stochastic HC (default: 50)")

    args = ap.parse_args()

    truck, catalog = parse_input(args.input)
    hc = HillClimbing(truck, catalog)

    variants_to_run = (
        ["steepest", "sideways", "restart", "stochastic"]
        if args.variant == "all"
        else [args.variant]
    )

    all_comparison_results = {}
    for var in variants_to_run:
        out_dir = os.path.join(args.out, f"hc_{var}")
        final_scores = run_variant(var, hc, truck, catalog, args, out_dir)
        all_comparison_results[var.capitalize()] = final_scores

    # If running all variants, produce a comparison plot
    if len(variants_to_run) > 1:
        comp_dir = os.path.join(args.out, "hc_comparison")
        os.makedirs(comp_dir, exist_ok=True)
        viz.plot_final_comparison(
            all_comparison_results,
            title="Hill-Climbing: Perbandingan Nilai Akhir Antar Varian",
            save_path=os.path.join(comp_dir, "hc_variants_comparison.png"),
            show=args.show
        )
        print(f"\nPlot perbandingan antar varian disimpan di {comp_dir}")


if __name__ == "__main__":
    main()
