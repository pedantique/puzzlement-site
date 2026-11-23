#!/usr/bin/env python3
"""Merge a contributor's catalog pull request by data, not by text.

Pull requests branched from the same main all touch `updated` and the end of
`added`, so a second one conflicts as text though its change is independent.
This applies the branch's change (against the merge base) onto HEAD:
new `added` entries are appended, entries the branch changed replace HEAD's
when HEAD left them alone, `puzzles` overrides likewise, and `updated` is
bumped. Anything that can't be applied cleanly is reported, not guessed.

Run from the repo root, after `git fetch`:
    git merge --no-ff --no-commit origin/<branch>   # conflicts are fine
    git checkout HEAD -- catalog/catalog.json
    python3 catalog/merge_pr.py <branch>
    git checkout origin/<branch> -- img/icons/<new>.png
    git add -A catalog img && git commit -m "Merge pull request #N from <owner>/<branch>"
"""
import datetime
import json
import subprocess
import sys

branch = sys.argv[1]


def show(ref):
    return json.loads(subprocess.check_output(['git', 'show', f'{ref}:catalog/catalog.json']))


mb = subprocess.check_output(['git', 'merge-base', 'HEAD', f'origin/{branch}']).decode().strip()
base, head, theirs = show(mb), show('HEAD'), show(f'origin/{branch}')
bmap = {a['id']: a for a in base['added']}
hidx = {a['id']: i for i, a in enumerate(head['added'])}
for a in theirs['added']:
    i = a['id']
    if i not in bmap:
        if i in hidx:
            print('SKIP already in HEAD', i)
        else:
            head['added'].append(a)
            print('added', i)
    elif a != bmap[i]:
        if i not in hidx:
            print('CONFLICT removed in HEAD', i)
        elif head['added'][hidx[i]] != bmap[i]:
            print('CONFLICT both changed', i)
        else:
            head['added'][hidx[i]] = a
            print('changed', i)
tids = {a['id'] for a in theirs['added']}
for i in bmap:
    if i not in tids:
        print('WARNING branch removed', i)
bp, hp, tp = base.get('puzzles', {}), head.setdefault('puzzles', {}), theirs.get('puzzles', {})
for k, v in tp.items():
    if bp.get(k) != v:
        if hp.get(k) != bp.get(k):
            print('CONFLICT override both changed', k)
        else:
            hp[k] = v
            print('override', k)
# Puzzles of the week, keyed by week and slot.
def week(f):
    return (f.get('start'), f.get('slot'))


bf = {week(f): f for f in base.get('featured', [])}
hf = {week(f): i for i, f in enumerate(head.get('featured', []))}
for f in theirs.get('featured', []):
    k = week(f)
    if f == bf.get(k):
        continue
    if k not in hf:
        if k in bf:
            print('CONFLICT featured removed in HEAD', k)
        else:
            head.setdefault('featured', []).append(f)
            print('featured', k)
    elif head['featured'][hf[k]] == bf.get(k):
        head['featured'][hf[k]] = f
        print('featured changed', k)
    elif head['featured'][hf[k]] != f:
        print('CONFLICT featured both changed', k)
for k in set(bf) - {week(f) for f in theirs.get('featured', [])}:
    print('WARNING branch removed featured', k)
for k in set(base) | set(theirs):
    if k not in ('added', 'puzzles', 'updated', 'featured') and base.get(k) != theirs.get(k):
        print('WARNING', k, 'changed in branch')
head['updated'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
open('catalog/catalog.json', 'w').write(json.dumps(head, indent=2, ensure_ascii=False) + '\n')
