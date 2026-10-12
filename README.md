# AI vibe slop up ahead
I, am no engineer, unfortunately this means that this project was mostly AI assisted (via Anthropic's Claude), I just provided the guidance, along with the trial and error.
but this should be pretty valid, at least. To me.

# Obsidian2 90-2440 unlock (Windows XP)
<img width="868" height="449" alt="thumbnail" src="https://github.com/user-attachments/assets/a550c18e-80f6-48fe-b518-1a8b3dc5a140" />

Unlocks the security-locked **Quantum3D Obsidian2 90-2440** (a Voodoo2-class OEM arcade board with the
546-0024-03 CPLD) from a normal Windows XP PC, so Glide / 3D programs can use it.

The board's CPLD stays "locked" (no 3D output) until it gets the challenge/response handshake the
Hydro Thunder arcade software performs at start-up. This tool replays that handshake through
[RWEverything](http://rweverything.com/) (`Rw.exe`). No game files are needed.

## Status

Works on the tested setup below: after the handshake the card renders (Glide demos, Half-Life 1 showed video).
Without it, the card shows nothing. **Tested on one machine only.**
The machine that this was tested on was a real Quantum3D Quicksilver II with some upgrades, if you have a system alike this should more than likely work out.

| | |
|---|---|
| Card | Quantum3D Obsidian2 90-2440, CPLD 546-0024-03 |
| PC | Intel SE440BX-2, Pentium III 450 MHz, 768 MB RAM |
| Display card | GeForce MX440 (AGP); the 90-2440 is in a PCI slot |
| OS | Windows XP |
| Driver for the 3D card | [PeDiniz Voodoo2 driver, v2xp (athlon)](https://3dfxarchive.com/downloads/PeDiniz-v2xp-(athlon).zip) |
| Python | 2.7.18, 32-bit (Python 3 is untested) |
| RWEverything | 1.5.3.7, at `C:\Program Files\Rw-Everything\Rw.exe` |

## How to use

1. Install RWEverything and Python 2.7. Install your 3D driver for the card as usual.
2. Boot the PC. **Close all Glide / 3D programs.**
3. Double-click `unlock.bat` (or run `python unlock.py`).
   - The first run does a one-time setup (a few seconds) and then the handshake.
   - The handshake takes a few minutes on a Pentium III (each dot is one `Rw.exe` call).
4. Wait for `UNLOCKED: 8/8 replies matched`, then start your 3D program.

**The unlock does not survive a restart or power-off - run it again after every boot**, before your 3D program.
A warm restart from Windows locked the card again in testing.

Other commands: `python unlock.py check` (read-only), `python unlock.py setup` (redo setup),
`--ask` (wait for Enter before touching the card), `--bar 0xADDR` (if your card's BAR0 is not
`0xFE000000`; find it in Device Manager or with RWEverything's PCI view), `--rw PATH` (location of `Rw.exe`).
Results are logged to `C:\unlock_log.txt`; settings are kept in `C:\unlock_cfg.txt`.

If the setup reports that `0x244` reads `0x00000000` or `0xFFFFFFFF`, the BAR address is wrong or the
card is not responding.

## Known problems and cautions

- **No video pass-through.** The 90-2440 has no pass-through port [(unless modded)](https://github.com/jeffqchen/quantum3d_obsidian2_voodoo2_info), so the monitor has to be moved between the display card
  and the 3D card. Swapping the cable while Windows was running crashed the test PC twice. (this could've been due to memory editing at the time, I do not know if this is confirmed but it happened twice.)
   Safer: a second monitor, an A/B VGA switch, or shutting down before moving the cable. The tool does not need video while
  it runs, so you can run it with the display-card monitor attached and move the cable afterwards.
- **"Mapmem driver initialization failure" (3dfx fxPCI library).** Seen on some launches of Glide programs
  after running other commands from earlier test versions of this tool. It did **not** appear on a fresh boot
  followed by a single `unlock.py` run, and video rendered even when it did appear. The cause is not
  understood. If you see it, reboot and run `unlock.py` first thing, with nothing else before it.
- Close Glide programs before running the tool.
- **This writes to hardware registers.** The tool restores the two registers it touches when it finishes
  (also on Ctrl+C), but use it at your own risk. A hang is possible; a power-cycle resets the card.

## How it works (short)

The card exposes two registers in BAR0 that the 3dfx init code uses as a bit-banged serial line
to the CPLD

- `BAR0+0x244` (fbiInit5): bit 4 = clock, bit 27 = enable
- `BAR0+0x248` (fbiInit6): bits 12:11 = data line (written high or low; read back as the CPLD's answer)

A transfer is 11-bit frames, LSB first (`byte | 0x100`). A "word" is 32 bits sent as four frames, then a
read command (`0x500`) and 32 clocked reads. The first word of a pass is preceded by a 16-byte start
sequence. The CPLD's reply for each word is:

    reply = DataMap1(word) ^ base
            ^ DataMap2(previous reply)      (omitted for the first word of a pass)

with `base = 0x7D3E9554` for the first word and `0x511B5522` for the others; `DataMap1/2` are fixed
32-bit bit permutations (`M1`, `M2` in `unlock.py`). The tool sends the eight "video enable" words and
checks each reply against that formula; all eight must match. The expected replies are
`1278EE11 00090000 70004001 0900FF70 00007000 10040500 33090760 7FF44F50`.

The register sequence is a port of the original game callback. `tests/test_trace_replay.py` compares it
write-for-write with a recording of that callback (3299 writes) and needs no hardware:

    python tests/test_trace_replay.py

`tests/test_pipeline.py` runs the whole tool against a fake `Rw.exe` (Linux/macOS; plumbing only).

## What is not included

No game executables, ROM images, disk dumps or other copyrighted material. The tool only implements the
handshake, so you must own the hardware it is meant for.

## Credits

This work started from existing Hydro Thunder projects. Those aim to make Hydro Thunder run on any
video card; this tool instead unlocks this specific card for general Glide / 3D use.

- [HT-Diego](https://github.com/pdaderko/HT-Diego/) - the Hydro Thunder / Diego I/O board project where the
  work was first found.
- [Arcade-Museum forum thread "Confirmed working Hydro Thunder video card security bypass"](https://forums.arcade-museum.com/threads/confirmed-working-hydro-thunder-video-card-security-bypass.357654/page-13#post-3216337)
  - had the Hydro Thunder script files used heavily early on to check the card's behaviour.
- [PeDiniz Voodoo2 driver, v2xp (athlon)](https://3dfxarchive.com/downloads/PeDiniz-v2xp-(athlon).zip) - the driver used on the test PC.
- [RWEverything](https://rweverything.com/) - register access requirement.
- [TDFX](http://www.tdfx.de/eng/obsidian2_90-2440.shtml) - reference photo for thumbnail.

Honorable mention: [jeffqchen/quantum3d_obsidian2_voodoo2_info](https://github.com/jeffqchen/quantum3d_obsidian2_voodoo2_info) -
in-depth information and mods for the Quantum3D Obsidian2 Voodoo 2 card, for hardware-level mods.


## License

Public domain, under the [Unlicense](LICENSE). The code was written with AI assistance (Claude) during
hands-on testing. The projects listed under Credits keep their own licenses; nothing from them is copied here.
