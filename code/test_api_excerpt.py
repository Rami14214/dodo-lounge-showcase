"""Excerpt from tests/test_api.py (fixtures and helpers are in the private repo)."""

def test_booking_uses_profile_and_blocks_slot(client):
    login(client)
    r = client.post("/api/bookings", json=booking())
    assert r.status_code == 200
    bid = r.json()["id"]
    page = client.get(f"/book/done/{bid}").text
    assert "Rita Khoury" in page and f"/book/send/{bid}" in page
    wa = client.get(f"/book/send/{bid}", follow_redirects=False)
    assert wa.status_code == 303 and "71%20000%20000" in wa.headers["location"] and "wa.me" in wa.headers["location"]
    assert client.post("/api/bookings", json=booking()).status_code == 409
    slots = client.get("/api/slots", params={"service": "megabase", "staff": "dodo", "date": next_monday()}).json()["slots"]
    assert "09:40" not in slots
    assert client.post("/api/bookings", json=booking(service="megabase-jana", staff="jana")).status_code == 200


def test_polygel_blocks_dodo(client):
    login(client)
    assert client.post("/api/bookings", json=booking(service="polygel", time="07:30")).status_code == 200
    assert client.post("/api/bookings", json=booking(time="08:00")).status_code == 409



def test_admin_requires_staff(make_client):
    anon = make_client()
    r = anon.get("/admin", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/auth/login")
    client = login(make_client(), uid="c", email="client@x.com")
    assert client.get("/admin").status_code == 403
    staff = login(make_client(), uid="m", email="staff@example.com", name="Dodo")
    assert staff.get("/admin").status_code == 200


def test_admin_cancel_frees_slot(make_client):
    c = login(make_client(), uid="c", email="client@x.com")
    bid = c.post("/api/bookings", json=booking()).json()["id"]
    staff = login(make_client(), uid="m", email="staff@example.com", name="Dodo")
    staff.post(f"/admin/bookings/{bid}/status", data={"status": "cancelled"})
    assert c.post("/api/bookings", json=booking()).status_code == 200


def test_admin_status_needs_staff(make_client):
    c = login(make_client(), uid="c", email="client@x.com")
    bid = c.post("/api/bookings", json=booking()).json()["id"]
    assert c.post(f"/admin/bookings/{bid}/status", data={"status": "cancelled"}).status_code == 403



def test_security_headers(client):
    r = client.get("/")
    csp = r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp and "nonce-" in csp
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    nonce = csp.split("'nonce-")[1].split("'")[0]
    assert f'nonce="{nonce}"' in r.text


def test_cross_site_post_blocked(client):
    login(client)
    r = client.post("/auth/logout", headers={"origin": "https://evil.example"}, follow_redirects=False)
    assert r.status_code == 403
    r = client.post("/auth/logout", headers={"origin": "http://testserver"}, follow_redirects=False)
    assert r.status_code == 303


