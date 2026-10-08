"""One-off patch applier (TEST-SIDE helper): step-1 navigate accepts a genuine server-side HTTP redirect chain."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


sub('''def _drag_values_equal(''', '''def _redirect_chain_verified(resp, target, final_url):
    """Was `final_url` reached from `target` by a genuine server-side HTTP
    redirect chain? Read from the navigation's own network record (the
    Response's request.redirected_from links), never from hostname rules:
    the chain must start at `target` (or a www/scheme equivalent of it),
    every hop before the last must be a real 3xx response, the last
    response must be a successful (2xx) page load - an error, block or
    challenge page (403/5xx...) doesn't count - and the page must still be
    on that last response's host (a script that moved it elsewhere after
    load is not a redirect). CONFIRMED: a site whose own server answers
    301 to a different domain/TLD is a real redirect, not a wrong page;
    no chain (client-side script redirect, unrelated landing, failed load)
    returns False."""
    try:
        if resp is None or not resp.ok:
            return False
        hops = []
        req = resp.request
        while req is not None:
            hops.append(req)
            req = req.redirected_from
        hops.reverse()
        if len(hops) < 2:
            return False
        for hop in hops[:-1]:
            hop_resp = hop.response()
            if hop_resp is None or not (300 <= hop_resp.status < 400):
                return False
        if not _hosts_equivalent(urlsplit(hops[0].url).netloc, urlsplit(target).netloc):
            return False
        return _hosts_equivalent(urlsplit(resp.url).netloc, urlsplit(final_url).netloc)
    except Exception:
        return False


def _drag_values_equal(''')

sub('''                                        page.goto(target, wait_until="domcontentloaded", timeout=30000)
                                        _settle(page)
                                        _step1_cur_url = page.url
                                        _step1_cur_host = urlsplit(_step1_cur_url).netloc
                                        _step1_ok = _hosts_equivalent(_step1_cur_host, _step1_target_host)
''', '''                                        _step1_resp = page.goto(target, wait_until="domcontentloaded", timeout=30000)
                                        _settle(page)
                                        _step1_cur_url = page.url
                                        _step1_cur_host = urlsplit(_step1_cur_url).netloc
                                        _step1_ok = _hosts_equivalent(_step1_cur_host, _step1_target_host)
                                        if not _step1_ok and _redirect_chain_verified(_step1_resp, target, _step1_cur_url):
                                            _step1_ok = True
                                            print(
                                                f"[redirect] {target} -> {_step1_cur_url} via a server-side "
                                                "HTTP redirect chain (verified from the navigation's network record)"
                                            )
''')
open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
