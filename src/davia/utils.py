import logging


class EndpointFilter(logging.Filter):
    def __init__(self, excluded_paths):
        super().__init__()
        self.excluded_paths = excluded_paths

    def filter(self, record):
        return not any(path in record.getMessage() for path in self.excluded_paths)


def setup_logging():
    """Configure logging filters for the application."""
    uvicorn_logger = logging.getLogger("uvicorn.access")
    endpoint_filter = EndpointFilter(["/openapi.json", "/davia/graph-schemas"])
    uvicorn_logger.addFilter(endpoint_filter)
