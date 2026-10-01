class ClientError(Exception):
    pass


class MlServiceUnavailableError(ClientError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"ml service is unavailable: {reason}")


class MlServiceError(ClientError):
    def __init__(self, status: int) -> None:
        super().__init__(f"ml service answered with status {status}")
        self.status = status


class MlProtocolError(ClientError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"ml service broke the protocol: {reason}")


class EmbeddingClientError(ClientError):
    pass
