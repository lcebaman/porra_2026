# OSU Collectives Sweep

Benchmarking toolkit for MPI collective operations across a sweep of
**tasks-per-node** values and **stack configurations**, built around the
OSU Micro-Benchmarks (OMB) collective tests. Designed for the modern
UCX → UCC → OpenMPI stack (no hcoll).

The methodology mirrors the kind of latency-vs-ranks-per-node analysis
shown in MPI vendor documentation for high-core-count CPUs, but extends
it to compare multiple stack configurations side by side and produces a
richer set of diagnostic plots.

## Contents

| File | Purpose |
|---|---|
| `run_osu_collectives_sweep.sh` | Slurm batch driver. Loops over configurations × ppn × collectives, writes one CSV per collective. |
| `configs.txt` | Configuration matrix. Each line defines a `name | mca_args | env_vars` triplet. |
| `plot_osu_sweep.py` | Plotter. Produces nine families of figures plus an HTML index. |

## Quick start

```bash
# 1. Edit configs.txt and the SBATCH header in run_osu_collectives_sweep.sh
#    (nodes, partition, account, cores per node).

# 2. Point OSU_ROOT at your OMB install (or leave the default).
export OSU_ROOT=$HOME/sw/osu-micro-benchmarks/7.5

# 3. Submit.
sbatch run_osu_collectives_sweep.sh

# 4. Plot.
python3 plot_osu_sweep.py results/<timestamp>_<jobid>/

# 5. Browse.
xdg-open results/<timestamp>_<jobid>/index.html
```

## The sweep matrix

Three nested loops:

```
for config in configs.txt:           # outer: stack configuration
    for ppn in PPN_LIST:             # middle: tasks per node
        for collective in COLLECTIVES:   # inner: OSU collective
            srun --ntasks-per-node=$ppn $OSU/$collective -m 8:1M
```

Default dimensions on a 192-core node, 16-node allocation:

- **9 configurations** (see `configs.txt`): tuned baseline, HAN, UCC basic, UCC hier, UCC hier with algorithm overrides, UCC hier with UCX transport variations
- **11 ppn values**: 1, 2, 4, 8, 16, 32, 64, 96, 128, 192, fully-populated
- **6 collectives**: allreduce, alltoall, allgather, bcast, reduce, barrier
- **~17 message sizes** per OSU run: 8 B to 1 MiB

That's ~9 × 11 × 6 = 594 OSU invocations per submission. Plan ~30 minutes
to ~6 hours depending on system size and `OSU_ITERATIONS`.

## Configuration file format

`configs.txt` is pipe-separated, three fields per line:

```
name | mca_args | env_vars
```

- `name` — short token; becomes a CSV column value and figure filename
- `mca_args` — extra arguments passed to the launcher (typically `--mca key val` pairs)
- `env_vars` — space-separated `KEY=VALUE` pairs exported before launch

Lines starting with `#` and blank lines are ignored. Quoting is not supported,
so keep values simple. Example:

```
ucc_hier_dc | --mca coll_ucc_enable 1 --mca coll_ucc_priority 100 | UCC_CLS=basic,hier UCC_TLS=ucp,self,shm UCX_TLS=dc,sm,self
```

The shipped `configs.txt` covers the meaningful axes of the UCX/UCC/OMPI stack:

| Config | What it tests |
|---|---|
| `tuned_default` | OMPI tuned collectives, no UCC. Baseline. |
| `tuned_han` | OMPI tuned + HAN hierarchical framework, no UCC. |
| `ucc_basic_ucp` | UCC with flat collective layer over UCP transport. |
| `ucc_hier` | UCC with hierarchical CL — the big lever for high ppn. |
| `ucc_hier_knomial` | Force knomial allreduce algorithm. |
| `ucc_hier_ring` | Force ring allreduce (BW-bound regime). |
| `ucc_hier_rc` / `ucc_hier_dc` / `ucc_hier_rcx` | UCX transport sweep — RC vs DC vs accelerated RC. |

## Tuning knobs in the driver script

All overridable via environment variables, all with sensible defaults:

| Variable | Default | Purpose |
|---|---|---|
| `OSU_ROOT` | `$HOME/sw/osu-micro-benchmarks/7.5` | Path to OMB install |
| `CORES_PER_NODE` | `192` | Maximum ppn; tailor to your hardware |
| `MSG_RANGE` | `8:1048576` | OSU `-m` argument: min:max bytes |
| `OSU_ITERATIONS` | `1000` | Measurement iterations per data point |
| `OSU_WARMUP` | `200` | Warmup iterations |
| `CONFIG_FILE` | `configs.txt` | Configuration matrix |
| `RESULTS_DIR` | `results/<timestamp>_<jobid>` | Output directory |
| `LAUNCHER` | `srun` | `srun` or `mpirun` |

`PPN_LIST` and `COLLECTIVES` are bash arrays edited at the top of the script
rather than env vars.

## Output

Each submission writes one CSV per collective with the canonical schema:

```
config,collective,ppn,total_ranks,msg_size,avg_us,min_us,max_us,iterations
```

Plus per-(config × ppn × collective) raw OSU output files for forensic
inspection, and one `.env` file per configuration recording all
`OMPI_*` / `UCX_*` / `UCC_*` / `PMIX_*` / `SLURM_JOB_*` variables that
were in scope at run time — so each result is reproducible.

The configuration file is copied into the results directory as
`configs.txt` so the run's matrix is self-documenting.

## Plot families

The plotter produces nine figure families per collective plus an HTML
index. Each family answers a different question:

| Family | Question | Notes |
|---|---|---|
| Absolute latency (vs ppn) | How does latency scale with ranks per node? | One figure per representative message size. |
| Absolute latency (vs msg size) | What's the latency vs message size curve at each ppn? | Log-log; reveals eager/rendezvous protocol knees. |
| Latency with min/max bands | Is this difference real or noise? | Shaded min/max around the avg curve. |
| Speedup vs baseline | How much faster is each config than the baseline? | Dashed line at speedup=1.0 is the threshold of interest. |
| Effective bandwidth | Are we saturating the fabric? | Collective-specific data factor (`2(N-1)/N · S` for allreduce, etc.). |
| Scaling efficiency | How badly does latency degrade with ppn relative to ppn=1? | Decouples scaling from absolute speed. |
| Cliff location | At what ppn does each config break? | Detected via the largest acceleration in log-space slope. |
| Best-config map | Which config wins per (ppn, msg_size) cell? | Direct input for UCC/OMPI dispatch rules. |
| Per-config heatmaps | Full (ppn × msg_size) latency landscape per config. | Shared colour scale across configs for direct comparison. |

## Plotter invocation modes

The plotter accepts three input shapes:

```bash
# 1. Sweep directory (the normal case):
python3 plot_osu_sweep.py results/20260516_123456_12345

# 2. A single CSV file (new schema or old schema without 'config' column):
python3 plot_osu_sweep.py results/.../osu_allreduce.csv

# 3. A raw OSU output file (auto-detected by '# OSU MPI ...' header):
python3 plot_osu_sweep.py allreduce.out
```

Optional:

```bash
--baseline <config_name>   # baseline for speedup plots
                           # default: first config alphabetically
```

When loading old-schema or raw input, the plotter synthesises a `config`
column and infers the collective from the filename. Speedup plots are
silently skipped when only one configuration is present.

## Requirements

**Runtime (driver script):**

- A Slurm cluster, or a system where `mpirun`/`srun` works directly
- OpenMPI built with UCC support (or another MPI; adjust `--mca` flags accordingly)
- UCX, UCC libraries installed
- OSU Micro-Benchmarks 7.x built against the target MPI
- bash 4+, awk

**Plotter:**

- Python 3.9+
- `pandas` ≥ 2.0 (uses post-1.5 idioms; avoids deprecated `applymap`)
- `numpy`
- `matplotlib`

## Troubleshooting

**`KeyError: 'config'` in the plotter** — old-schema CSV. Already handled
in current code; if it still fires, verify the CSV header line contains
the canonical columns. The plotter will inject `config="default"` and
proceed.

**`ERROR: not a directory` / `not found`** — pass either a results
directory, a single CSV file, or a raw OSU output file. The error
message lists all three options.

**Failed runs at high ppn** — usually one of:
- IB QP exhaustion → reduce ppn, or switch to `UCX_TLS=dc,sm,self`
- Out of memory → check OSU's per-rank buffer requirements at large message sizes
- Slurm task-launch timeout → increase `--time` in the SBATCH header

When a `(config, ppn, collective)` combination fails, the driver logs
the failure and continues with the next combination rather than aborting
the whole job — so partial results are still useful.

**Latency cliff appears at unexpected ppn** — useful debugging steps:

1. Check the per-config `.env` files: confirm `UCX_TLS` / `UCC_CLS` got
   set as intended.
2. Rerun the suspect configuration with `UCC_LOG_LEVEL=info` to see
   which TL and CL UCC actually selected.
3. Compare the affected configuration's heatmap to a known-good one;
   cliff patterns differ between QP-cache pressure, CCD-boundary
   crossings, and algorithm switches.

**Configuration not picked up** — check `configs.txt` for stray
whitespace; the parser is fussy about the pipe-separated format. The
driver echoes each configuration's `mca` and `env` strings at the start
of the per-config block, so a misparse is visible in the job log.

## Methodology notes

**Why no hcoll** — assumes an UCX/UCC/OpenMPI stack built without
Mellanox hcoll. The `configs.txt` and driver are designed accordingly;
if you build OpenMPI with hcoll, you'd add `--mca coll_hcoll_enable 1`
to the relevant config row and a `hcoll_*` configuration to the matrix.

**Why these PPN values** — the default list deliberately includes
boundaries that matter on modern CPUs: 1 (baseline single-rank), 8
(one CCD on EPYC Genoa/Turin), 16, 32, 64, 96, 128 (typical IB QP-cache
crossover region), and fully populated. Edit `PPN_LIST` to add your
own CCD/NUMA boundaries.

**Why effective bandwidth not raw bandwidth** — for collectives, the
"bytes moved" depends on the algorithm. The plotter uses a per-collective
data factor (`2(N-1)/N · S` for allreduce, `(N-1) · S` for allgather,
etc.) that gives consistent comparisons across configurations even if
they pick different underlying algorithms. It's a lower-bound estimate,
not a precise model.

**Why log-space cliff detection** — latency-vs-ppn curves are usually
monotonically increasing, so a simple "biggest derivative" detector
just reports the highest ppn every time. Detecting acceleration in
log-log space catches the "smooth then sharp upturn" shape that
characterises a real cliff.

## Extending

**Adding a new configuration** — append a line to `configs.txt`. No
script changes needed.

**Adding a new collective** — append to the `COLLECTIVES` array at the
top of `run_osu_collectives_sweep.sh`. The plotter handles any
`osu_*` name automatically.

**Adding a new plot family** — write a `plot_xxx(df, ...)` function in
`plot_osu_sweep.py`, call it from `plot_one()`, and add a `(name, [patterns])`
entry to `family_order` in `build_index()` so the HTML index buckets it
correctly. Order in `family_order` is significant: more specific
patterns must come first.

**Comparing two sweeps** — not yet built. A `compare_runs.py` that
diffs two results directories and flags per-cell regressions is the
obvious next addition; ask if it'd be useful.

## License

Internal benchmarking tooling. No specific license attached; treat as
the property of whoever's filesystem you found it on.
