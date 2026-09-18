# Calibration Manual - AliBahmani IronOre Process Simulator
Developer: Ali Bahmani - 09915420558

1. Perform a plant/magnetite drum test; record Test ID, date, feed mass, feed
   Fe %, feed PSD, field (G), RPM, moisture, product mass & Fe %, tail mass & Fe %.
2. Enter the data via `ahsim.engine.calibration.CalibrationTest` and the
   Excel sheet 20_CALIBRATION.
3. The engine computes Observed vs Predicted recovery, Residual and Relative
   Error. Tests with relative error <= 10% are accepted as calibration data
   (Site Calibration > Validated User Test > Manufacturer > Published >
   Correlation > Default - Section 28) and replace the default partition
   correlation without modifying core software (Section 114).
4. Until calibration exists, all recovery figures are labelled MODEL RESULT
   and the software warns accordingly (Sections 38, 113).
