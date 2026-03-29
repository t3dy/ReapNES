# Trace Comparison: Castlevania 1 Vampire Killer

Comparing parser output against emulator APU trace.
Trace start offset: frame 111
Frames compared: 1792

## Summary

| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |
|---------|-----------------|-------------------|-----------------|--------------------|--------------------|
| pulse1 | 0 | 0 | 0 | 0 | none |
| pulse2 | 0 | 0 | 0 | 0 | none |
| triangle | 0 | 195 | 0 | 195 | none |

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
- ... (80 more regions)

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
- ... (72 more regions)

### triangle
- frames 4-13 (10 frames, 0.17s)
- frames 18-20 (3 frames, 0.05s)
- frames 25-27 (3 frames, 0.05s)
- frames 32-48 (17 frames, 0.28s)
- frames 53-55 (3 frames, 0.05s)
- frames 60-69 (10 frames, 0.17s)
- frames 74-76 (3 frames, 0.05s)
- frames 81-83 (3 frames, 0.05s)
- frames 88-90 (3 frames, 0.05s)
- frames 95-97 (3 frames, 0.05s)
- frames 102-104 (3 frames, 0.05s)
- frames 109-111 (3 frames, 0.05s)
- frames 116-125 (10 frames, 0.17s)
- frames 130-132 (3 frames, 0.05s)
- frames 137-139 (3 frames, 0.05s)
- frames 144-167 (24 frames, 0.40s)
- frames 172-174 (3 frames, 0.05s)
- frames 179-181 (3 frames, 0.05s)
- frames 186-188 (3 frames, 0.05s)
- frames 193-195 (3 frames, 0.05s)
- ... (97 more regions)

## First Frame Diffs (per channel)

### pulse1

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 4 | A4 | --- | 0 | 0 | False | False |
| 5 | A4 | --- | 0 | 0 | False | False |
| 6 | A4 | --- | 0 | 0 | False | False |
| 11 | A4 | --- | 0 | 0 | False | False |
| 12 | A4 | --- | 0 | 0 | False | False |
| 13 | A4 | --- | 0 | 0 | False | False |
| 25 | G4 | --- | 0 | 0 | False | False |
| 26 | G4 | --- | 0 | 0 | False | False |
| 27 | G4 | --- | 0 | 0 | False | False |
| 90 | D4 | --- | 0 | 0 | False | False |
| 97 | D4 | --- | 0 | 0 | False | False |
| 104 | C4 | --- | 0 | 0 | False | False |
| 111 | C4 | --- | 0 | 0 | False | False |
| 132 | D4 | --- | 0 | 0 | False | False |
| 153 | A#3 | --- | 0 | 0 | False | False |
| 167 | D4 | --- | 0 | 0 | False | False |
| 174 | C4 | --- | 0 | 0 | False | False |
| 223 | G4 | --- | 0 | 0 | False | False |
| 228 | A4 | --- | 0 | 0 | False | False |
| 229 | A4 | --- | 0 | 0 | False | False |
| 230 | A4 | --- | 0 | 0 | False | False |
| 235 | A4 | --- | 0 | 0 | False | False |
| 236 | A4 | --- | 0 | 0 | False | False |
| 237 | A4 | --- | 0 | 0 | False | False |
| 249 | G4 | --- | 0 | 0 | False | False |
| 250 | G4 | --- | 0 | 0 | False | False |
| 251 | G4 | --- | 0 | 0 | False | False |
| 314 | D4 | --- | 0 | 0 | False | False |
| 321 | D4 | --- | 0 | 0 | False | False |
| 328 | C4 | --- | 0 | 0 | False | False |

### pulse2

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 230 | D5 | --- | 0 | 0 | False | False |
| 237 | D5 | --- | 0 | 0 | False | False |
| 251 | C5 | --- | 0 | 0 | False | False |
| 314 | D4 | --- | 0 | 0 | False | False |
| 321 | E4 | --- | 0 | 0 | False | False |
| 328 | F4 | --- | 0 | 0 | False | False |
| 335 | G4 | --- | 0 | 0 | False | False |
| 356 | A4 | --- | 0 | 0 | False | False |
| 377 | D4 | --- | 0 | 0 | False | False |
| 391 | A4 | --- | 0 | 0 | False | False |
| 398 | G4 | --- | 0 | 0 | False | False |
| 447 | C4 | --- | 0 | 0 | False | False |
| 467 | D5 | --- | 0 | 0 | False | False |
| 468 | D5 | --- | 0 | 0 | False | False |
| 469 | D5 | --- | 0 | 0 | False | False |
| 470 | D5 | --- | 0 | 0 | False | False |
| 471 | D5 | --- | 0 | 0 | False | False |
| 472 | D5 | --- | 0 | 0 | False | False |
| 473 | D5 | --- | 0 | 0 | False | False |
| 474 | D5 | --- | 0 | 0 | False | False |
| 475 | D5 | --- | 0 | 0 | False | False |
| 476 | D5 | --- | 0 | 0 | False | False |
| 477 | D5 | --- | 0 | 0 | False | False |
| 478 | D5 | --- | 0 | 0 | False | False |
| 479 | D5 | --- | 0 | 0 | False | False |
| 480 | D5 | --- | 0 | 0 | False | False |
| 481 | D5 | --- | 0 | 0 | False | False |
| 482 | D5 | --- | 0 | 0 | False | False |
| 488 | A5 | --- | 0 | 0 | False | False |
| 489 | A5 | --- | 0 | 0 | False | False |

### triangle

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 4 | D3 | D3 | 0 | 15 | False | True |
| 5 | D3 | --- | 0 | 0 | False | False |
| 6 | D3 | --- | 0 | 0 | False | False |
| 7 | D3 | --- | 0 | 0 | False | False |
| 8 | D3 | --- | 0 | 0 | False | False |
| 9 | D3 | --- | 0 | 0 | False | False |
| 10 | D3 | --- | 0 | 0 | False | False |
| 11 | D3 | --- | 0 | 0 | False | False |
| 12 | D3 | --- | 0 | 0 | False | False |
| 13 | D3 | --- | 0 | 0 | False | False |
| 18 | D3 | D3 | 0 | 15 | False | True |
| 19 | D3 | --- | 0 | 0 | False | False |
| 20 | D3 | --- | 0 | 0 | False | False |
| 25 | D3 | D3 | 0 | 15 | False | True |
| 26 | D3 | --- | 0 | 0 | False | False |
| 27 | D3 | --- | 0 | 0 | False | False |
| 32 | D3 | D3 | 0 | 15 | False | True |
| 33 | D3 | --- | 0 | 0 | False | False |
| 34 | D3 | --- | 0 | 0 | False | False |
| 35 | D3 | --- | 0 | 0 | False | False |
| 36 | D3 | --- | 0 | 0 | False | False |
| 37 | D3 | --- | 0 | 0 | False | False |
| 38 | D3 | --- | 0 | 0 | False | False |
| 39 | D3 | --- | 0 | 0 | False | False |
| 40 | D3 | --- | 0 | 0 | False | False |
| 41 | D3 | --- | 0 | 0 | False | False |
| 42 | D3 | --- | 0 | 0 | False | False |
| 43 | D3 | --- | 0 | 0 | False | False |
| 44 | D3 | --- | 0 | 0 | False | False |
| 45 | D3 | --- | 0 | 0 | False | False |
