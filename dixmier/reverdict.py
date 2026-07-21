"""Reclassify finished cells from their msolve .out files.

fleet.py <= 69e92e3 mislabeled every cell NONEMPTY because it did not strip
msolve's '#' comment headers before looking for the trivial basis [1].
This reads each cell_*.out and prints the correct verdict, one per line:
  <tag>: EMPTY | NONEMPTY?! | NO_OUTPUT  (basis length if reported)
"""
import glob
import re

for f in sorted(glob.glob('cell_*.out')):
    out = open(f).read()
    body = ''.join(l.strip() for l in out.splitlines()
                   if not l.lstrip().startswith('#')).replace(' ', '')
    m = re.search(r'#length of basis:\s*(\d+)', out)
    blen = m.group(1) if m else '?'
    if not body:
        v = 'NO_OUTPUT'
    elif body.rstrip(':,;') == '[1]':
        v = 'EMPTY'
    else:
        v = 'NONEMPTY?!'
    print(f'{f[5:-4]}: {v} [basis length {blen}]')
