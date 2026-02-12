"""Constants for the Turnov Třídí integration."""

DOMAIN = "turnov_tridi"

CONF_STREET = "street"

BASE_URL = "http://turnovtridi.cz/views/ajax"

# Waste type CSS class -> key mapping
WASTE_TYPES = {
    "sko": {
        "key": "mixed_waste",
        "name_cs": "Směsný komunální odpad",
        "name_en": "Mixed municipal waste",
        "icon": "mdi:trash-can",
    },
    "plast": {
        "key": "plastic",
        "name_cs": "Plasty",
        "name_en": "Plastic",
        "icon": "mdi:recycle",
    },
    "papir": {
        "key": "paper",
        "name_cs": "Papír",
        "name_en": "Paper",
        "icon": "mdi:newspaper-variant-outline",
    },
    "bio": {
        "key": "bio_waste",
        "name_cs": "Bio odpad",
        "name_en": "Bio waste",
        "icon": "mdi:leaf",
    },
}

# Default update interval in hours
DEFAULT_UPDATE_INTERVAL_HOURS = 6
