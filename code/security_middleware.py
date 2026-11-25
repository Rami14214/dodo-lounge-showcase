"""Excerpt from app/main.py: the security middleware every request goes through."""

    @app.middleware("http")
    async def security(request: Request, call_next):
        # Block cross-site form/API posts (CSRF): a browser always sends Origin on POST.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != "null":
                allowed = {public_url} if public_url else set()
                allowed.add(f"{request.url.scheme}://{request.headers.get('host', '')}")
                if origin.rstrip("/") not in allowed:
                    return JSONResponse({"detail": "Cross-site request blocked."}, 403)
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        resp = await call_next(request)
        h = resp.headers
        h["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'")
        h["X-Frame-Options"] = "DENY"
        h["X-Content-Type-Options"] = "nosniff"
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        if https_only:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith(("/admin", "/me", "/account", "/auth", "/book/done", "/book/send", "/shop/done", "/api/")):
            h["Cache-Control"] = "no-store"
        return resp

    app.add_middleware(SessionMiddleware, secret_key=env("DODO_SECRET") or secrets.token_hex(32),
                       same_site="lax", https_only=https_only, max_age=60 * 60 * 24 * 30,
                       session_cookie="dodo_session")
    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
