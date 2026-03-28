# Trace Comparison: Castlevania 1 Vampire Killer

Comparing parser output against emulator APU trace.
Trace start offset: frame 111
Frames compared: 2016

## Summary

| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |
|---------|-----------------|-------------------|-----------------|--------------------|--------------------|
| pulse1 | 0 | 687 | 192 | 373 | none |
| pulse2 | 0 | 1728 | 210 | 546 | none |
| triangle | 0 | 742 | 0 | 742 | none |

## Mismatch Regions

### pulse1
- frames 4-6 (3 frames, 0.05s)
- frames 11-13 (3 frames, 0.05s)
- frames 25-27 (3 frames, 0.05s)
- frames 90-90 (1 frames, 0.02s)
- frames 97-97 (1 frames, 0.02s)
- frames 104-104 (1 frames, 0.02s)
- frames 111-111 (1 frames, 0.02s)
- frames 132-132 (1 frames, 0.02s)
- frames 153-153 (1 frames, 0.02s)
- frames 167-167 (1 frames, 0.02s)
- frames 174-174 (1 frames, 0.02s)
- frames 223-223 (1 frames, 0.02s)
- frames 228-230 (3 frames, 0.05s)
- frames 235-237 (3 frames, 0.05s)
- frames 249-251 (3 frames, 0.05s)
- frames 314-314 (1 frames, 0.02s)
- frames 321-321 (1 frames, 0.02s)
- frames 328-328 (1 frames, 0.02s)
- frames 335-335 (1 frames, 0.02s)
- frames 356-356 (1 frames, 0.02s)
- ... (92 more regions)

### pulse2
- frames 230-230 (1 frames, 0.02s)
- frames 237-237 (1 frames, 0.02s)
- frames 251-251 (1 frames, 0.02s)
- frames 314-314 (1 frames, 0.02s)
- frames 321-321 (1 frames, 0.02s)
- frames 328-328 (1 frames, 0.02s)
- frames 335-335 (1 frames, 0.02s)
- frames 356-356 (1 frames, 0.02s)
- frames 377-377 (1 frames, 0.02s)
- frames 391-391 (1 frames, 0.02s)
- frames 398-398 (1 frames, 0.02s)
- frames 447-447 (1 frames, 0.02s)
- frames 467-482 (16 frames, 0.27s)
- frames 488-503 (16 frames, 0.27s)
- frames 509-510 (2 frames, 0.03s)
- frames 516-517 (2 frames, 0.03s)
- frames 523-524 (2 frames, 0.03s)
- frames 530-559 (30 frames, 0.50s)
- frames 579-580 (2 frames, 0.03s)
- frames 586-587 (2 frames, 0.03s)
- ... (74 more regions)

### triangle
- frames 616-622 (7 frames, 0.12s)
- frames 840-846 (7 frames, 0.12s)
- frames 924-951 (28 frames, 0.47s)
- frames 980-1007 (28 frames, 0.47s)
- frames 1036-1063 (28 frames, 0.47s)
- frames 1092-1119 (28 frames, 0.47s)
- frames 1148-1175 (28 frames, 0.47s)
- frames 1204-1231 (28 frames, 0.47s)
- frames 1260-1287 (28 frames, 0.47s)
- frames 1316-1343 (28 frames, 0.47s)
- frames 1351-1357 (7 frames, 0.12s)
- frames 1365-1378 (14 frames, 0.23s)
- frames 1393-1399 (7 frames, 0.12s)
- frames 1414-1455 (42 frames, 0.70s)
- frames 1463-1469 (7 frames, 0.12s)
- frames 1477-1511 (35 frames, 0.58s)
- frames 1519-1525 (7 frames, 0.12s)
- frames 1533-1567 (35 frames, 0.58s)
- frames 1575-1581 (7 frames, 0.12s)
- frames 1589-1602 (14 frames, 0.23s)
- ... (7 more regions)

## First Frame Diffs (per channel)

### pulse1

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 4 | A3 | --- | 1 | 0 | True | False |
| 5 | A3 | --- | 0 | 0 | False | False |
| 6 | A3 | --- | 0 | 0 | False | False |
| 11 | A3 | --- | 1 | 0 | True | False |
| 12 | A3 | --- | 0 | 0 | False | False |
| 13 | A3 | --- | 0 | 0 | False | False |
| 25 | G3 | --- | 1 | 0 | True | False |
| 26 | G3 | --- | 0 | 0 | False | False |
| 27 | G3 | --- | 0 | 0 | False | False |
| 90 | D3 | --- | 1 | 0 | True | False |
| 97 | D3 | --- | 1 | 0 | True | False |
| 104 | C3 | --- | 1 | 0 | True | False |
| 111 | C3 | --- | 1 | 0 | True | False |
| 132 | D3 | --- | 1 | 0 | True | False |
| 153 | A#2 | --- | 1 | 0 | True | False |
| 167 | D3 | --- | 1 | 0 | True | False |
| 174 | C3 | --- | 1 | 0 | True | False |
| 223 | G3 | --- | 1 | 0 | True | False |
| 228 | A3 | --- | 1 | 0 | True | False |
| 229 | A3 | --- | 0 | 0 | False | False |
| 230 | A3 | --- | 0 | 0 | False | False |
| 235 | A3 | --- | 1 | 0 | True | False |
| 236 | A3 | --- | 0 | 0 | False | False |
| 237 | A3 | --- | 0 | 0 | False | False |
| 249 | G3 | --- | 1 | 0 | True | False |
| 250 | G3 | --- | 0 | 0 | False | False |
| 251 | G3 | --- | 0 | 0 | False | False |
| 314 | D3 | --- | 1 | 0 | True | False |
| 321 | D3 | --- | 1 | 0 | True | False |
| 328 | C3 | --- | 1 | 0 | True | False |

### pulse2

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 230 | D4 | --- | 5 | 0 | True | False |
| 237 | D4 | --- | 5 | 0 | True | False |
| 251 | C4 | --- | 5 | 0 | True | False |
| 314 | D3 | --- | 5 | 0 | True | False |
| 321 | E3 | --- | 5 | 0 | True | False |
| 328 | F3 | --- | 5 | 0 | True | False |
| 335 | G3 | --- | 5 | 0 | True | False |
| 356 | A3 | --- | 5 | 0 | True | False |
| 377 | D3 | --- | 5 | 0 | True | False |
| 391 | A3 | --- | 5 | 0 | True | False |
| 398 | G3 | --- | 5 | 0 | True | False |
| 447 | C3 | --- | 5 | 0 | True | False |
| 467 | D4 | --- | 5 | 0 | True | False |
| 468 | D4 | --- | 5 | 0 | True | False |
| 469 | D4 | --- | 5 | 0 | True | False |
| 470 | D4 | --- | 5 | 0 | True | False |
| 471 | D4 | --- | 5 | 0 | True | False |
| 472 | D4 | --- | 5 | 0 | True | False |
| 473 | D4 | --- | 5 | 0 | True | False |
| 474 | D4 | --- | 5 | 0 | True | False |
| 475 | D4 | --- | 5 | 0 | True | False |
| 476 | D4 | --- | 5 | 0 | True | False |
| 477 | D4 | --- | 5 | 0 | True | False |
| 478 | D4 | --- | 5 | 0 | True | False |
| 479 | D4 | --- | 5 | 0 | True | False |
| 480 | D4 | --- | 5 | 0 | True | False |
| 481 | D4 | --- | 5 | 0 | True | False |
| 482 | D4 | --- | 5 | 0 | True | False |
| 488 | A4 | --- | 5 | 0 | True | False |
| 489 | A4 | --- | 5 | 0 | True | False |

### triangle

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 616 | --- | A#2 | 0 | 15 | False | True |
| 617 | --- | A#2 | 0 | 15 | False | True |
| 618 | --- | A#2 | 0 | 15 | False | True |
| 619 | --- | A#2 | 0 | 15 | False | True |
| 620 | --- | A#2 | 0 | 15 | False | True |
| 621 | --- | A#2 | 0 | 15 | False | True |
| 622 | --- | A#2 | 0 | 15 | False | True |
| 840 | --- | A#2 | 0 | 15 | False | True |
| 841 | --- | A#2 | 0 | 15 | False | True |
| 842 | --- | A#2 | 0 | 15 | False | True |
| 843 | --- | A#2 | 0 | 15 | False | True |
| 844 | --- | A#2 | 0 | 15 | False | True |
| 845 | --- | A#2 | 0 | 15 | False | True |
| 846 | --- | A#2 | 0 | 15 | False | True |
| 924 | --- | C#3 | 0 | 15 | False | True |
| 925 | --- | C#3 | 0 | 15 | False | True |
| 926 | --- | C#3 | 0 | 15 | False | True |
| 927 | --- | C#3 | 0 | 15 | False | True |
| 928 | --- | C#3 | 0 | 15 | False | True |
| 929 | --- | C#3 | 0 | 15 | False | True |
| 930 | --- | C#3 | 0 | 15 | False | True |
| 931 | --- | C#3 | 0 | 15 | False | True |
| 932 | --- | C#3 | 0 | 15 | False | True |
| 933 | --- | C#3 | 0 | 15 | False | True |
| 934 | --- | C#3 | 0 | 15 | False | True |
| 935 | --- | C#3 | 0 | 15 | False | True |
| 936 | --- | C#3 | 0 | 15 | False | True |
| 937 | --- | C#3 | 0 | 15 | False | True |
| 938 | --- | C#3 | 0 | 15 | False | True |
| 939 | --- | C#3 | 0 | 15 | False | True |
