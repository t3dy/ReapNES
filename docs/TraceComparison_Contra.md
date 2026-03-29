# Trace Comparison: CONTRA (track: jungle)

Comparing parser output against emulator APU trace.
Trace start offset: frame 155
Frames compared: 2976

## Summary

| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |
|---------|-----------------|-------------------|-----------------|--------------------|--------------------|
| pulse1 | 72 | 175 | 0 | 18 | frame 0 |
| pulse2 | 72 | 199 | 0 | 18 | frame 0 |
| triangle | 17 | 250 | 0 | 250 | frame 54 |

## Mismatch Regions

### pulse1
- frames 0-41 (42 frames, 0.70s)
- frames 48-95 (48 frames, 0.80s)
- frames 882-885 (4 frames, 0.07s)
- frames 900-903 (4 frames, 0.07s)
- frames 978-981 (4 frames, 0.07s)
- frames 996-999 (4 frames, 0.07s)
- frames 1074-1077 (4 frames, 0.07s)
- frames 1092-1095 (4 frames, 0.07s)
- frames 1170-1173 (4 frames, 0.07s)
- frames 1188-1191 (4 frames, 0.07s)
- frames 1382-1385 (4 frames, 0.07s)
- frames 1400-1403 (4 frames, 0.07s)
- frames 1412-1415 (4 frames, 0.07s)
- frames 1430-1433 (4 frames, 0.07s)
- frames 1544-1550 (7 frames, 0.12s)
- frames 1574-1580 (7 frames, 0.12s)
- frames 1592-1598 (7 frames, 0.12s)
- frames 1622-1628 (7 frames, 0.12s)
- frames 1640-1646 (7 frames, 0.12s)
- frames 1670-1673 (4 frames, 0.07s)
- ... (30 more regions)

### pulse2
- frames 0-53 (54 frames, 0.90s)
- frames 60-95 (36 frames, 0.60s)
- frames 1382-1385 (4 frames, 0.07s)
- frames 1400-1403 (4 frames, 0.07s)
- frames 1412-1415 (4 frames, 0.07s)
- frames 1430-1433 (4 frames, 0.07s)
- frames 1544-1550 (7 frames, 0.12s)
- frames 1574-1580 (7 frames, 0.12s)
- frames 1592-1598 (7 frames, 0.12s)
- frames 1622-1628 (7 frames, 0.12s)
- frames 1640-1646 (7 frames, 0.12s)
- frames 1670-1673 (4 frames, 0.07s)
- frames 1688-1694 (7 frames, 0.12s)
- frames 2117-2117 (1 frames, 0.02s)
- frames 2123-2123 (1 frames, 0.02s)
- frames 2129-2129 (1 frames, 0.02s)
- frames 2135-2141 (7 frames, 0.12s)
- frames 2153-2153 (1 frames, 0.02s)
- frames 2159-2159 (1 frames, 0.02s)
- frames 2165-2165 (1 frames, 0.02s)
- ... (65 more regions)

### triangle
- frames 0-77 (78 frames, 1.30s)
- frames 83-95 (13 frames, 0.22s)
- frames 100-101 (2 frames, 0.03s)
- frames 106-107 (2 frames, 0.03s)
- frames 112-113 (2 frames, 0.03s)
- frames 118-125 (8 frames, 0.13s)
- frames 130-131 (2 frames, 0.03s)
- frames 136-137 (2 frames, 0.03s)
- frames 142-143 (2 frames, 0.03s)
- frames 148-149 (2 frames, 0.03s)
- frames 154-155 (2 frames, 0.03s)
- frames 160-161 (2 frames, 0.03s)
- frames 166-173 (8 frames, 0.13s)
- frames 178-179 (2 frames, 0.03s)
- frames 184-185 (2 frames, 0.03s)
- frames 190-191 (2 frames, 0.03s)
- frames 196-197 (2 frames, 0.03s)
- frames 202-203 (2 frames, 0.03s)
- frames 208-209 (2 frames, 0.03s)
- frames 214-221 (8 frames, 0.13s)
- ... (305 more regions)

## First Frame Diffs (per channel)

### pulse1

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 0 | C5 | D#4 | 3 | 5 | True | True |
| 1 | C5 | D#4 | 4 | 6 | True | True |
| 2 | C5 | D#4 | 3 | 7 | True | True |
| 3 | C5 | D#4 | 2 | 6 | True | True |
| 4 | C5 | D#4 | 2 | 5 | True | True |
| 5 | C5 | D#4 | 1 | 4 | True | True |
| 6 | A#4 | D4 | 3 | 5 | True | True |
| 7 | A#4 | D4 | 4 | 6 | True | True |
| 8 | A#4 | D4 | 3 | 7 | True | True |
| 9 | A#4 | D4 | 2 | 6 | True | True |
| 10 | A#4 | D4 | 2 | 5 | True | True |
| 11 | A#4 | D4 | 1 | 4 | True | True |
| 12 | G4 | D#4 | 3 | 5 | True | True |
| 13 | G4 | D#4 | 4 | 6 | True | True |
| 14 | G4 | D#4 | 3 | 7 | True | True |
| 15 | G4 | D#4 | 2 | 6 | True | True |
| 16 | G4 | D#4 | 2 | 5 | True | True |
| 17 | G4 | D#4 | 1 | 4 | True | True |
| 18 | F4 | G3 | 3 | 5 | True | True |
| 19 | F4 | G3 | 4 | 6 | True | True |
| 20 | F4 | G3 | 3 | 7 | True | True |
| 21 | F4 | G3 | 2 | 6 | True | True |
| 22 | F4 | G3 | 2 | 5 | True | True |
| 23 | F4 | G3 | 1 | 4 | True | True |
| 24 | G4 | G3 | 3 | 3 | True | True |
| 25 | G4 | G3 | 4 | 3 | True | True |
| 26 | G4 | G3 | 3 | 3 | True | True |
| 27 | G4 | G3 | 2 | 3 | True | True |
| 28 | G4 | G3 | 2 | 3 | True | True |
| 29 | G4 | G3 | 1 | 3 | True | True |

### pulse2

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 0 | F5 | G4 | 7 | 5 | True | True |
| 1 | F5 | G4 | 6 | 6 | True | True |
| 2 | F5 | G4 | 5 | 7 | True | True |
| 3 | F5 | G4 | 4 | 6 | True | True |
| 4 | F5 | G4 | 3 | 5 | True | True |
| 5 | F5 | G4 | 3 | 4 | True | True |
| 6 | D#5 | F4 | 7 | 5 | True | True |
| 7 | D#5 | F4 | 6 | 6 | True | True |
| 8 | D#5 | F4 | 5 | 7 | True | True |
| 9 | D#5 | F4 | 4 | 6 | True | True |
| 10 | D#5 | F4 | 3 | 5 | True | True |
| 11 | D#5 | F4 | 3 | 4 | True | True |
| 12 | C5 | G4 | 7 | 5 | True | True |
| 13 | C5 | G4 | 6 | 6 | True | True |
| 14 | C5 | G4 | 5 | 7 | True | True |
| 15 | C5 | G4 | 4 | 6 | True | True |
| 16 | C5 | G4 | 3 | 5 | True | True |
| 17 | C5 | G4 | 3 | 4 | True | True |
| 18 | A#4 | C4 | 7 | 5 | True | True |
| 19 | A#4 | C4 | 6 | 6 | True | True |
| 20 | A#4 | C4 | 5 | 7 | True | True |
| 21 | A#4 | C4 | 4 | 6 | True | True |
| 22 | A#4 | C4 | 3 | 5 | True | True |
| 23 | A#4 | C4 | 3 | 4 | True | True |
| 24 | C5 | C4 | 7 | 3 | True | True |
| 25 | C5 | C4 | 6 | 3 | True | True |
| 26 | C5 | C4 | 5 | 3 | True | True |
| 27 | C5 | C4 | 4 | 3 | True | True |
| 28 | C5 | C4 | 3 | 3 | True | True |
| 29 | C5 | C4 | 3 | 3 | True | True |

### triangle

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 0 | F4 | --- | 15 | 0 | True | False |
| 1 | F4 | --- | 15 | 0 | True | False |
| 2 | F4 | --- | 15 | 0 | True | False |
| 3 | F4 | --- | 15 | 0 | True | False |
| 4 | F4 | --- | 15 | 0 | True | False |
| 5 | F4 | --- | 0 | 0 | False | False |
| 6 | D#4 | --- | 15 | 0 | True | False |
| 7 | D#4 | --- | 15 | 0 | True | False |
| 8 | D#4 | --- | 15 | 0 | True | False |
| 9 | D#4 | --- | 15 | 0 | True | False |
| 10 | D#4 | --- | 15 | 0 | True | False |
| 11 | D#4 | --- | 0 | 0 | False | False |
| 12 | C4 | --- | 15 | 0 | True | False |
| 13 | C4 | --- | 15 | 0 | True | False |
| 14 | C4 | --- | 15 | 0 | True | False |
| 15 | C4 | --- | 15 | 0 | True | False |
| 16 | C4 | --- | 15 | 0 | True | False |
| 17 | C4 | --- | 0 | 0 | False | False |
| 18 | A#3 | --- | 15 | 0 | True | False |
| 19 | A#3 | --- | 15 | 0 | True | False |
| 20 | A#3 | --- | 15 | 0 | True | False |
| 21 | A#3 | --- | 15 | 0 | True | False |
| 22 | A#3 | --- | 15 | 0 | True | False |
| 23 | A#3 | --- | 0 | 0 | False | False |
| 24 | C4 | --- | 15 | 0 | True | False |
| 25 | C4 | --- | 15 | 0 | True | False |
| 26 | C4 | --- | 15 | 0 | True | False |
| 27 | C4 | --- | 15 | 0 | True | False |
| 28 | C4 | --- | 15 | 0 | True | False |
| 29 | C4 | --- | 0 | 0 | False | False |
