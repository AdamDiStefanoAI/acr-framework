# ACR Control Plane — Reference Implementation
# Apache 2.0 License
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("acr-control-plane")
except PackageNotFoundError:  # source checkout without install
    __version__ = "0.0.0+unknown"
