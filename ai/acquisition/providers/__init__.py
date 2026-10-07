"""
ai/acquisition/providers package.
"""

from ai.acquisition.providers.base import StockSourceAdapter
from ai.acquisition.providers.pexels import PexelsAdapter
from ai.acquisition.providers.pixabay import PixabayAdapter
from ai.acquisition.providers.freesound import FreesoundAdapter
from ai.acquisition.providers.iconify import IconifyAdapter

__all__ = [
    "StockSourceAdapter",
    "PexelsAdapter",
    "PixabayAdapter",
    "FreesoundAdapter",
    "IconifyAdapter",
]
