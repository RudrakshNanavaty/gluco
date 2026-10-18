# Predeclared temperature model comparison

The prior sensor-group study suggests temperature summaries contain useful
signal. Label provenance now agrees from staged demographics through saved
training labels for all 15 approved people; no error-selected exclusions or
label corrections are justified. The existing 65.33% temperature pipeline is
the fixed control, not an independent test set.

Run one bounded nested participant-held-out comparison on the same 660 real
windows and five temperature features. Preserve coverage, participants, labels,
seed 42, equal participant weights, threshold 0.5, fold-local weighted scaling,
and inner balanced-accuracy/log-loss estimator selection.

Primary procedure: the existing six temperature candidates plus exactly two
fixed alternatives, selected only using inner participant-disjoint predictions:

- Gaussian Naive Bayes, var_smoothing=0.01, with weighted standardization and
  weighted fit. This tests a diagonal class-conditional nonlinear boundary.
- RBF support vector classifier, C=1, gamma='scale', probability=False, with
  weighted standardization and weighted fit. This tests a smooth nonlinear
  boundary without sample-level internal probability calibration.

For the SVC only, map decision margins through a fixed sigmoid so the shared
bounded-score reporting API can compute losses; these are explicitly
uncalibrated scores. Do not enable SVC probability=True because its internal
sample-level CV would ignore participant groups. No calibration claim is made.

Report the old temperature control, each fixed added candidate, the primary
inner-selected procedure, and prior. Reproduce the reference temperature
metrics, fold estimator selections and per-person accuracies from MLflow
14db0b9a30fd4199b655b5a136d470f8 before interpreting alternatives. Log exact
held-out predictions, full paired outcomes and all five metrics.

One completed run, no adaptive expansion of hyperparameters, threshold changes,
post-hoc label flipping, or error-selected exclusions. Reporting a fixed added
candidate that happens to exceed 70% is not the same as the primary selection
procedure exceeding 70%. Preserve negative results. This is another reused-
cohort development comparison; it cannot establish independent validation.
Do not publish artifacts, releases, feature contracts or session pins.
