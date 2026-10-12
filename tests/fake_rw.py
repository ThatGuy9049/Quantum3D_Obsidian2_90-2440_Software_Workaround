#!/usr/bin/env python
# Stand-in for Rw.exe, only for testing unlock.py's plumbing on a machine without the card.
# Understands R32/W32 chained with ';' and keeps register values in fake_rw_state.json.
# Use:  RW_EXE=tests/fake_rw.py UNLOCK_DIR=/some/dir/ python unlock.py     (see tests/test_pipeline.py)
import sys, json, os, re
st = os.path.join(os.environ.get('FAKE_RW_DIR', '.'), 'fake_rw_state.json')
regs = {'0xFE000244': 0x08408062, '0xFE000248': 0x001E7E00}
if os.path.exists(st): regs = json.load(open(st))
cmd = [a for a in sys.argv[1:] if a.startswith('/Command=')][0][9:]
logf = [a[9:] for a in sys.argv[1:] if a.startswith('/LogFile=')]
out = []
for p in re.split(r'\s*;\s*|\n', cmd):
    t = p.split()
    if not t: continue
    key = '0x%08X' % int(t[1], 16)
    if t[0] == 'R32': out.append('Read Memory Address %s = 0x%08X' % (key, regs.get(key, 0)))
    elif t[0] == 'W32': regs[key] = int(t[2], 16); out.append('Write Memory Address %s = 0x%08X' % (key, regs[key]))
json.dump(regs, open(st, 'w'))
txt = '\n'.join(out) + '\n'
sys.stdout.write(txt)
if logf: open(logf[0], 'w').write(txt)
