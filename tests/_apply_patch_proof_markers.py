"""TEMPORARY proof markers (test-side); reverted by restoring the backup in tests/_probe_out/proof_backup_dir.txt."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()
M = 'open("D:/new_test/tests/_probe_out/proof_markers.txt", "a").write('
a = '''    if not host_a or not host_b:
        return False

    def _bare(h):'''
assert s.count(a) == 1
s = s.replace(a, '    ' + M + 'f"[PROOF-TEMP] _hosts_equivalent {host_a!r} vs {host_b!r}" + chr(10))\n' + a)
import re
m = re.search(r'(def _drag_verify_held\([^)]*\):\n(?:    """.*?"""\n)?)', s, re.S)
s = s.replace(m.group(1), m.group(1) + '    ' + M + '"[PROOF-TEMP] _drag_verify_held reached" + chr(10))\n', 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
