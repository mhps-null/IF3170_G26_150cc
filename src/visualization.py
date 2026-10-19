from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from src.foundation import Package, State, Truck

# ---------- helper ----------
def _box_faces(x, y, z, dx, dy, dz):
    v = [(x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z),
         (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)]
    idx = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4))
    return [[v[i] for i in f] for f in idx]


def _colors(catalog: Dict[str, Package]):
    cmap = plt.get_cmap("tab20")
    return {pid: cmap(i % 20) for i, pid in enumerate(sorted(catalog))}


def _finish(fig, save_path: Optional[str], show: bool):
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close(fig)


def _info_text(state: State, truck: Truck, catalog: Dict[str, Package], max_outside: int = 14) -> str:
    inside = [p for p, pos in state.placements.items() if pos is not None]
    outside = [p for p, pos in state.placements.items() if pos is None]
    weight = sum(catalog[p].weight for p in inside)
    lines = [
        f"Value total : {state.get_objective_value(catalog)}",
        f"Berat       : {weight} / {truck.maxCapacity}",
        f"Di dalam    : {len(inside)} paket",
        f"Di luar     : {len(outside)} paket",
        f"Peti kemas  : {truck.w} x {truck.l} x {truck.h}",
        "(garis merah tebal = fragile)",
        "",
        "Paket di luar (id: WxLxH value berat):",
    ]
    for pid in outside[:max_outside]:
        p = catalog[pid]
        lines.append(f" {pid}: {p.w}x{p.l}x{p.h} v={p.value} b={p.weight}{' F' if p.is_fragile else ''}")
    if len(outside) > max_outside:
        lines.append(f" ... +{len(outside) - max_outside} lainnya")
    return "\n".join(lines)


# ---------- state / truk ----------
def draw_state(ax, state: State, truck: Truck, catalog: Dict[str, Package], title: str = ""):
    colors = _colors(catalog)
    ax.add_collection3d(Poly3DCollection(
        _box_faces(0, 0, 0, truck.w, truck.l, truck.h),
        facecolors="gray", edgecolors="black", linewidths=1.2, alpha=0.05))
    for pid, pos in state.placements.items():
        if pos is None:
            continue
        pkg = catalog[pid]
        dx, dy, dz = pos.get_effective_dimensions(pkg)
        ax.add_collection3d(Poly3DCollection(
            _box_faces(pos.x, pos.y, pos.z, dx, dy, dz),
            facecolors=colors[pid], edgecolors="red" if pkg.is_fragile else "black",
            linewidths=2.2 if pkg.is_fragile else 0.6, alpha=0.75))
        ax.text(pos.x + dx / 2, pos.y + dy / 2, pos.z + dz, pid, fontsize=6, ha="center")
    ax.set_xlim(0, truck.w); ax.set_ylim(0, truck.l); ax.set_zlim(0, truck.h)
    ax.set_box_aspect((truck.w, truck.l, truck.h))
    ax.set_xlabel("x (width)"); ax.set_ylabel("y (length)"); ax.set_zlabel("z (height)")
    ax.set_title(title)


def plot_state(state: State, truck: Truck, catalog: Dict[str, Package], title: str = "State",
               save_path: Optional[str] = None, show: bool = False):
    fig = plt.figure(figsize=(11, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.2, 1])
    draw_state(fig.add_subplot(gs[0], projection="3d"), state, truck, catalog, title)
    axt = fig.add_subplot(gs[1]); axt.axis("off")
    axt.text(0, 1, _info_text(state, truck, catalog), va="top", family="monospace", fontsize=8)
    _finish(fig, save_path, show)
    return fig


def plot_initial_final(start: State, final: State, truck: Truck, catalog: Dict[str, Package],
                       suptitle: str = "", save_path: Optional[str] = None, show: bool = False):
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1.3])
    draw_state(fig.add_subplot(gs[0, 0], projection="3d"), start, truck, catalog, "State Awal")
    draw_state(fig.add_subplot(gs[0, 1], projection="3d"), final, truck, catalog, "State Akhir")
    for col, st in enumerate((start, final)):
        axt = fig.add_subplot(gs[1, col]); axt.axis("off")
        axt.text(0, 1, _info_text(st, truck, catalog), va="top", family="monospace", fontsize=8)
    if suptitle:
        fig.suptitle(suptitle)
    _finish(fig, save_path, show)
    return fig


# ---------- plot hasil eksperimen ----------
def plot_objective(histories: Dict[str, List[float]], title: str = "Objective function vs iterasi",
                   ylabel: str = "Objective function", save_path: Optional[str] = None, show: bool = False):
    """histories: {'Run 1': [...], 'Run 2': [...]} -> satu garis per run."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, hist in histories.items():
        ax.plot(range(len(hist)), hist, label=label, linewidth=1)
    ax.set_xlabel("Iterasi"); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(alpha=0.3); ax.legend()
    _finish(fig, save_path, show)
    return fig


def plot_sa_prob(prob_histories: Dict[str, List[Tuple[int, float]]],
                 title: str = "Simulated Annealing: e^(dE/T) vs iterasi",
                 save_path: Optional[str] = None, show: bool = False):
    """prob_histories: {'Run 1': [(iter, p), ...]} (hanya move yang lebih buruk)."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, pts in prob_histories.items():
        if pts:
            ax.scatter([i for i, _ in pts], [p for _, p in pts], s=4, alpha=0.5, label=label)
    ax.set_xlabel("Iterasi"); ax.set_ylabel("e^(dE/T)"); ax.set_ylim(0, 1.02)
    ax.set_title(title); ax.grid(alpha=0.3);
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, markerscale=3)
    _finish(fig, save_path, show)
    return fig


def plot_ga_progress(max_history: List[float], avg_history: List[float],
                     title: str = "Genetic Algorithm: objective populasi",
                     save_path: Optional[str] = None, show: bool = False):
    """nilai objective maksimum & rata-rata populasi per generasi."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(max_history, label="Maksimum"); ax.plot(avg_history, label="Rata-rata")
    ax.set_xlabel("Iterasi (generasi)"); ax.set_ylabel("Objective function")
    ax.set_title(title); ax.grid(alpha=0.3); ax.legend()
    _finish(fig, save_path, show)
    return fig


def plot_final_comparison(results: Dict[str, List[float]], title: str = "Perbandingan nilai akhir",
                          save_path: Optional[str] = None, show: bool = False):
    """results: {'Steepest': [v1, v2, v3], 'SA': [...], 'GA': [...]} -> titik tiap run + rata-rata."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (name, vals) in enumerate(results.items()):
        ax.scatter([i] * len(vals), vals, alpha=0.7)
        ax.hlines(sum(vals) / len(vals), i - 0.25, i + 0.25, colors="black")
    ax.set_xticks(range(len(results))); ax.set_xticklabels(list(results.keys()))
    ax.set_ylabel("Objective akhir"); ax.set_title(title); ax.grid(alpha=0.3)
    _finish(fig, save_path, show)
    return fig