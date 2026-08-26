import reflex as rx

config = rx.Config(
    app_name="app",
    db_url="sqlite:///reflex.db",
    # default_color_mode is the REAL OS-inheritance guard (the previously
    # removed rx.theme(...) mode-pin prop below was a no-op). 11-RESEARCH.md
    # verified against the installed reflex_components_radix/themes/base.py
    # source that Theme._render() strips that prop via .remove_props(...)
    # before it ever reaches the DOM. default_color_mode is the compiled
    # `defaultColorMode` JS constant the ThemeProvider falls back to when
    # localStorage["theme"] is absent; left unset it silently resolves to
    # "system". Per D-02 this value must never be "system" or "inherit".
    default_color_mode="light",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(accent_color="cyan", radius="small")
        ),
    ]
)