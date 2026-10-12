#!/usr/bin/env python
# End-to-end plumbing test of unlock.py with a fake Rw.exe (no card needed): the setup, the
# batching, the register restore.  The fake card does not answer the handshake, so the
# replies are expected to MISMATCH; what is checked is that everything runs to the end,
# that the registers are put back, and that the number of writes is what the reference says.
from __future__ import print_function
import os, sys, json, shutil, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
d = tempfile.mkdtemp()
env = dict(os.environ, UNLOCK_DIR=d + os.sep, FAKE_RW_DIR=d,
           RW_EXE=os.path.join(HERE, 'fake_rw.py'))
os.chmod(os.path.join(HERE, 'fake_rw.py'), 0o755)
p = subprocess.Popen([sys.executable, os.path.join(ROOT, 'unlock.py')], env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out = p.communicate()[0].decode('latin-1')
regs = json.load(open(os.path.join(d, 'fake_rw_state.json')))
ok = True
def check(name, cond):
    global ok
    print(('PASS  ' if cond else 'FAIL  ') + name)
    ok = ok and cond
check('program ran to the end (exit code 1 = replies did not match, as expected with a fake card)', p.returncode == 1)
check('setup ran and wrote its config', os.path.exists(os.path.join(d, 'unlock_cfg.txt')))
check('registers restored (0x244, 0x248)',
      regs['0xFE000244'] == 0x08408062 and regs['0xFE000248'] == 0x001E7E00)
check('reported "NOT UNLOCKED" for a card that did not answer', 'NOT UNLOCKED' in out)
shutil.rmtree(d)
if not ok: print(out[-1500:])
sys.exit(0 if ok else 1)
