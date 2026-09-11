import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def city_regions():
    # Same normalized province/city names as the admin and mobile address pickers.
    return json.loads((Path(__file__).parents[1] / 'data' / 'city_regions.json').read_text(encoding='utf-8'))
