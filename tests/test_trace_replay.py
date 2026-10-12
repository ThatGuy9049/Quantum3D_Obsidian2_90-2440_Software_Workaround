#!/usr/bin/env python
# Checks unlock.py's handshake against a recorded reference trace.
# reference_trace.json holds the register writes (and replies) produced by the ORIGINAL
# game callback for the 8 video words, recorded once; no game files are needed to run this.
# Run:  python tests/test_trace_replay.py       (Python 2.7 or 3, no hardware needed)
from __future__ import print_function
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import unlock

ref = json.load(open(os.path.join(HERE, 'reference_trace.json')))
sense = lambda n: (0x800 if (n * 7 + 3) % 5 < 2 else (0x1000 if n % 3 == 0 else 0))

class FakeBus(object):
    def __init__(s):
        s.regs = {0x244: ref['init244'], 0x248: ref['init248'], 0: 0x0FFFF07F}
        s.tr = []; s.n = 0
    def r(s, off):
        v = s.regs.get(off, 0)
        if off == 0x248:
            v = (v & ~0x1800) | sense(s.n); s.n += 1
        return v
    def w(s, off, val):
        val &= 0xFFFFFFFF; s.regs[off] = val; s.tr.append([off, val])
    def flush(s): pass
    def rq(s, off): return s.r(off)
    def collect(s, hs): return list(hs)

bus = FakeBus(); card = unlock.Card(bus)
words = ref['words']
results = [card.callback(w, k == 0)[0] for k, w in enumerate(words)]
ok = True
if bus.tr == ref['writes']:
    print('PASS  %d register writes identical to the original callback' % len(bus.tr))
else:
    ok = False
    print('FAIL  write traces differ (mine %d, reference %d)' % (len(bus.tr), len(ref['writes'])))
    for i, (a, b) in enumerate(zip(bus.tr, ref['writes'])):
        if a != b:
            print('  first difference at write %d: mine %s reference %s' % (i, a, b)); break
if results == ref['results']:
    print('PASS  replies identical to the original callback')
else:
    ok = False; print('FAIL  replies differ')
# the reply algorithm itself: first expected word from the real captures
e0 = unlock.expected(unlock.VIDEO_WORDS[0], 0, True)
if e0 == 0x1278EE11:
    print('PASS  expected reply for the first video word is 0x1278EE11')
else:
    ok = False; print('FAIL  expected reply for word 1 is 0x%08X, not 0x1278EE11' % e0)
prev = 0; exp = []
for k, w in enumerate(unlock.VIDEO_WORDS):
    prev = unlock.expected(w, prev, k == 0); exp.append(prev)
want = [0x1278EE11, 0x00090000, 0x70004001, 0x0900FF70, 0x00007000, 0x10040500, 0x33090760, 0x7FF44F50]
if exp == want:
    print('PASS  all 8 expected replies match the known-good list')
else:
    ok = False; print('FAIL  expected replies differ:', [hex(x) for x in exp])
sys.exit(0 if ok else 1)
