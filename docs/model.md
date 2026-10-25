# Model and source guide

Original coursework: 2021. Documentation and independent reserve check: 2026.

## Reserve uncertainty

The workbook gives each prospect a success probability $p$, lognormal location $\mu$ and scale $\sigma$. Its displacement column is zero for the included inputs. For the independent prior model,

$$
Q=I\exp(\mu+\sigma Z),\quad I\perp Z,
$$

$$
E[Q]=p e^{\mu+\sigma^2/2},\qquad
\mathrm{Var}(Q)=p e^{2\mu+2\sigma^2}-p^2 e^{2\mu+\sigma^2}.
$$

The point mass at zero represents geological failure. Conditional on success, the positive reserve is lognormal. `data_input` uses the mixture expectation and `recon_results_create` samples a Bernoulli success followed by a lognormal reserve.

The new `scripts/reserve_audit.py` independently checks this prior model against the supplied data. It uses a local NumPy generator, a specified seed and the analytic variance to report the standard error of the simulated mean. That error measures finite Monte Carlo noise, not uncertainty in the geological parameters.

## Timing and economic decisions

The archive models exploration and construction on a monthly timeline. Exploration reveals information; delivery options have different fixed costs, operating costs, capacities and construction delays. Annual cash flows are discounted by a factor of the form $(1+r)^{-k}$.

| Original function | Responsibility |
| --- | --- |
| `data_input` | Read workbook inputs and calculate reserve / money expectations |
| `recon_results_create` | Simulate geological success and revealed reserves |
| `recon_set`, `timeline_build_update` | Place exploration and construction events on the timeline |
| `income_per_month`, `expenses_per_month` | Calculate operational income and investment costs |
| `end_of_year` | Apply the archived tax/loss rule and discount annual cash flow |
| `simulation_cars_pipe` | Simulate switching from trucks to a pipeline |
| `simulation_cars_cars` | Simulate continued truck delivery |
| `simulation_cars_none` | Simulate stopping the project |
| `point_simulation` | Compare three actions at a candidate decision date |
| `main` | Search candidate decision dates |

## What the policy rule actually optimises

Within `point_simulation`, an action receives a point whenever its NPV is the largest among the three actions for that simulated scenario. The selected action maximises this win count, with fixed tie priorities. Its average NPV is then reported. This is a probability-of-being-best heuristic, not the same objective as maximising expected NPV.

The outer loop searches dates using sampled averages. Using the same simulations for choosing and reporting a policy can produce selection optimism. A future revision should choose the objective explicitly, use common scenarios for paired comparisons, then evaluate the selected policy on independent simulations.

## Issues retained in the archive

- `uplifts_oil_update_generation_with_considering_reconed_wells` samples a lognormal value for unrevealed prospects without the Bernoulli failure draw used elsewhere. This changes the distribution.
- The inner decision routine uses only 5 or 20 draws, depending on its flag. Such small samples cannot support precise outcome estimates or close policy comparisons.
- Several helper routines depend on mutable globals. Reproducing a policy comparison requires controlling state as well as random seeds.
- The workbook has an `.xlsx` suffix but contains an OpenDocument archive. Explicit format detection is needed with modern readers.
- The tax/loss rule and cash-flow units should be reviewed before drawing economic conclusions.

The 2026 distribution check is separate from the archived policy engine and does not silently repair its results. A complete policy rerun and financial validation remain future work.
