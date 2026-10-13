"""One-off patch applier (TEST-SIDE helper): step-1 navigate host comparison ignores a leading 'www.'."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


sub('''def _drag_values_equal(''', '''def _hosts_equivalent(host_a, host_b):
    """Same site, ignoring only a leading "www." on either side (and case).
    CONFIRMED: https://www.<domain>/ answers with a server-side redirect to
    https://<domain>/ (and the reverse exists on other sites) - the same
    site, not a wrong page. Any other difference (another domain, a
    different subdomain, a different port) is still a different host."""
    if not host_a or not host_b:
        return False

    def _bare(h):
        h = h.lower()
        return h[4:] if h.startswith("www.") else h

    return _bare(host_a) == _bare(host_b)


def _drag_values_equal(''')
sub('''if _step1_cur_host and _step1_target_host and _step1_cur_host == _step1_target_host:''',
    '''if _hosts_equivalent(_step1_cur_host, _step1_target_host):''')
sub('''_step1_ok = bool(_step1_target_host) and _step1_cur_host == _step1_target_host''',
    '''_step1_ok = _hosts_equivalent(_step1_cur_host, _step1_target_host)''')
open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
