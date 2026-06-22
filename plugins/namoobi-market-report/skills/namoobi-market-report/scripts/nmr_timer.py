#!/usr/bin/env python3
# nmr_timer.py (v3.21) -- lightweight per-phase wall-clock logging for namoobi-market-report.
# Cheap: each phase boundary appends one line; Phase 6 prints a per-phase breakdown so we can
# SEE where the ~1h goes (Phase 1 collection vs Phase 5 send vs gate rework) and prove savings.
# Usage:
#   nmr_timer.py mark   <label> [logfile]   -> append "<epoch> <label>"
#   nmr_timer.py report [logfile]           -> Phase-by-phase durations + total
# default logfile: <outputs>/nmr_build/nmr_phase_times.txt
import sys, os, glob, time, datetime as dt

def find_log():
    for b in glob.glob('/sessions/*/mnt/outputs/nmr_build'):
        return os.path.join(b, 'nmr_phase_times.txt')
    return 'nmr_phase_times.txt'

def fmt(s):
    s=int(round(s)); m,sec=divmod(s,60)
    return ("%dm %02ds"%(m,sec)) if m else ("%ds"%sec)

def mark(label, log):
    os.makedirs(os.path.dirname(log) or '.', exist_ok=True)
    with open(log,'a',encoding='utf-8') as f:
        f.write("%d %s\n"%(int(time.time()), label))
    print("⏱ mark %s @ %s"%(label, dt.datetime.now().strftime('%H:%M:%S')))

def report(log):
    try:
        pts=[(int(t),lab) for t,lab in
             (ln.strip().split(None,1) for ln in open(log,encoding='utf-8') if ln.strip())]
    except FileNotFoundError:
        print("(phase log 없음: %s)"%log); return
    if len(pts)<2:
        print("(mark 2개 이상 필요 — 현재 %d개)"%len(pts)); return
    print("Phase별 소요(벽시계)")
    print("%-26s %10s" % ("구간","소요"))
    print("-"*38)
    for (t0,l0),(t1,_l1) in zip(pts, pts[1:]):
        print("%-26s %10s" % (l0, fmt(t1-t0)))
    print("-"*38)
    print("%-26s %10s" % ("합계(%s→%s)"%(pts[0][1],pts[-1][1]), fmt(pts[-1][0]-pts[0][0])))

def main():
    a=sys.argv[1:]
    if not a: print("usage: mark <label> [log] | report [log]"); sys.exit(2)
    if a[0]=='mark' and len(a)>=2:
        mark(a[1], a[2] if len(a)>2 else find_log())
    elif a[0]=='report':
        report(a[1] if len(a)>1 else find_log())
    else:
        print("usage: mark <label> [log] | report [log]"); sys.exit(2)

if __name__=='__main__': main()
