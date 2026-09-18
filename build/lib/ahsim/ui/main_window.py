"""Desktop GUI for the AliBahmani IronOre Process Simulator (AH-SIM).

PySide6 application layer. It is deliberately thin: it reads the plant
parameters, calls the *unchanged* engineering engine in ``ahsim.engine`` and
displays the streams/KPIs; the export buttons call the same
``ahsim.outputs`` writers that ``scripts/make_release.py`` uses, so the GUI and
the batch route can never disagree.

If PySide6 is not importable the module raises ImportError and
``ahsim_app.py`` falls back to a console run - the engine stays usable headless.

Developer / Manufacturer: Ali Bahmani (علی بهمنی) - Contact: 09915420558
"""
from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QStatusBar, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..app.metadata import CONTACT, DEVELOPER_EN, DEVELOPER_FA, SOFTWARE_NAME, VERSION
from ..engine.simulation import PlantConfig, SimulationEngine

# Fields shown in the input panel: (attribute, label, unit, minimum, maximum,
# decimals, step)
FIELDS = [
    ("feed_rate_t_h", "Feed rate", "t/h", 1.0, 5000.0, 1, 50.0),
    ("feed_fe_pct", "Feed Fe grade", "%", 1.0, 70.0, 3, 0.5),
    ("moisture_pct", "Feed moisture", "%", 0.0, 20.0, 3, 0.1),
    ("ore_density_t_m3", "Ore density", "t/m3", 0.5, 8.0, 3, 0.1),
    ("magnetite_fe_share", "Fe in magnetite phase", "-", 0.0, 1.0, 3, 0.05),
    ("operating_hours_day", "Operating hours", "h/day", 1.0, 24.0, 1, 1.0),
    ("operating_days_month", "Operating days", "d/month", 1.0, 31.0, 1, 1.0),
    ("operating_days_year", "Operating days", "d/year", 1.0, 366.0, 1, 5.0),
]

STREAM_COLUMNS = [
    ("stream_id", "Stream"),
    ("source", "From"),
    ("destination", "To"),
    ("dry_mass_flow_t_h", "Dry t/h"),
    ("fe_grade_pct", "Fe %"),
    ("fe_mass_flow_t_h", "Fe t/h"),
    ("moisture_pct", "Moist %"),
    ("status", "Status"),
]

KPI_ORDER = [
    "feed_rate_t_h", "feed_fe_pct", "product_mass_flow_t_h", "product_fe_pct",
    "tailings_mass_flow_t_h", "tailings_fe_pct", "fe_recovery_pct",
    "mass_yield_pct", "mass_balance_error_pct", "fe_balance_error_pct",
    "circulating_load_pct", "annual_production_t",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.engine: SimulationEngine | None = None
        self.result = None
        self.spins: dict[str, QDoubleSpinBox] = {}

        self.setWindowTitle(f"{SOFTWARE_NAME} v{VERSION}")
        self.resize(1180, 720)

        self._build_menu()
        self._build_body()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            f"{SOFTWARE_NAME} v{VERSION} - {DEVELOPER_EN} | {CONTACT}"
        )
        self.log(f"{SOFTWARE_NAME} v{VERSION}")
        self.log(f"Developer / Manufacturer: {DEVELOPER_EN} ({DEVELOPER_FA})")
        self.log(f"Contact: {CONTACT}")
        self.log("Enter the plant parameters on the left, then press 'Run Simulation'.")

    # ---------------------------------------------------------------- layout --
    def _build_menu(self) -> None:
        run_menu = self.menuBar().addMenu("&Run")
        act_run = QAction("&Run Simulation", self)
        act_run.setShortcut("F5")
        act_run.triggered.connect(self.run_simulation)
        run_menu.addAction(act_run)

        act_all = QAction("Run + Export All (Excel, DXF, PDF, MP4)", self)
        act_all.triggered.connect(self.export_all)
        run_menu.addAction(act_all)
        run_menu.addSeparator()

        act_quit = QAction("E&xit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        run_menu.addAction(act_quit)

        file_menu = self.menuBar().addMenu("&File")
        act_open = QAction("Open Sample Project ...", self)
        act_open.triggered.connect(self.open_project)
        file_menu.addAction(act_open)

        help_menu = self.menuBar().addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self.about)
        help_menu.addAction(act_about)

    def _build_body(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        splitter = QSplitter(Qt.Horizontal)

        # ---- left: inputs -------------------------------------------------
        left = QWidget()
        left_layout = QVBoxLayout(left)

        box = QGroupBox("Plant parameters (USER INPUT)")
        form = QFormLayout(box)
        cfg = PlantConfig()
        for attr, label, unit, lo, hi, dec, step in FIELDS:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setDecimals(dec)
            spin.setSingleStep(step)
            spin.setValue(float(getattr(cfg, attr)))
            spin.setSuffix(f" {unit}" if unit != "-" else "")
            self.spins[attr] = spin
            form.addRow(label, spin)
        left_layout.addWidget(box)

        box2 = QGroupBox("Outputs")
        v2 = QVBoxLayout(box2)
        self.cb_excel = QCheckBox("Excel workbook (streams, equipment, KPIs)")
        self.cb_dxf = QCheckBox("CAD flowsheet (AutoCAD R2010 DXF)")
        self.cb_pdf = QCheckBox("Engineering report (PDF)")
        self.cb_mp4 = QCheckBox("Process animation (MP4 / H.264)")
        self.cb_sens = QCheckBox("Scenario + sensitivity study (JSON)")
        for cb in (self.cb_excel, self.cb_dxf, self.cb_pdf, self.cb_mp4, self.cb_sens):
            cb.setChecked(True)
            v2.addWidget(cb)
        left_layout.addWidget(box2)

        btn_run = QPushButton("Run Simulation")
        btn_run.setFont(QFont("", 10, QFont.Bold))
        btn_run.clicked.connect(self.run_simulation)
        left_layout.addWidget(btn_run)

        btn_all = QPushButton("Run + Export All ...")
        btn_all.clicked.connect(self.export_all)
        left_layout.addWidget(btn_all)

        btn_open = QPushButton("Open Output Folder")
        btn_open.clicked.connect(self.open_output_folder)
        left_layout.addWidget(btn_open)
        left_layout.addStretch(1)

        # ---- right: results -----------------------------------------------
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.tabs = QTabWidget()

        self.tbl_streams = QTableWidget(0, len(STREAM_COLUMNS))
        self.tbl_streams.setHorizontalHeaderLabels([c[1] for c in STREAM_COLUMNS])
        self.tabs.addTab(self.tbl_streams, "Streams")

        self.tbl_kpis = QTableWidget(0, 2)
        self.tbl_kpis.setHorizontalHeaderLabels(["Indicator", "Value"])
        self.tabs.addTab(self.tbl_kpis, "KPIs")

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Monospace", 9))
        self.tabs.addTab(self.txt_log, "Log")

        right_layout.addWidget(self.tabs)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        self.setCentralWidget(root)

    # ------------------------------------------------------------- actions --
    def config(self) -> PlantConfig:
        return PlantConfig(**{a: self.spins[a].value() for a, *_ in FIELDS})

    def log(self, text: str) -> None:
        self.txt_log.appendPlainText(text)

    def run_simulation(self) -> None:
        cfg = self.config()
        try:
            self.engine = SimulationEngine(cfg)
            self.result = self.engine.run()
        except Exception as exc:  # noqa: BLE001
            self.log("ERROR: " + repr(exc))
            self.log(traceback.format_exc())
            QMessageBox.critical(self, "Simulation failed", str(exc))
            return

        r = self.result
        self.log("-" * 64)
        self.log(f"simulation id : {r.simulation_id}")
        self.log(f"status        : {r.status}   iterations: {r.solver.iterations}")
        self.log(f"input hash    : {r.input_hash}")
        self.log(f"result hash   : {r.result_hash}")
        self.log(f"mass balance error : {r.kpis['mass_balance_error_pct']:.6f} %")
        self.log(f"Fe balance error   : {r.kpis['fe_balance_error_pct']:.6f} %")
        for w in r.warnings:
            self.log(f"warning: {w}")
        self.statusBar().showMessage(
            f"{r.simulation_id} - {r.status} - "
            f"mass balance error {r.kpis['mass_balance_error_pct']:.6f} %"
        )
        self._fill_streams(r)
        self._fill_kpis(r)

    def _fill_streams(self, r) -> None:
        rows = list(r.streams.values())
        self.tbl_streams.setRowCount(len(rows))
        for i, s in enumerate(rows):
            d = s.as_dict()
            for j, (key, _) in enumerate(STREAM_COLUMNS):
                val = d.get(key, "")
                if isinstance(val, float):
                    val = f"{val:,.4f}"
                item = QTableWidgetItem("" if val is None else str(val))
                self.tbl_streams.setItem(i, j, item)
        self.tbl_streams.resizeColumnsToContents()

    def _fill_kpis(self, r) -> None:
        kpis = dict(r.kpis)
        keys = [k for k in KPI_ORDER if k in kpis] + [k for k in kpis if k not in KPI_ORDER]
        self.tbl_kpis.setRowCount(len(keys))
        for i, k in enumerate(keys):
            v = kpis[k]
            shown = f"{v:,.4f}" if isinstance(v, float) else str(v)
            self.tbl_kpis.setItem(i, 0, QTableWidgetItem(k))
            self.tbl_kpis.setItem(i, 1, QTableWidgetItem(shown))
        self.tbl_kpis.resizeColumnsToContents()

    def open_project(self) -> None:
        start = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "RELEASE", "SAMPLE_PROJECTS")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open AH-SIM project", start, "AH-SIM project (*.ahsim.json *.json)")
        if not path:
            return
        import json
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open project", str(exc))
            return
        cfg = data.get("config", {})
        for attr, spin in self.spins.items():
            if attr in cfg:
                try:
                    spin.setValue(float(cfg[attr]))
                except (TypeError, ValueError):
                    pass
        meta = data.get("metadata", {})
        sim = data.get("simulation", {})
        self.log(f"project loaded: {path}")
        self.log(f"  software : {meta.get('software_name')} v{meta.get('version')}")
        self.log(f"  developer: {meta.get('developer')} ({meta.get('developer_fa')})")
        self.log(f"  contact  : {meta.get('contact')}")
        if sim:
            self.log(f"  recorded simulation: {sim.get('simulation_id')} {sim.get('status')}")

    def open_output_folder(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "RELEASE")
        QDesktopServices.openUrl(QUrl.fromLocalFile(base))

    def export_all(self) -> None:
        if self.result is None:
            self.run_simulation()
        if self.result is None:
            return

        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "RELEASE")
        targets = [
            ("EXCEL_REPORTS", "Plant_Simulation_Report.xlsx", self.cb_excel.isChecked(), "excel"),
            ("CAD_OUTPUT", "Process_Flowsheet.dxf", self.cb_dxf.isChecked(), "dxf"),
            ("TEST_REPORTS", "Engineering_Report.pdf", self.cb_pdf.isChecked(), "pdf"),
            ("VIDEO_OUTPUT", "Process_Animation.mp4", self.cb_mp4.isChecked(), "mp4"),
        ]
        for folder, name, wanted, kind in targets:
            if not wanted:
                continue
            out_dir = os.path.join(base, folder)
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, name)
            try:
                if kind == "excel":
                    from ..outputs.excel_export import export_workbook
                    export_workbook(self.result, path)
                elif kind == "dxf":
                    from ..outputs.cad_dxf import export_dxf
                    export_dxf(self.result, path)
                elif kind == "pdf":
                    from ..outputs.pdf_export import export_pdf
                    export_pdf(self.result, path)
                else:
                    from ..outputs.video_engine import export_video
                    export_video(self.result, path, seconds=8)
                self.log(f"[OUT] {os.path.getsize(path):>10,} bytes  {path}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"[FAIL] {path}: {exc!r}")
                QMessageBox.warning(self, "Export failed", f"{name}\n\n{exc!r}")

        if self.cb_sens.isChecked():
            try:
                import json
                from ..engine.calibration import run_scenario, sensitivity
                scenarios = [run_scenario(f"Scenario-{i:03d}", feed_rate_t_h=f)
                             for i, f in enumerate([100, 200, 400, 600, 800, 1000], 1)]
                sens = sensitivity("feed_rate_t_h", [100, 200, 400, 600, 800, 1000])
                out_dir = os.path.join(base, "TEST_REPORTS")
                os.makedirs(out_dir, exist_ok=True)
                path = os.path.join(out_dir, "Scenario_Sensitivity_Results.json")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump({"scenarios": scenarios, "feed_sensitivity": sens}, fh,
                              ensure_ascii=False, indent=2, default=str)
                self.log(f"[OUT] {os.path.getsize(path):>10,} bytes  {path}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"[FAIL] sensitivity study: {exc!r}")

        self.statusBar().showMessage("Exports finished - see the Log tab")
        QMessageBox.information(self, "Exports finished",
                                "All selected outputs were written to the RELEASE folder "
                                "next to the application.")

    def about(self) -> None:
        QMessageBox.information(
            self, f"About {SOFTWARE_NAME}",
            f"<b>{SOFTWARE_NAME}</b><br>Version {VERSION}<br><br>"
            f"Industrial Mineral Processing Simulation and Engineering Software<br><br>"
            f"Developer / Manufacturer: <b>{DEVELOPER_EN}</b> ({DEVELOPER_FA})<br>"
            f"Contact: <b>{CONTACT}</b><br><br>"
            f"Dry iron-ore beneficiation circuit: crushing, screening, dry magnetic "
            f"separation with recycle convergence, PSD tracking, mass/Fe balancing, "
            f"Excel / DXF / PDF / MP4 reporting.<br><br>"
            f"(c) 2026 {DEVELOPER_EN} - All rights reserved.")


def run_app() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(SOFTWARE_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName(DEVELOPER_EN)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
