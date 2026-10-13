"""TEMPORARY marker (test-side), reverted by restoring the backup in tests/_probe_out/redirect_backup_dir.txt."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()
a = '''                                        page.goto(target, wait_until="domcontentloaded", timeout=30000)
                                        _settle(page)
                                        _step1_cur_url = page.url
                                        _step1_cur_host = urlsplit(_step1_cur_url).netloc
'''
assert s.count(a) == 1
b = a.replace('page.goto(target,', '_r_tmp = page.goto(target,', 1) + '''                                        open("D:/new_test/tests/_probe_out/redirect_marker.txt", "a").write("[PROOF-TEMP] step1 mismatch branch: target=" + repr(target) + " landed=" + repr(_step1_cur_url) + " resp_status=" + repr(_r_tmp.status if _r_tmp else None) + " redirected_from=" + repr(_r_tmp.request.redirected_from.url if _r_tmp and _r_tmp.request.redirected_from else None) + chr(10))
'''
s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('marker added')
