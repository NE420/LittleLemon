def roles(request):
    """
    Makes login state and role flags available in every template, so views
    don't have to pass is_manager etc. one by one.

    The flags are written to the session once, at login (see LoginView).
    They only drive what the UI shows; the views and the API enforce access.
    """
    session = getattr(request, "session", None)
    if session is None:
        return {}

    user_roles = session.get("roles", {})
    logged_in = bool(session.get("auth_token"))
    is_admin = bool(user_roles.get("is_admin"))
    is_manager = bool(user_roles.get("is_manager"))
    is_delivery_crew = bool(user_roles.get("is_delivery_crew"))

    return {
        "logged_in": logged_in,
        "current_username": session.get("username", ""),
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_delivery_crew": is_delivery_crew,
        # Logged in, but neither staff nor crew: the person who shops.
        "is_customer": logged_in and not (is_manager or is_delivery_crew),
    }
