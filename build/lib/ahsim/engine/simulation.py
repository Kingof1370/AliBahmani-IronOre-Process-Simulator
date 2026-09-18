"""Plant simulation engine (Spec Sections 08, 42-48, 91, 98, 101, 105).

Executes the default dry-magnetic circuit of Section 15 with a real recycle
loop, computes per-unit mass & Fe balances, plant balance, recovery,
circulating load and production figures. Results are snapshotted immutably
with input/result hashes (Section 98).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.params import Parameter, ValidationError
from ..models.psd import PSD
from ..models.stream import Stream
from ..models.equipment import MagneticSeparator, Screen, HydroconeCrusher
from ..models.graph import build_default_plant, FeedDistribution
from .recycle import SolverSettings, solve_recycle, SolverResult


@dataclass
class PlantConfig:
    feed_rate_t_h: float = 600.0           # user configurable, never hard-coded
    feed_fe_pct: float = 18.5
    moisture_pct: float = 0.5
    ore_density_t_m3: float = 2.9
    operating_hours_day: float = 20.0
    operating_days_month: float = 26.0
    operating_days_year: float = 330.0
    magnetite_fe_share: float = 0.75   # share of Fe in magnetite phase (USER INPUT)

    def as_dict(self):
        return dict(self.__dict__)


class SimulationEngine:
    """Runs the full circuit and produces a validated result snapshot."""

    def __init__(self, config: PlantConfig = None):
        self.cfg = config or PlantConfig()
        self.plant = build_default_plant()
        self.gyratory = HydroconeCrusher("GYRATORY", "PRIMARY")
        self.gyratory.css_mm.value = 200.0   # primary gyratory close-side setting, USER INPUT
        self.distribution = FeedDistribution(6)
        self.solver_settings = SolverSettings()
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.status = "READY"

    # ------------------------------------------------------------------ run --
    def run(self, feed_psd: PSD = None) -> "SimulationResult":
        cfg = self.cfg
        self.warnings, self.errors = [], []
        if cfg.feed_rate_t_h <= 0:
            raise ValidationError("feed rate must be > 0")
        psd = feed_psd or PSD.default()
        psd.validate()

        pre_seps = self.plant["pre_separators"]
        screens = self.plant["screens"]
        coarse, fine = self.plant["coarse_crusher"], self.plant["fine_crusher"]
        finals = self.plant["final_separators"]
        shares = self.distribution.shares()

        rec_psd_holder = {"psd": None}

        def circuit(recycle_dry: float, recycle_fe: float):
            """One pass through the circuit including the recycle stream.
            Returns (new_recycle_dry_t_h, new_recycle_fe_pct, streams dict)."""
            streams: Dict[str, Stream] = {}

            def mk(sid, dry, fe, psd_, src, dst, moist=cfg.moisture_pct):
                s = Stream(stream_id=sid, source_equipment=src, destination_equipment=dst,
                           moisture_pct=moist, fe_grade_pct=fe, psd=psd_)
                s.set_dry_mass_flow(dry, moist)
                s.reconcile_psd_fe()   # grade/PSD consistency rule (Fe balance integrity)
                streams[sid] = s
                return s

            # Primary gyratory crushing -> distribution node
            gyr_psd = self.gyratory.product_psd(psd)
            gyr_out = mk("S-GYR", cfg.feed_rate_t_h, cfg.feed_fe_pct, gyr_psd, "GYRATORY", "DISTRIBUTION")

            seps_out = []
            for i, (sep, share) in enumerate(zip(pre_seps, shares), start=1):
                sub = mk(f"S-PRE{i}-IN", gyr_out.dry_mass_flow_t_h * share, cfg.feed_fe_pct,
                         gyr_out.psd.copy(), "DISTRIBUTION", sep.sep_id)
                m, t = sep.process(sub, (f"S-PRE{i}-MAG", f"S-PRE{i}-TAIL"),
                                   magnetite_fe_share=cfg.magnetite_fe_share)
                streams[f"S-PRE{i}-MAG"], streams[f"S-PRE{i}-TAIL"] = m, t
                seps_out.append(m)

            merged = seps_out[0].copy("S-MERGE")
            for s in seps_out[1:]:
                merged = merged.mix(s, "S-MERGE", "PRE-SEPARATORS", "SCREENS")
            streams["S-MERGE"] = merged

            rec_psd = rec_psd_holder["psd"] if rec_psd_holder["psd"] is not None else gyr_out.psd.copy()
            rec = mk("S-RECYCLE-IN", recycle_dry, recycle_fe, rec_psd.copy(), "RECYCLE", "SCREENS")
            screen_feed = merged.mix(rec, "S-SCR-FEED", "MERGER", "SCREENS")
            streams["S-SCR-FEED"] = screen_feed

            unders, overs = [], []
            scr_share = 1.0 / len(screens)
            for i, scr in enumerate(screens, start=1):
                sub = mk(f"S-SCR{i}-IN", screen_feed.dry_mass_flow_t_h * scr_share,
                         screen_feed.fe_grade_pct, screen_feed.psd.copy(), "MERGER", scr.screen_id)
                u, o = scr.process(sub, (f"S-SCR{i}-UND", f"S-SCR{i}-OV"))
                streams[f"S-SCR{i}-UND"], streams[f"S-SCR{i}-OV"] = u, o
                unders.append(u)
                overs.append(o)

            fines = unders[0].copy("S-FINES")
            for s in unders[1:]:
                fines = fines.mix(s, "S-FINES", "SCREENS", "FINAL-SEPARATORS")
            streams["S-FINES"] = fines

            coarse_ov = overs[0].copy("S-OV-COARSE")
            for s in overs[1:]:
                coarse_ov = coarse_ov.mix(s, "S-OV-COARSE", "SCREENS", "HYD-COARSE")
            streams["S-OV-COARSE"] = coarse_ov

            c_out = coarse.process(coarse_ov, "S-COARSE-OUT")
            streams["S-COARSE-OUT"] = c_out
            f_out = fine.process(c_out, "S-FINE-OUT")
            streams["S-FINE-OUT"] = f_out
            rec_psd_holder["psd"] = f_out.psd.copy()
            return f_out.dry_mass_flow_t_h, f_out.fe_grade_pct, streams

        # ---------------- solve recycle (Section 36-37) ----------------
        solver = solve_recycle(0.0, cfg.feed_fe_pct, circuit, self.solver_settings)
        seed = solver.history[-1] if solver.history else {"recycle_t_h": 0.0,
                                                          "recycle_fe_pct": cfg.feed_fe_pct}
        _, _, streams = circuit(seed["recycle_t_h"], seed["recycle_fe_pct"])

        # ---------------- final magnetic separation (Section 39) --------
        fines = streams["S-FINES"]
        products, tails = [], []
        for i, fs in enumerate(finals, start=1):
            sub = Stream(stream_id=f"S-FIN{i}-IN", source_equipment="MERGER",
                         destination_equipment=fs.sep_id, moisture_pct=fines.moisture_pct,
                         fe_grade_pct=fines.fe_grade_pct, psd=fines.psd.copy())
            sub.set_dry_mass_flow(fines.dry_mass_flow_t_h * 0.5, fines.moisture_pct)
            streams[f"S-FIN{i}-IN"] = sub
            p, t = fs.process(sub, (f"S-PRODUCT-{i}", f"S-TAIL-{i}"),
                              magnetite_fe_share=cfg.magnetite_fe_share)
            products.append(p)
            tails.append(t)
            streams[f"S-PRODUCT-{i}"], streams[f"S-TAIL-{i}"] = p, t

        product = products[0].copy("S-PRODUCT")
        for s in products[1:]:
            product = product.mix(s, "S-PRODUCT", "FINAL-SEPARATORS", "PRODUCT_SILO")
        # Total plant tailings = pre-processing rejects + final separator tails
        pre_tails = [streams[f"S-PRE{i}-TAIL"] for i in range(1, 7)]
        fin_tail = tails[0].copy("S-TAIL-FIN")
        for s in tails[1:]:
            fin_tail = fin_tail.mix(s, "S-TAIL-FIN", "FINAL-SEPARATORS", "TAILINGS")
        pre_tail = pre_tails[0].copy("S-TAIL-PRE")
        for s in pre_tails[1:]:
            pre_tail = pre_tail.mix(s, "S-TAIL-PRE", "PRE-SEPARATORS", "TAILINGS")
        tail = pre_tail.mix(fin_tail, "S-TAIL", "PLANT", "TAILINGS")
        streams["S-TAIL-FIN"], streams["S-TAIL-PRE"], streams["S-TAIL"] = fin_tail, pre_tail, tail
        streams["S-PRODUCT"] = product

        feed = Stream(stream_id="S-FEED", source_equipment="ENV", destination_equipment="GRIZZLY",
                      moisture_pct=cfg.moisture_pct, fe_grade_pct=cfg.feed_fe_pct, psd=psd.copy())
        feed.set_dry_mass_flow(cfg.feed_rate_t_h, cfg.moisture_pct)
        streams["S-FEED"] = feed

        kpis = self._kpis(streams, solver)
        auto_w = self._auto_warnings(kpis, solver)
        status = self._status(kpis, solver)

        return SimulationResult(
            simulation_id=str(uuid.uuid4())[:8].upper(),
            timestamp=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            config=cfg, streams=streams, solver=solver, kpis=kpis,
            warnings=self.warnings + auto_w, errors=self.errors, status=status,
        )

    # ------------------------------------------------------------------ KPI --
    def _kpis(self, streams: Dict[str, Stream], solver: SolverResult) -> dict:
        feed, product, tail = streams["S-FEED"], streams["S-PRODUCT"], streams["S-TAIL"]
        recycle = streams["S-FINE-OUT"]
        cfg = self.cfg
        fd, pd, td = feed.dry_mass_flow_t_h, product.dry_mass_flow_t_h, tail.dry_mass_flow_t_h
        screen_feed = streams["S-SCR-FEED"].dry_mass_flow_t_h
        crusher_feed = streams["S-OV-COARSE"].dry_mass_flow_t_h
        mass_rec = (pd / fd * 100.0) if fd > 0 else 0.0
        fe_in = feed.fe_mass_flow_t_h
        fe_rec = (product.fe_mass_flow_t_h / fe_in * 100.0) if fe_in > 0 else 0.0
        cl_t_h = recycle.dry_mass_flow_t_h
        cl_pct = (cl_t_h / fd * 100.0) if fd > 0 else 0.0
        prod_day = pd * cfg.operating_hours_day
        return {
            "feed_t_h": fd, "product_t_h": pd, "tail_t_h": td,
            "product_fe_pct": product.fe_grade_pct, "tail_fe_pct": tail.fe_grade_pct,
            "mass_recovery_pct": mass_rec, "fe_recovery_pct": fe_rec,
            "fe_in_t_h": fe_in, "fe_product_t_h": product.fe_mass_flow_t_h,
            "fe_tail_t_h": tail.fe_mass_flow_t_h,
            "circulating_load_t_h": cl_t_h, "circulating_load_pct": cl_pct,
            "screen_load_t_h": screen_feed, "crusher_load_t_h": crusher_feed,
            "separator_load_t_h": [streams[f"S-PRE{i}-IN"].dry_mass_flow_t_h for i in range(1, 7)],
            "final_separator_load_t_h": [streams[f"S-FIN{i}-IN"].dry_mass_flow_t_h for i in (1, 2)],
            "production_t_day": prod_day,
            "production_t_month": prod_day * cfg.operating_days_month,
            "production_t_year": prod_day * cfg.operating_days_year,
            "mass_balance_error_pct": self._balance_error(fd, pd, td),
            "fe_balance_error_pct": self._fe_balance_error(
                fe_in, product.fe_mass_flow_t_h, tail.fe_mass_flow_t_h),
        }

    @staticmethod
    def _balance_error(feed, product, tail):
        if feed <= 0:
            return 0.0
        return abs(feed - (product + tail)) / feed * 100.0

    @staticmethod
    def _fe_balance_error(fe_in, fe_prod, fe_tail):
        if fe_in <= 0:
            return 0.0
        return abs(fe_in - (fe_prod + fe_tail)) / fe_in * 100.0

    def _auto_warnings(self, kpis, solver) -> List[str]:
        w = []
        if solver.status != "CONVERGED":
            w.append("RECYCLE SOLVER: NOT CONVERGED - results are NOT final (Section 38)")
        if any(s.capacity_t_h.value == 0.0 for s in
               self.plant["pre_separators"] + self.plant["final_separators"]):
            w.append("Separator capacity = CALIBRATION REQUIRED (no manufacturer/test data)")
        if kpis["mass_recovery_pct"] > 100.0 or kpis["fe_recovery_pct"] > 100.0:
            w.append("Recovery > 100% - invalid partition parameters")
        if self.gyratory.capacity_t_h.value == 0.0:
            w.append("GYRATORY capacity = CALIBRATION REQUIRED (no manufacturer data)")
        return w

    def _status(self, kpis, solver) -> str:
        if self.errors:
            return "ERROR"
        if solver.status != "CONVERGED":
            return "NOT CONVERGED"
        if kpis["mass_balance_error_pct"] > 1.0 or kpis["fe_balance_error_pct"] > 1.0:
            return "CONVERGED WITH WARNINGS"
        return "CONVERGED"


@dataclass
class SimulationResult:
    """Immutable snapshot (Section 98)."""
    simulation_id: str
    timestamp: str
    config: PlantConfig
    streams: Dict[str, Stream]
    solver: SolverResult
    kpis: dict
    warnings: List[str]
    errors: List[str]
    status: str
    input_hash: str = ""
    result_hash: str = ""

    def __post_init__(self):
        payload_in = json.dumps(self.config.as_dict(), sort_keys=True, default=str)
        self.input_hash = hashlib.sha256(payload_in.encode()).hexdigest()[:16]
        payload_out = json.dumps({k: v.as_dict() for k, v in self.streams.items()},
                                 sort_keys=True, default=str)
        self.result_hash = hashlib.sha256(payload_out.encode()).hexdigest()[:16]

    def summary(self) -> dict:
        return {
            "simulation_id": self.simulation_id, "timestamp": self.timestamp,
            "status": self.status, "solver_status": self.solver.status,
            "iterations": self.solver.iterations,
            "input_hash": self.input_hash, "result_hash": self.result_hash,
            **self.kpis, "warnings": self.warnings,
        }
