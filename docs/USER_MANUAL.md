# User Manual - AliBahmani IronOre Process Simulator v1.0.0
Developer: Ali Bahmani - Contact: 09915420558

## Quick start (headless / API)
```python
from ahsim.engine.simulation import SimulationEngine, PlantConfig
cfg = PlantConfig(feed_rate_t_h=600.0, feed_fe_pct=18.5, moisture_pct=0.5)
res = SimulationEngine(cfg).run()          # full circuit incl. recycle solve
res.kpis                                   # dashboard metrics
res.streams["S-PRODUCT"].fe_grade_pct      # stream-by-stream access
```
## Outputs
- Excel (26 sheets): `python scripts/make_release.py` -> RELEASE/EXCEL_REPORTS
- DXF (14 layers + title block): RELEASE/CAD_OUTPUT
- PDF report: RELEASE/TEST_REPORTS
- MP4 animation (1920x1080 H.264): RELEASE/VIDEO_OUTPUT
## Units
Feed rate accepts kg/s, kg/min, kg/h, t/h, t/day, t/month, t/year (convert via
`ahsim.core.units.convert`). Magnetic field: Gauss <-> Tesla (1 T = 10000 G).
## Data policy
Every parameter carries a Source Classification. Capacity, power and pole
geometry of the custom separators are UNKNOWN / CALIBRATION REQUIRED until you
enter manufacturer or site data. Results are MODEL RESULT, not SITE VERIFIED,
until calibration testwork is loaded (Calibration sheet 20).
