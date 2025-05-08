# Tránh circular imports
__all__ = ["ServiceFactory"]

# Sẽ import ServiceFactory khi được gọi
def get_service_factory():
    from .factory import ServiceFactory
    return ServiceFactory()