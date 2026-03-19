from dotenv import load_dotenv

load_dotenv(".env", override=True)

from src.config import config as config  # noqa: E402

__version__ = "0.0.1"


def get_version():
    """Return version."""
    return __version__
