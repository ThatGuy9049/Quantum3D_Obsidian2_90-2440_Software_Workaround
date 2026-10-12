#!/usr/bin/env python
# unlock.py - unlock the Quantum3D Obsidian2 90-2440 (Voodoo2 OEM arcade board, CPLD 546-0024-03)
# from Windows XP, by replaying the Hydro Thunder CPLD challenge/response handshake through
# RWEverything (Rw.exe).  Python 2.7 or 3.
#
#   python unlock.py            run the handshake (8 words).  First run does a quick one-time setup.
#   python unlock.py check      read-only: shows what Rw.exe reads from the card.  Writes nothing.
#   python unlock.py setup      redo the one-time setup (re-measures Rw.exe batching)
#   options:  --ask    wait for Enter before touching the card
#             --bar N  card BAR0 address (default 0xFE000000)   --rw PATH   path to Rw.exe
#
# The unlock lasts until the PC is restarted or powered off - run it again after every boot,
# BEFORE starting your Glide / 3D application.
#
# The handshake is a port of the original _security_Callback from the Hydro Thunder game
# executable; the port was checked write-for-write against that code (see tests/).
# This tool writes to hardware registers.  Use at your own risk.
# Public domain (Unlicense, see LICENSE).
from __future__ import print_function
import os, sys, re, time, subprocess

USAGE = """unlock.py - unlock the Quantum3D Obsidian2 90-2440 from Windows XP
  python unlock.py          run the handshake (first run does a quick one-time setup)
  python unlock.py check    read-only: show what Rw.exe reads from the card
  python unlock.py setup    redo the one-time setup
options: --ask (wait for Enter first)  --bar N  --rw PATH
Run it after every boot, BEFORE starting your Glide / 3D application.
Log: C:\\unlock_log.txt
"""

VERSION = '1.0'
_DEF = r'C:\Program Files\Rw-Everything\Rw.exe'
RW = os.environ.get('RW_EXE') or (_DEF if os.path.exists(_DEF) else 'Rw.exe')
BAR = 0xFE000000

# working files: C:\ on Windows (a path without spaces), the current folder elsewhere.
# Override with the UNLOCK_DIR environment variable.
_DIR = os.environ.get('UNLOCK_DIR') or ('C:\\' if os.name == 'nt' else '')
CFG = os.path.join(_DIR, 'unlock_cfg.txt')
OUT = os.path.join(_DIR, 'unlock_log.txt')
LOGF = os.path.join(_DIR, 'unlock_rw.log')

# ---------------- algorithm (verified against real captures) ----------------
M1 = [0x7,0x2,0x4,0x5,0x6,0x1,0x0,0x3,0xC,0xB,0xE,0x9,0xD,0xF,0x8,0xA,
      0x13,0x15,0x14,0x11,0x10,0x17,0x12,0x16,0x18,0x1A,0x1D,0x1F,0x19,0x1B,0x1C,0x1E]
M2 = [0x2,0x1D,0x14,0x5,0x1F,0xC,0xE,0x11,0x1,0x16,0x19,0x9,0x6,0x1B,0x13,0x3,
      0x10,0xD,0x15,0x8,0x0,0x1C,0xA,0x1E,0x4,0x18,0xB,0x12,0x17,0xF,0x1A,0x7]
def _map(x, m):
    r = 0
    for i in range(32):
        r |= ((x >> i) & 1) << m[i]
    return r
def expected(data, prev, start):
    """the reply the CPLD must give: DataMap1(data) ^ base, then (not start) ^ DataMap2(prev reply)"""
    out = _map(data, M1) ^ (0x7D3E9554 if start else 0x511B5522)
    if not start:
        out ^= _map(prev, M2)
    return out & 0xFFFFFFFF
def swap32(x):
    return ((x & 0xFF) << 24) | ((x & 0xFF00) << 8) | ((x >> 8) & 0xFF00) | ((x >> 24) & 0xFF)

START_BYTES = [83,107,77,25, 122,35,18,57, 83,29,5,45, 55,22,60,79]
VIDEO_WORDS = [0xB7C85F52,0xB8AD0DEA,0x050D8168,0xE23C1A36,0xF9DCDD9C,0xA15C0538,0x842E0D10,0x274B6E18]

# ---------------- the original callback, step for step ----------------
# Registers are card BAR0 + 0x244 (fbiInit5: bit 4 = clock, bit 27 = GPIO control enable) and
# + 0x248 (fbiInit6: bits 12:11 = data line).  11-bit frames, LSB first, byte | 0x100.
class Card(object):
    """bus needs: r(off), w(off, val), flush(), rq(off), collect(handles)."""
    def __init__(self, bus):
        self.bus = bus; self.b1 = 0; self.b2 = 0
    def _sigwrite(self, data):                       # _sst1InitSigWrite
        b, b1, b2 = self.bus, self.b1, self.b2
        b.w(0x244, b1 | 0x10); b.w(0x248, b2 | 0x1800); b.flush()
        b.w(0x248, b2 | 0x1000); b.flush()
        self._bits(data)
        b.w(0x244, b1); b.w(0x248, b2 | 0x800); b.flush()
    def _bits(self, data):                           # 11 bits, LSB first
        b, b1, b2 = self.bus, self.b1, self.b2
        for i in range(11):
            b.w(0x244, b1); b.flush()
            b.w(0x248, b2 | (0x1800 if (data >> i) & 1 else 0x1000))
            b.w(0x244, b1); b.flush()
            b.w(0x244, b1 | 0x10); b.flush()
    def _rearm(self):
        b, b1, b2 = self.bus, self.b1, self.b2
        b.w(0x244, b1 | 0x10); b.w(0x248, b2 | 0x1800); b.flush()
        b.w(0x248, b2 | 0x1000); b.flush()
    def _release(self):
        b, b1, b2 = self.bus, self.b1, self.b2
        b.w(0x244, b1); b.w(0x248, b2 | 0x800); b.flush()
    def _sigread(self):                              # _sst1InitSigRead
        b, b1, b2 = self.bus, self.b1, self.b2
        b.w(0x244, b1 | 0x10); b.w(0x248, b2 | 0x1800); b.flush()
        b.w(0x248, b2 | 0x1000); b.flush()
        self._bits(0x500)
        self._release(); b.flush()
        hs = []
        for i in range(32):
            b.w(0x244, b1 | 0x10); b.flush()
            hs.append(b.rq(0x248))
            if i < 31:
                b.w(0x244, b1); b.flush()
        val = 0
        for i, v in enumerate(b.collect(hs)):
            if v & 0x1800:                           # ANY of bit 11/12, like the game
                val |= 1 << i
        return val
    def callback(self, word, start):
        """returns (byte-swapped reply as the game hands it to the I/O board, raw 32-bit read)"""
        b = self.bus
        if start:
            v = b.r(0x244); b.w(0x244, v | 0x8000000)
            self.b1 = b.r(0x244) & 0xFFFFFFEF
            self.b2 = b.r(0x248) & 0xFFFFE7FF
            b.w(0x244, self.b1); b.flush()
            self._sigwrite(0)
            for i in range(16):
                self._sigwrite(START_BYTES[i] | 0x100)
        self.b1 = b.r(0x244) & 0xFFFFFFEF
        self.b2 = b.r(0x248) & 0xFFFFE7FF
        b1, b2 = self.b1, self.b2
        b.w(0x244, b1 | 0x10); b.w(0x248, b2 | 0x1800); b.flush()
        b.w(0x248, b2 | 0x1000); b.flush()
        self._bits((word & 0xFF) | 0x100); self._release(); self._rearm()
        self._bits(((word >> 8) & 0xFF) | 0x100); self._release(); self._rearm()
        self._bits(((word >> 16) & 0xFF) | 0x100); self._release()
        self._sigwrite((word >> 24) | 0x100)
        raw = self._sigread()
        return swap32(raw), raw

# ---------------- Rw.exe bus ----------------
class RwError(Exception): pass

def tokens(text):
    return [int(m.group(0), 16) for m in
            re.finditer(r'0[xX][0-9A-Fa-f]{1,8}|\b[0-9A-Fa-f]{8}\b', text)]

def parse_reads(text, n):
    """values of the 'Read Memory Address 0x... = 0x...' lines, in order (de-duplicated
    if the same text arrives twice, via stdout and the log file)"""
    got = [int(m.group(2), 16) for m in re.finditer(
        r'Read Memory Address\s+(0[xX][0-9A-Fa-f]+)\s*=\s*(0[xX][0-9A-Fa-f]+)', text)]
    if len(got) == 2 * n and got[:n] == got[n:]:
        got = got[:n]
    if not got and n == 1:                      # unknown output style: fall back to last number
        t = tokens(text)
        got = t[-1:] if t else []
    return got

class RwBus(object):
    def __init__(self, cfg, coalesce=True):
        self.sep = cfg.get('sep', '')              # '' = no chaining
        self.pending = []; self.shadow = {}
        self.chunk = int(cfg.get('chunk', '24')); self.rvals = []; self.rq_n = 0
        self.coalesce = coalesce
        self.calls = 0; self.cmds = 0; self.t = 0.0
        self.verbose = False
    def run(self, cmds):
        text = (self.sep.join(cmds) if self.sep else cmds[0])
        if os.path.exists(LOGF):
            try: os.remove(LOGF)
            except OSError: pass
        if os.name == 'nt':
            exe = ('"%s"' % RW) if (' ' in RW and not RW.startswith('"')) else RW
            args = '%s /Min /Nologo /Stdout /Command="%s" /LogFile=%s' % (exe, text, LOGF)
        else:
            args = [RW, '/Min', '/Nologo', '/Stdout', '/Command=' + text, '/LogFile=' + LOGF]
        t0 = time.time()
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            o = p.communicate()[0]
        except OSError as e:
            raise RwError('cannot start %s: %s\n(set the path with --rw "C:\\path\\Rw.exe")' % (RW, e))
        self.t += time.time() - t0; self.calls += 1; self.cmds += len(cmds)
        if self.verbose:
            sys.stdout.write('.'); sys.stdout.flush()
        if not isinstance(o, str):
            o = o.decode('latin-1')
        if os.path.exists(LOGF):
            try:
                f = open(LOGF, 'r'); o += '\n' + f.read(); f.close()
            except IOError: pass
        return o
    def _addr(self, off): return BAR + off
    def w(self, off, val):
        val &= 0xFFFFFFFF
        if self.coalesce and self.shadow.get(off) == val:   # shadow = last value WE wrote
            return
        self.shadow[off] = val
        self.pending.append('W32 0x%08X 0x%08X' % (self._addr(off), val))
        if not self.sep or len(self.pending) >= self.chunk:
            self._send_pending()
    def _send_pending(self):
        while self.pending:
            n = self.chunk if self.sep else 1
            chunk = self.pending[:n]; del self.pending[:n]
            o = self.run(chunk)
            nr = len([c for c in chunk if c.startswith('R32')])
            if nr:
                got = parse_reads(o, nr)
                if len(got) != nr:
                    raise RwError('expected %d read values, got %d. Output:\n%s' % (nr, len(got), o[-400:]))
                self.rvals.extend(got)
    def flush(self): pass
    def rq(self, off):
        """queue a read now; its value is available from collect()"""
        self.pending.append('R32 0x%08X' % self._addr(off))
        self.rq_n += 1
        h = self.rq_n - 1
        if not self.sep or len(self.pending) >= self.chunk:
            self._send_pending()
        return h
    def collect(self, handles):
        self._send_pending()
        return [self.rvals[h] for h in handles]
    def r(self, off):
        if off == 0: return 0x0FFFF07F
        return self.collect([self.rq(off)])[0]
    def commit(self):
        self._send_pending()

# ---------------- helpers ----------------
def load_cfg():
    c = {}
    if os.path.exists(CFG):
        for line in open(CFG):
            if '=' in line:
                k, v = line.rstrip('\n').split('=', 1); c[k] = v
    return c
def save_cfg(c):
    f = open(CFG, 'w')
    for k in sorted(c): f.write('%s=%s\n' % (k, c[k]))
    f.close()
class Out(object):
    def __init__(self):
        try: self.f = open(OUT, 'a')
        except IOError: self.f = None
    def p(self, s=''):
        print(s)
        if self.f: self.f.write(s + '\n'); self.f.flush()
def ask(msg):
    try: return raw_input(msg)
    except NameError: return input(msg)

def read_regs(o, bus_cfg=None):
    """three single-call reads (0x244, 0x248, 0x244); returns (vals, seconds per call)"""
    b = RwBus({'sep': ''})
    vals = {}; t0 = time.time()
    for off in (0x244, 0x248, 0x244):
        raw = b.run(['R32 0x%08X' % (BAR + off)])
        got = parse_reads(raw, 1)
        if not got:
            raise RwError('could not read 0x%08X from Rw.exe. Output was:\n%s' % (BAR + off, raw[-300:]))
        vals[off] = got[0]
    return vals, (time.time() - t0) / 3.0

# ---------------- read-only check ----------------
def cmd_check(o):
    o.p('== check (read-only) %s  RW=%s  BAR=0x%08X' % (time.strftime('%Y-%m-%d %H:%M:%S'), RW, BAR))
    vals, per = read_regs(o)
    o.p('0x244 = 0x%08X   0x248 = 0x%08X   (%.2f s per Rw.exe call)' % (vals[0x244], vals[0x248], per))
    if vals[0x244] in (0, 0xFFFFFFFF):
        o.p('!! 0x244 reads 0x%08X: wrong BAR address or the card is not responding.' % vals[0x244])
        return False
    o.p('Nothing was written.')
    return True

# ---------------- one-time setup: batching + clean-write test ----------------
def setup(o, cfg):
    o.p('== one-time setup %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    vals, per = read_regs(o)
    o.p('0x244 = 0x%08X  0x248 = 0x%08X  (%.2f s per Rw.exe call)' % (vals[0x244], vals[0x248], per))
    if vals[0x244] in (0, 0xFFFFFFFF):
        o.p('!! 0x244 reads 0x%08X: wrong BAR address or the card is not responding. Stopping.' % vals[0x244])
        return False
    cfg['per'] = '%.3f' % per
    # can several commands share one Rw.exe call?  (makes the run ~100x faster)
    sep = ''
    a244, a248 = BAR + 0x244, BAR + 0x248
    for s in (';', ' ; ', '\n'):
        raw = RwBus({'sep': s}).run(['R32 0x%08X' % a244, 'R32 0x%08X' % a248])
        got = parse_reads(raw, 2)
        if len(got) == 2 and got[0] == vals[0x244] and got[1] == vals[0x248]:
            sep = s; break
    cfg['sep'] = sep
    if sep:
        best = 24
        for n in (24, 48, 96, 192):
            raw = RwBus({'sep': sep}).run(['R32 0x%08X' % a248] * n)
            ok = len(parse_reads(raw, n)) == n
            o.p('batch of %d reads: %s' % (n, 'ok' if ok else 'FAILED'))
            if not ok: break
            best = n
        cfg['chunk'] = str(min(best, 96))
        o.p('using batches of %s commands' % cfg['chunk'])
    else:
        cfg['chunk'] = '1'
        o.p('!! this Rw.exe does not accept several commands per call; the handshake will be VERY slow (hours).')
    # is W32 a clean 32-bit write?  write back the value 0x244 already holds and read it again
    b = RwBus({'sep': ''}); b.coalesce = False
    v = b.r(0x244)
    b.run(['W32 0x%08X 0x%08X' % (a244, v)])
    v2 = b.r(0x244)
    if v2 != v:
        o.p('FAIL: wrote 0x%08X to 0x244, read back 0x%08X. Rw.exe W32 is not a clean write here.' % (v, v2))
        b.run(['W32 0x%08X 0x%08X' % (a244, v)])
        o.p('tried to put it back; 0x244 now reads 0x%08X' % b.r(0x244))
        return False
    o.p('write test passed (wrote back the same value, read back 0x%08X)' % v2)
    cfg['setup'] = VERSION
    save_cfg(cfg)
    return True

# ---------------- the handshake ----------------
def handshake(o, cfg, words, ask_first):
    bus = RwBus(cfg); bus.verbose = True
    t0 = time.time()
    orig244 = bus.r(0x244); orig248 = bus.r(0x248)
    per = (time.time() - t0) / 2.0                  # measured now: the machine may be busy
    if orig244 in (0, 0xFFFFFFFF):
        o.p('!! 0x244 reads 0x%08X, stopping' % orig244); return 0, len(words)

    class Count(object):                             # dry run, only to estimate the time
        def __init__(s): s.n = 0; s.sh = {}
        def r(s, off): return 0x08408062 if off == 0x244 else 0
        def rq(s, off): s.n += 1; return 0
        def collect(s, hs): return [0] * len(hs)
        def w(s, off, val):
            val &= 0xFFFFFFFF
            if s.sh.get(off) != val: s.n += 1; s.sh[off] = val
        def flush(s): pass
    est = 0
    for k in range(len(words)):
        c = Count(); Card(c).callback(words[k], k == 0); est += c.n
    chunk = int(cfg.get('chunk', '24')) if cfg.get('sep') else 1
    calls = (est + 40 * len(words)) / float(chunk) + 2 * len(words)
    o.p('start %s: saved 0x244=0x%08X 0x248=0x%08X' % (time.strftime('%H:%M:%S'), orig244, orig248))
    o.p('about %d register writes, ~%d Rw.exe calls, roughly %.1f minutes (each dot = one call)' %
        (est, calls, calls * per / 60.0))
    if ask_first:
        ask('Press Enter to start (Ctrl+C to cancel) ')
    good = 0; prev = 0
    try:
        card = Card(bus)
        for k, w in enumerate(words):
            t1 = time.time()
            exp = expected(w, prev, k == 0)
            got, raw = card.callback(w, k == 0)
            bus.commit()
            m = 'MATCH' if got == exp else ('MATCH(raw order)' if raw == exp else 'MISMATCH')
            if m != 'MISMATCH': good += 1
            o.p('')
            o.p('word %d/%d  sent 0x%08X  got 0x%08X (raw 0x%08X)  expected 0x%08X  %s  [%.0fs]' %
                (k + 1, len(words), w, got, raw, exp, m, time.time() - t1))
            prev = exp
    finally:
        try:                                          # always put 0x244/0x248 back (also on Ctrl+C)
            bus.commit(); bus.coalesce = False
            bus.w(0x244, orig244); bus.w(0x248, orig248); bus.commit()
            o.p('registers restored: 0x244 = 0x%08X (was 0x%08X), 0x248 = 0x%08X (was 0x%08X)' %
                (bus.r(0x244), orig244, bus.r(0x248), orig248))
        except Exception as e:
            o.p('!! restore failed: %s - power-cycle the PC to reset the card' % e)
    return good, len(words)

def main():
    global BAR, RW
    a = sys.argv[1:]
    if '--bar' in a:
        i = a.index('--bar'); BAR = int(a[i + 1], 0); del a[i:i + 2]
    if '--rw' in a:
        i = a.index('--rw'); RW = a[i + 1]; del a[i:i + 2]
    ask_first = '--ask' in a
    a = [x for x in a if x != '--ask']
    cmd = a[0] if a else 'unlock'
    if cmd not in ('unlock', 'check', 'setup'):
        print(USAGE); return 2
    o = Out()
    try:
        if cmd == 'check':
            return 0 if cmd_check(o) else 1
        cfg = load_cfg()
        need = (cmd == 'setup' or cfg.get('setup') != VERSION or 'chunk' not in cfg)
        if need and not setup(o, cfg):
            o.p('Setup failed - nothing further was done. Send unlock_log.txt if you want help.')
            return 1
        good, total = handshake(o, cfg, VIDEO_WORDS, ask_first)
        o.p('')
        if good == total:
            o.p('UNLOCKED: %d/%d replies matched. You can start your Glide/3D application now.' % (good, total))
            o.p('(The unlock lasts until the PC is restarted or powered off.)')
            return 0
        o.p('NOT UNLOCKED: only %d/%d replies matched. Close any 3D application, make sure nothing else '
            'is touching the card, and run it again.' % (good, total))
        return 1
    except RwError as e:
        o.p('RW ERROR: %s' % e)
        return 1

if __name__ == '__main__':
    sys.exit(main())
