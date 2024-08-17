class GradleError:
    """
    Standardized error response for any Gradle command failures.
    """
    def __init__(self, error_message: str, error_code: int) -> None:
        self.error_message: str = error_message  # The error message as a string
        self.error_code: int = error_code  # The error code from the subprocess call
