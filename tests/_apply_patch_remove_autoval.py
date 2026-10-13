"""One-off patch applier (test-side): removes the recorder's automatic validate injection (both methods + call)."""
p = 'recorder/record_session.py'
s = open(p, encoding='utf-8').read()

# 1) the call site
call = '''        # the field-presence path (multi-field signup/details forms) is a
        # deliberately separate, later check - it only runs when the
        # single search-field path above found nothing to insert, so the
        # two never fire for the same trigger
        self._maybe_auto_insert_validate()

'''
assert s.count(call) == 1
s = s.replace(call, '''        # recording captures ONLY what the user did: nothing here ever adds an
        # action (validation/assert included) on its own - a validation step
        # exists only if the user adds it deliberately through the editor's
        # "Add Action"
        print("[auto-validate] no automatic validation step is added (injection removed)")  # TEMP-PROOF

''')

# 2) both auto-injecting methods, up to the next method
start = s.index('    def _maybe_auto_insert_validate(self):')
end = s.index('    def _ensure_active(self, page_id, ts):')
assert start < end
s = s[:start] + s[end:]
open(p, 'w', encoding='utf-8').write(s)
print('patched OK; removed', s.count('\n'), 'lines remain')
