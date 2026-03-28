# Trace Comparison: Castlevania 1 Vampire Killer

Comparing parser output against emulator APU trace.
Trace start offset: frame 111
Frames compared: 2016

## Summary

| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |
|---------|-----------------|-------------------|-----------------|--------------------|--------------------|
| pulse1 | 354 | 996 | 395 | 445 | frame 910 |
| pulse2 | 523 | 1773 | 461 | 477 | frame 910 |
| triangle | 294 | 525 | 0 | 525 | frame 896 |

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
- ... (60 more regions)

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
- ... (50 more regions)

### triangle
- frames 616-622 (7 frames, 0.12s)
- frames 840-846 (7 frames, 0.12s)
- frames 896-951 (56 frames, 0.93s)
- frames 1008-1119 (112 frames, 1.87s)
- frames 1148-1175 (28 frames, 0.47s)
- frames 1204-1231 (28 frames, 0.47s)
- frames 1260-1399 (140 frames, 2.33s)
- frames 1428-1567 (140 frames, 2.33s)
- frames 1575-1581 (7 frames, 0.12s)
- frames 1589-1602 (14 frames, 0.23s)
- frames 1617-1623 (7 frames, 0.12s)
- frames 1638-1679 (42 frames, 0.70s)
- frames 1687-1693 (7 frames, 0.12s)
- frames 1701-1735 (35 frames, 0.58s)
- frames 1743-1749 (7 frames, 0.12s)
- frames 1757-1791 (35 frames, 0.58s)
- frames 1799-1805 (7 frames, 0.12s)
- frames 1813-1826 (14 frames, 0.23s)
- frames 1834-1847 (14 frames, 0.23s)
- frames 1862-1903 (42 frames, 0.70s)
- ... (3 more regions)

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
| 896 | D3 | C#3 | 15 | 15 | True | True |
| 897 | D3 | C#3 | 15 | 15 | True | True |
| 898 | D3 | C#3 | 15 | 15 | True | True |
| 899 | D3 | C#3 | 15 | 15 | True | True |
| 900 | D3 | C#3 | 15 | 15 | True | True |
| 901 | D3 | C#3 | 15 | 15 | True | True |
| 902 | D3 | C#3 | 15 | 15 | True | True |
| 903 | D3 | C#3 | 15 | 15 | True | True |
| 904 | D3 | C#3 | 15 | 15 | True | True |
| 905 | D3 | C#3 | 15 | 15 | True | True |
| 906 | D3 | C#3 | 15 | 15 | True | True |
| 907 | D3 | C#3 | 15 | 15 | True | True |
| 908 | D3 | C#3 | 15 | 15 | True | True |
| 909 | D3 | C#3 | 15 | 15 | True | True |
| 910 | D3 | C#3 | 15 | 15 | True | True |
| 911 | D3 | C#3 | 15 | 15 | True | True |
