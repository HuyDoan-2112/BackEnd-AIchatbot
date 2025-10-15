"""
Logging middleware for FastAPI application.
Logs all incoming requests and outgoing responses with detailed information.
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logger import get_logger

logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details"""

        # Generate request ID
        request_id = request.headers.get("X-Request-ID", f"{int(time.time() * 1000)}")

        # Start timer
        start_time = time.time()

        # Log incoming request
        await self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            self._log_response(request, response, duration, request_id)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "extra_data": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration": duration,
                        "error": str(e)
                    }
                },
                exc_info=True
            )
            raise

    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request details"""

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode("utf-8")
                    # Try to parse as JSON for better logging
                    try:
                        body = json.loads(body)
                        # Mask sensitive fields
                        if isinstance(body, dict):
                            body = self._mask_sensitive_data(body)
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.warning(f"Could not read request body: {e}")

        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                    "client_host": request.client.host if request.client else None,
                    "body": body
                }
            }
        )

    def _log_response(self, request: Request, response: Response, duration: float, request_id: str):
        """Log outgoing response details"""

        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        log_message = f"← {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"

        log_data = {
            "extra_data": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "response_headers": dict(response.headers)
            }
        }

        # Log at appropriate level
        getattr(logger, log_level)(log_message, extra=log_data)

    def _mask_sensitive_data(self, data: dict) -> dict:
        """Mask sensitive fields in request/response data"""
        sensitive_fields = [
            "password",
            "confirm_password",
            "token",
            "access_token",
            "refresh_token",
            "secret",
            "api_key",
            "authorization"
        ]

        masked_data = data.copy()
        for field in sensitive_fields:
            if field in masked_data:
                masked_data[field] = "***MASKED***"

        return masked_data
