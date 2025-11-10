from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status
import jwt, logging

logger = logging.getLogger(__name__)

async def jwt_exception_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired token from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Token has expired. Please log in again."}
        )
    except jwt.InvalidTokenError:
        logger.warning(f"Invalid token from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid authentication token."}
        )
    except Exception as e:
        # Optional: catch-all for unexpected errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )
