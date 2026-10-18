# Accuracy experiment v2 (predeclared)

Keep release `38ec33cb326146c7991650a3164cf440`, its 660 real windows,
15 participants, original 12 features and labels fixed. No synthetic training,
coverage changes, or release publication. This is reused-cohort development.

Compare the reproduced original nested participant-held-out baseline with:
1. Original candidates plus logistic C=0.001 and 0.01, using the existing inner
   balanced-accuracy/log-loss selection at threshold 0.5.
2. Those same candidates with thresholds 0.35 through 0.65 in steps of 0.05.
   Select threshold and model on inner participant-held-out predictions only,
   ranking participant-weighted accuracy, then balanced accuracy, then log loss.
   Threshold ties prefer 0.5. Never select against outer predictions.

Use the existing seed, inner three participant-stratified folds and outer
leave-one-participant-out evaluation, including fold-local weighted scaling.
Report accuracy, balanced accuracy, AUC, log loss, Brier, and per-person changes.
Reproduce baseline/prior predictions exactly before interpreting alternatives.
One run; no iterative tuning against outer results. Do not auto-promote any gain.
New independently labeled participants are required for stronger validation.
