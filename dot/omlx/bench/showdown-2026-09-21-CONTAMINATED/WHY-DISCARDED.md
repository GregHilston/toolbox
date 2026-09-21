# Discarded — the drift control caught a real handicap

oMLX was restarted once at the top of the run instead of before each model, so
the three arms did not see the same machine:

| arm | resident when measured |
|---|---|
| `plain` | itself, 19 GB, on a fresh server |
| `dwq` | itself **plus** plain, 38 GB |
| `plain-repeat` | both, plus accumulated thermal load |

The control says how much that mattered: plain's decode on the code family fell
129.34 -> 100.54 t/s (-22%) and its 16K prefill 1,316 -> 1,062 tok/s (-19%)
between two identical passes, and its per-rep spread went from 127.7-130.8 to
94.6-118.8.

DWQ was the arm carrying the worse residency, so its measured -25% prefill and
-13% decode are not attributable to the checkpoint. `bench/README.md` rule #1
exists for exactly this and the script did not follow it.

The one FOREIGN request in the dwq window is unrelated and harmless: plain's
last longctx request shared a timestamp with dwq's window start, because both
were stamped from the same clock tick.

Kept as the record of a run that should not be quoted.
