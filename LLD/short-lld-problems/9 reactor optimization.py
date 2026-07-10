"""
RIPPLING / SCIENTIFIC CODING — Isothermal Reactor Optimization
==============================================================
Parallel reactions A → B (desired) and A → C (undesired).
Optimize temperature T and residence time t_res to maximize net economic benefit.

Uses scipy.integrate.solve_ivp + scipy.optimize.minimize.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

# --- feed & kinetics ---
A0 = 3.0  # M
B0 = 0.0  # M
C0 = 0.0  # M
Ea1 = 6.0  # kcal/mol  (A → B)
Ea2 = 8.0  # kcal/mol  (A → C, higher Ea → selectivity to C worsens at high T)
k1 = 30.0  # 1/s  (pre-exponential)
k2 = 90.0  # 1/s
R = 0.001987  # kcal/(mol·K)  (not given in prompt; standard with kcal/mol Ea)

# --- economics ---
reactant_cost = 50.0  # $/M of A fed
reactor_operating_cost = 200.0  # $/minute
product_benefit = 200.0  # $/M of B
cost_purify_reuse_A = 5.0  # $/M of unreacted A
cost_safely_dispose_waste_C = 1.0  # $/M of C


def _rates(T: float, A: float) -> tuple[float, float, float]:
    """Return (dA/dt, dB/dt, dC/dt) at temperature T (K)."""
    k1_T = k1 * math.exp(-Ea1 / (R * T))
    k2_T = k2 * math.exp(-Ea2 / (R * T))
    dB = k1_T * A
    dC = k2_T * A
    dA = -(dB + dC)
    return dA, dB, dC


def dBdt(A: float, B: float, t: float, T: float) -> float:
    return _rates(T, A)[1]


def dCdt(A: float, B: float, t: float, T: float) -> float:
    return _rates(T, A)[2]


def dAdt(A: float, B: float, t: float, T: float) -> float:
    return _rates(T, A)[0]


def _ode_system(t: float, y: np.ndarray, T: float) -> list[float]:
    A, B, C = y
    dA, dB, dC = _rates(T, A)
    return [dA, dB, dC]


def solve_reactor(T: float, t_res: float, n_points: int = 200):
    """Integrate batch reactor to residence time t_res (seconds)."""
    t_eval = np.linspace(0.0, t_res, n_points) if n_points > 1 else None
    sol = solve_ivp(
        _ode_system,
        (0.0, t_res),
        [A0, B0, C0],
        args=(T,),
        t_eval=t_eval,
        method="RK45",
        rtol=1e-8,
        atol=1e-10,
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol


def net_benefit_per_M_A(A: float, B: float, C: float, t_res: float) -> float:
    """
    Total benefits minus total costs, normalized per M of A in the feed.
    t_res in seconds; operating cost uses minutes.
    """
    t_min = t_res / 60.0
    total = (
        product_benefit * B
        - reactant_cost * A0
        - cost_purify_reuse_A * A
        - cost_safely_dispose_waste_C * C
        - reactor_operating_cost * t_min
    )
    return total / A0


def _objective(x: np.ndarray) -> float:
    T, t_res = float(x[0]), float(x[1])
    if T <= 0 or t_res <= 0:
        return 1e12
    try:
        A, B, C = solve_reactor(T, t_res, n_points=2).y[:, -1]
    except RuntimeError:
        return 1e12
    return -net_benefit_per_M_A(A, B, C, t_res)


def find_optimum():
    """Multi-start L-BFGS-B — objective can be non-convex."""
    bounds = [(400.0, 1500.0), (1.0, 600.0)]  # T [K], t_res [s]
    best = None
    for T0 in (500.0, 700.0, 900.0, 1100.0):
        for t0 in (10.0, 60.0, 180.0, 300.0):
            result = minimize(
                _objective,
                x0=[T0, t0],
                bounds=bounds,
                method="L-BFGS-B",
            )
            if best is None or result.fun < best.fun:
                best = result
    return best


def plot_profiles(T: float, t_res: float, path: str) -> None:
    sol = solve_reactor(T, t_res, n_points=300)
    A, B, C = sol.y
    t = sol.t

    plt.figure(figsize=(8, 5))
    plt.plot(t, A, label="A", linewidth=2)
    plt.plot(t, B, label="B (product)", linewidth=2)
    plt.plot(t, C, label="C (waste)", linewidth=2)
    plt.xlabel("Time (s)")
    plt.ylabel("Concentration (M)")
    plt.title(f"Reactor profiles at T = {T:.1f} K, t_res = {t_res:.2f} s")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    opt = find_optimum()
    T_opt, t_res_opt = opt.x
    sol = solve_reactor(T_opt, t_res_opt, n_points=2)
    A_f, B_f, C_f = sol.y[:, -1]
    net = net_benefit_per_M_A(A_f, B_f, C_f, t_res_opt)

    print("Optimal reactor conditions:")
    print(f"  T     = {T_opt:.2f} K")
    print(f"  t_res = {t_res_opt:.4f} s  ({t_res_opt / 60:.4f} min)")
    print()
    print("Final concentrations at optimal conditions:")
    print(f"  A = {A_f:.6f} M")
    print(f"  B = {B_f:.6f} M")
    print(f"  C = {C_f:.6f} M")
    print()
    print(f"Net benefit per M of A input = ${net:.4f}/M")

    plot_path = "reactor_profiles_optimal.png"
    plot_profiles(T_opt, t_res_opt, plot_path)
    print(f"\nFollow-up plot saved to: {plot_path}")


if __name__ == "__main__":
    main()
