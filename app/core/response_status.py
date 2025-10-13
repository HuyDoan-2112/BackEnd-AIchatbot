# app/core/response_status.py
from fastapi.responses import JSONResponse
from http import HTTPStatus


class ResponseStatus:
    def __init__(self, message, status_code=HTTPStatus.OK, data=None, error_code=None, meta=None):
        self.success = status_code < 400
        self.message = message
        self.status_code = int(status_code)
        self.data = data
        self.meta = meta
        self.error_code = error_code

    def send(self):
        payload = {
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }

        if self.meta:
            payload["meta"] = self.meta

        if self.error_code and not self.success:
            payload["error_code"] = self.error_code

        return JSONResponse(content=payload, status_code=self.status_code)

class OK(ResponseStatus):
    def __init__(self, message="OK", data=None, meta=None):
        super().__init__(message, HTTPStatus.OK, data=data, meta=meta)

class Created(ResponseStatus):
    def __init__(self, message="Created", data=None, meta=None):
        super().__init__(message, HTTPStatus.CREATED, data=data, meta=meta)

class BadRequest(ResponseStatus):
    def __init__(self, message="Bad Request", error_code="4000"):
        super().__init__(message, HTTPStatus.BAD_REQUEST, error_code=error_code)

class Unauthorized(ResponseStatus):
    def __init__(self, message="Unauthorized", error_code="4001"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED, error_code=error_code)

class Forbidden(ResponseStatus):
    def __init__(self, message="Forbidden", error_code="4003"):
        super().__init__(message, HTTPStatus.FORBIDDEN, error_code=error_code)

class NotFound(ResponseStatus):
    def __init__(self, message="Not Found", error_code="4004"):
        super().__init__(message, HTTPStatus.NOT_FOUND, error_code=error_code)

class Conflict(ResponseStatus):
    def __init__(self, message="Conflict", error_code="4009"):
        super().__init__(message, HTTPStatus.CONFLICT, error_code=error_code)

class InternalError(ResponseStatus):
    def __init__(self, message="Internal Server Error", error_code="5000"):
        super().__init__(message, HTTPStatus.INTERNAL_SERVER_ERROR, error_code=error_code)

class UserNotFound(ResponseStatus):
    def __init__(self, message="User Not Found", error_code="4004"):
        super().__init__(message, HTTPStatus.NOT_FOUND, error_code=error_code)
        
class InvalidCredentials(ResponseStatus):
    def __init__(self, message="Invalid Credentials", error_code="4001"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED, error_code=error_code)
        
class TokenExpired(ResponseStatus):
    def __init__(self, message="Token Expired", error_code="4011"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED, error_code=error_code)
        
class TokenInvalid(ResponseStatus):
    def __init__(self, message="Token Invalid", error_code="4012"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED, error_code=error_code)
        
class InvalidToken(ResponseStatus):
    def __init__(self, message="Invalid Token", error_code="4012"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED, error_code=error_code)

class ServiceUnavailable(ResponseStatus):
    def __init__(self, message="Service Unavailable", error_code="5003"):
        super().__init__(message, HTTPStatus.SERVICE_UNAVAILABLE, error_code=error_code)

class DatabaseError(ResponseStatus):
    def __init__(self, message="Database Error", error_code="5001"):
        super().__init__(message, HTTPStatus.INTERNAL_SERVER_ERROR, error_code=error_code)

class ValidationError(ResponseStatus):
    def __init__(self, message="Validation Error", error_code="4002"):
        super().__init__(message, HTTPStatus.BAD_REQUEST, error_code=error_code)

class UnprocessableEntity(ResponseStatus):
    def __init__(self, message="Unprocessable Entity", error_code="4022"):
        super().__init__(message, HTTPStatus.UNPROCESSABLE_ENTITY, error_code=error_code)

class TooManyRequests(ResponseStatus):
    def __init__(self, message="Too Many Requests", error_code="4029"):
        super().__init__(message, HTTPStatus.TOO_MANY_REQUESTS, error_code=error_code)

class MethodNotAllowed(ResponseStatus):
    def __init__(self, message="Method Not Allowed", error_code="4005"):
        super().__init__(message, HTTPStatus.METHOD_NOT_ALLOWED, error_code=error_code)
        
class ChatNotFound(ResponseStatus):
    def __init__(self, message="Chat Not Found", error_code="4004"):
        super().__init__(message, HTTPStatus.NOT_FOUND, error_code=error_code)