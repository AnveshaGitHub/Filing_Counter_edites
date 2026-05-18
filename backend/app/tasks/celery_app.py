from __future__ import annotations


try:
    from celery import Celery  # type: ignore

    celery_app = Celery("filing_counter")
except Exception:
    class _FallbackCeleryApp:
        def task(self, name: str | None = None):
            def decorator(func):
                func.delay = func
                return func

            return decorator

    celery_app = _FallbackCeleryApp()
