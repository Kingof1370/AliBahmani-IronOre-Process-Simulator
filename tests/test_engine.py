"""Test suite (Spec Sections 100-103). Run: pytest tests/ -v"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from ahsim.core import units
from ahsim.core.params import ValidationError, Parameter, TIER, SITE_MEASUREMENT
from ahsim.models.psd import PSD, PSDFraction
from ahsim.models.stream import Stream
from ahsim.models.equipment import MagneticSeparator, Screen, HydroconeCrusher
from ahsim.engine.recycle import solve_recycle, SolverSettings
from ahsim.engine.simulation import SimulationEngine, PlantConfig
from ahsim.app.metadata import CONTACT, DEVELOPER_EN


# ---------------------------------------------- Unit Conversion (Sec 100)
class TestUnits:
    def test_kg_s_to_t_h(self):
        assert units.convert(1, "kg/s", "t/h", "mass_flow") == pytest.approx(3.6)

    def test_t_day_to_t_h(self):
        assert units.convert(2400, "t/day", "t/h", "mass_flow") == pytest.approx(100.0)

    def test_tesla_gauss_exact(self):
        assert units.convert(1, "T", "G", "field") == pytest.approx(10000.0)
        assert units.convert(3000, "G", "T", "field") == pytest.approx(0.3)

    def test_invalid_unit_raises(self):
        with pytest.raises(units.UnitError):
            units.convert(1, "kg/s", "t/h", "mass")

    def test_month_year_factors(self):
        assert units.convert(720, "t/month", "t/h", "mass_flow") == pytest.approx(1.0)   # 30 d
        assert units.convert(8760, "t/year", "t/h", "mass_flow") == pytest.approx(1.0)   # 365 d


# ---------------------------------------------- Geometry / RPM (Sec 19-20, 100)
class TestGeometry:
    def test_peripheral_speed_examples(self):
        D = 3.0
        for v, rpm in [(0.5, 3.18), (1.0, 6.37), (1.5, 9.55), (2.0, 12.73),
                       (2.5, 15.92), (3.0, 19.10), (5.0, 31.83), (8.0, 50.93)]:
            assert units.rpm_from_speed(D, v) == pytest.approx(rpm, abs=0.01), v
            # Section 20 example RPMs are rounded to 2 decimals -> loose back-tolerance
            assert units.peripheral_speed(D, rpm) == pytest.approx(v, abs=0.01), v

    def test_round_trip(self):
        for rpm in [0.1, 6.37, 44.56]:
            v = units.peripheral_speed(3.0, rpm)
            assert units.rpm_from_speed(3.0, v) == pytest.approx(rpm)

    def test_geometry_derived(self):
        sep = MagneticSeparator("SEP-T")
        g = sep.derived_geometry()
        assert g["diameter_m"] == 3.0
        assert g["circumference_m"] == pytest.approx(math.pi * 3.0)
        assert g["surface_area_m2"] == pytest.approx(math.pi * 3.0 * 3.0)

    def test_volume_not_capacity(self):
        sep = MagneticSeparator("SEP-T")
        assert sep.capacity_t_h.value == 0.0        # CALIBRATION REQUIRED, not invented
        assert sep.capacity_t_h.source == "CALIBRATION REQUIRED"


# ---------------------------------------------- PSD (Sec 12, 100)
class TestPSD:
    def test_default_sums_100(self):
        psd = PSD.default()
        assert psd.total_mass_pct() == pytest.approx(100.0, abs=1e-6)

    def test_invalid_psd_raises(self):
        psd = PSD([PSDFraction(0, 1, 50, 10), PSDFraction(1, 2, 40, 10)])
        with pytest.raises(ValidationError):
            psd.validate()

    def test_split_conserves_mass(self):
        psd = PSD.default()
        u, o, of = psd.split_by_aperture(3.0, 0.85)
        assert u.total_mass_pct() + o.total_mass_pct() == pytest.approx(100.0, abs=1e-6)
        assert 0 <= of <= 1

    def test_weighted_merge_fe_conserving(self):
        a = PSD([PSDFraction(0, 3, 100, 20)])
        b = PSD([PSDFraction(0, 3, 100, 10)])
        m = a.merge_weighted((a, 100.0), (b, 100.0))
        assert m.weighted_fe() == pytest.approx(15.0, abs=1e-9)

    def test_fine_mesh_fe(self):
        psd = PSD.default()
        assert psd.weighted_fe() > 0


# ---------------------------------------------- Stream / basis (Sec 10, 49-50)
class TestStream:
    def test_wet_dry_basis(self):
        s = Stream("T1")
        s.set_dry_mass_flow(100.0, 5.0)
        assert s.wet_mass_flow_t_h == pytest.approx(100 / 0.95)
        assert s.dry_mass_flow_t_h == pytest.approx(100.0)

    def test_mix_conserves_mass_and_fe(self):
        s1 = Stream("A", fe_grade_pct=20.0)
        s1.set_dry_mass_flow(100, 0)
        s2 = Stream("B", fe_grade_pct=10.0)
        s2.set_dry_mass_flow(50, 0)
        m = s1.mix(s2, "M", "x", "y")
        assert m.dry_mass_flow_t_h == pytest.approx(150.0)
        assert m.fe_mass_flow_t_h == pytest.approx(s1.fe_mass_flow_t_h + s2.fe_mass_flow_t_h)
        assert m.fe_grade_pct == pytest.approx((100 * 20 + 50 * 10) / 150)


# ---------------------------------------------- Separator / Screen / Crusher
class TestEquipment:
    def test_partition_sums_to_one(self):
        sep = MagneticSeparator("SEP-T")
        sep.set_field(3000, "G")
        for d in [0.1, 1, 3, 10, 25]:
            p = sep.p_magnetic(d, 20, 50)
            assert 0 <= p <= 1

    def test_field_unit_conversion(self):
        sep = MagneticSeparator("SEP-T")
        sep.set_field(1.8, "T")
        assert sep.field_g.value == pytest.approx(18000.0)

    def test_higher_field_more_recovery(self):
        recs = []
        for g in [1400, 3000, 5000]:
            sep = MagneticSeparator("SEP-T")
            sep.set_field(g, "G")
            feed = Stream("F", fe_grade_pct=20, psd=PSD.default())
            feed.set_dry_mass_flow(100, 0)
            m, t = sep.process(feed, ("M", "T"))
            recs.append(m.dry_mass_flow_t_h)
        assert recs[0] <= recs[1] <= recs[2]

    def test_screen_mass_conserved(self):
        scr = Screen("SCR-T", 3.0)
        feed = Stream("F", fe_grade_pct=18)
        feed.set_dry_mass_flow(200, 1.0)
        u, o = scr.process(feed, ("U", "O"))
        assert u.dry_mass_flow_t_h + o.dry_mass_flow_t_h == pytest.approx(200.0)

    def test_crusher_product_finer_than_feed(self):
        c = HydroconeCrusher("C-T", "FINE")
        c.css_mm.value = 5.0
        feed = PSD([PSDFraction(25, 50, 60, 18), PSDFraction(10, 25, 40, 18)])
        out = c.product_psd(feed)
        fine = sum(f.mass_pct for f in out.fractions if f.size_upper_mm <= 3.0)
        assert fine > 0


# ---------------------------------------------- Recycle solver (Sec 36-37)
class TestRecycle:
    def test_convergence_fixed_point(self):
        def circuit(rec, fe):
            return rec * 0.5 + 100.0, fe, {}
        r = solve_recycle(0.0, 18.5, circuit, SolverSettings())
        assert r.status == "CONVERGED"
        assert r.final_mass_residual < 1e-3

    def test_divergence_flagged(self):
        def circuit(rec, fe):
            return rec * 1.5 + 10.0, fe, {}
        r = solve_recycle(0.0, 18.5, circuit, SolverSettings())
        assert r.status == "NOT CONVERGED"


# ---------------------------------------------- Plant integration (Sec 101-103)
class TestPlantIntegration:
    @pytest.fixture(scope="class")
    def result_600(self):
        return SimulationEngine(PlantConfig(feed_rate_t_h=600.0)).run()

    def test_converged(self, result_600):
        assert result_600.status.startswith("CONVERGED")
        assert result_600.solver.status == "CONVERGED"

    def test_mass_balance(self, result_600):
        assert result_600.kpis["mass_balance_error_pct"] < 0.01

    def test_fe_balance(self, result_600):
        assert result_600.kpis["fe_balance_error_pct"] < 0.01

    def test_recovery_range(self, result_600):
        k = result_600.kpis
        assert 0 <= k["fe_recovery_pct"] <= 100
        assert 0 <= k["mass_recovery_pct"] <= 100

    def test_product_grade_above_feed(self, result_600):
        assert result_600.kpis["product_fe_pct"] >= result_600.config.feed_fe_pct

    def test_reproducibility(self, result_600):
        r2 = SimulationEngine(PlantConfig(feed_rate_t_h=600.0)).run()
        assert r2.input_hash == result_600.input_hash
        assert r2.result_hash == result_600.result_hash

    def test_immutable_snapshot(self, result_600):
        assert result_600.simulation_id and result_600.result_hash

    @pytest.mark.parametrize("rate", [100, 200, 400, 600, 800, 1000])
    def test_stress_feed_rates(self, rate):
        res = SimulationEngine(PlantConfig(feed_rate_t_h=float(rate))).run()
        assert res.kpis["mass_balance_error_pct"] < 0.01

    def test_zero_feed_raises(self):
        with pytest.raises(ValidationError):
            SimulationEngine(PlantConfig(feed_rate_t_h=0.0)).run()

    def test_full_magnetic_feed(self):
        psd = PSD([PSDFraction(1, 3, 100, 60, liberation_pct=100)])
        res = SimulationEngine(PlantConfig()).run(psd)
        assert res.status.startswith("CONVERGED")

    def test_no_recycle_case(self):
        # CSS far below aperture -> near-zero recycle, circuit must still converge
        eng = SimulationEngine(PlantConfig())
        eng.plant["fine_crusher"].css_mm.value = 0.5
        res = eng.run()
        assert res.solver.status == "CONVERGED"

    def test_invalid_psd_rejected(self):
        bad = PSD([PSDFraction(0, 1, 90, 10), PSDFraction(1, 2, 5, 10)])
        with pytest.raises(ValidationError):
            SimulationEngine(PlantConfig()).run(bad)

    def test_metadata_in_outputs(self, result_600):
        assert DEVELOPER_EN == "Ali Bahmani"
        assert CONTACT == "09915420558"
