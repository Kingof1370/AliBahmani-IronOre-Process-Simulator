"""Application metadata and manufacturer identity (Spec Section 02)."""
SOFTWARE_NAME = "AliBahmani IronOre Process Simulator"
SOFTWARE_TITLE = "Industrial Mineral Processing Simulation and Engineering Software"
SHORT_NAME = "AH-SIM"
VERSION = "1.0.0"
BUILD_DATE = "2026-09-18"
DEVELOPER_EN = "Ali Bahmani"
DEVELOPER_FA = "علی بهمنی"
CONTACT = "09915420558"
PUBLISHER = "Ali Bahmani"
COPYRIGHT = f"(c) 2026 {DEVELOPER_EN} - {CONTACT}"

PROJECT_NAME_DEFAULT = "Dry Iron Ore Beneficiation Plant - 600 t/h"
PLANT_NAME_DEFAULT = "Dry Magnetite Processing Plant"

MODEL_VERSIONS = {
    "MagneticModel": "v1",
    "ScreenModel": "v1",
    "CrusherModel": "v1",
    "RecycleSolver": "v1",
    "MassBalanceEngine": "v1",
    "PSDEngine": "v1",
}

CREDIT_LINES = [
    f"Software: {SOFTWARE_NAME} v{VERSION}",
    f"Developer / Manufacturer: {DEVELOPER_EN} ({DEVELOPER_FA})",
    f"Contact: {CONTACT}",
]


def as_dict() -> dict:
    return {
        "software_name": SOFTWARE_NAME,
        "software_title": SOFTWARE_TITLE,
        "version": VERSION,
        "build_date": BUILD_DATE,
        "developer": DEVELOPER_EN,
        "developer_fa": DEVELOPER_FA,
        "contact": CONTACT,
        "publisher": PUBLISHER,
        "copyright": COPYRIGHT,
        "model_versions": MODEL_VERSIONS,
    }
