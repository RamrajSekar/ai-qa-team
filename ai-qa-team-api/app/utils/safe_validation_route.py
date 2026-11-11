"""Keep submitted credential values out of validation error responses."""
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse


class SafeValidationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                return JSONResponse(status_code=422, content={"detail": [
                    {"loc": error["loc"], "type": error["type"], "msg": "Invalid request field."}
                    for error in exc.errors()
                ]})
        return safe_handler
