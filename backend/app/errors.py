class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str = "validation"):
        self.status = status
        self.message = message
        self.code = code
