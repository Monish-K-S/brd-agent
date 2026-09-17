from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, enable_hsts: bool = False):
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)

            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.setdefault("headers", []))

                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"referrer-policy"] = (
                    b"strict-origin-when-cross-origin"
                )

                if self.enable_hsts:
                    headers[b"strict-transport-security"] = (
                        b"max-age=31536000; includeSubDomains"
                    )

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_with_headers)
