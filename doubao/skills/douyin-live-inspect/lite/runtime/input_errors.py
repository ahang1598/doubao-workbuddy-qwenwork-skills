"""Safe, fixed startup diagnostics shared by command receipts and telemetry."""


class InputValidationError(ValueError):
    code = 'INVALID_INPUT'

    def __init__(self, detail, message):
        super().__init__(message)
        self.error_detail = detail


class ConfigurationError(RuntimeError):
    code = 'RUNTIME_UNAVAILABLE'

    def __init__(self, detail, message):
        super().__init__(message)
        self.error_detail = detail
