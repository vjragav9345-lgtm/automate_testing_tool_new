from sidecheck_helpers import *
with FixtureServer() as fx:
    tc = record(fx.url("sc_b_ids.html"), lambda pg: (pg.locator("#oa").click(), pg.wait_for_timeout(700), pg.locator("#ob").click(), pg.wait_for_timeout(700), pg.locator("#oa").click(), pg.wait_for_timeout(700)), "sc_b_ids")
    for a in tc["actions"]:
        print("ACT", {k:a.get(k) for k in ("action_type","page_url","expected_url","caused_by_timestamp","delay_before_ms","induced_by_prev")})
