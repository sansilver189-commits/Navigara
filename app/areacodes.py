"""US area codes by state, and a rough centre point per state.

Used to pick which of your numbers calls a lead: same area code first, then the number
whose state is nearest. Approximate on purpose - it only chooses a caller ID.
"""
import math

BY_STATE = {
    "AL": "205 251 256 334 659 938", "AK": "907", "AZ": "480 520 602 623 928",
    "AR": "479 501 870", "CA": "209 213 279 310 323 341 350 369 408 415 424 442 510 530 559 562 619 626 628 650 657 661 669 707 714 747 760 805 818 820 831 840 858 909 916 925 949 951",
    "CO": "303 719 720 970 983", "CT": "203 475 860 959", "DE": "302", "DC": "202 771",
    "FL": "239 305 321 324 352 386 407 448 561 645 656 689 727 728 754 772 786 813 850 863 904 941 954",
    "GA": "229 404 470 478 678 706 762 770 912 943", "HI": "808", "ID": "208 986",
    "IL": "217 224 309 312 331 447 464 618 630 708 730 773 779 815 847 861 872",
    "IN": "219 260 317 463 574 765 812 930", "IA": "319 515 563 641 712",
    "KS": "316 620 785 913", "KY": "270 364 502 606 859", "LA": "225 318 337 504 985",
    "ME": "207", "MD": "227 240 301 410 443 667", "MA": "339 351 413 508 617 774 781 857 978",
    "MI": "231 248 269 313 517 586 616 679 734 810 906 947 989", "MN": "218 320 507 612 651 763 952",
    "MS": "228 601 662 769", "MO": "235 314 417 557 573 636 660 816 975", "MT": "406",
    "NE": "308 402 531", "NV": "702 725 775", "NH": "603", "NJ": "201 551 609 640 732 848 856 862 908 973",
    "NM": "505 575", "NY": "212 315 332 347 363 516 518 585 607 624 631 646 680 716 718 838 845 914 917 929 934",
    "NC": "252 336 472 704 743 828 910 919 980 984", "ND": "701",
    "OH": "216 220 234 283 326 330 380 419 436 440 513 567 614 740 937",
    "OK": "405 539 572 580 918", "OR": "458 503 541 971", "PA": "215 223 267 272 412 445 484 570 582 610 717 724 814 835 878",
    "RI": "401", "SC": "803 821 839 843 854 864", "SD": "605", "TN": "423 615 629 731 865 901 931",
    "TX": "210 214 254 281 325 346 361 409 430 432 469 512 682 713 726 737 806 817 830 832 903 915 936 940 945 956 972 979",
    "UT": "385 435 801", "VT": "802", "VA": "276 434 540 571 686 703 757 804 826 948",
    "WA": "206 253 360 425 509 564", "WV": "304 681", "WI": "262 274 414 534 608 715 920", "WY": "307",
}

# Rough centre (latitude, longitude) of where people live in each state.
CENTER = {
    "AL": (32.8, -86.8), "AK": (61.2, -149.9), "AZ": (33.4, -111.9), "AR": (34.8, -92.3),
    "CA": (36.0, -119.8), "CO": (39.7, -105.0), "CT": (41.6, -72.7), "DE": (39.2, -75.5),
    "DC": (38.9, -77.0), "FL": (27.8, -81.6), "GA": (33.7, -84.4), "HI": (21.3, -157.8),
    "ID": (43.6, -116.2), "IL": (41.5, -88.4), "IN": (39.8, -86.2), "IA": (41.7, -93.0),
    "KS": (38.5, -97.0), "KY": (37.8, -85.3), "LA": (30.6, -91.4), "ME": (44.3, -69.8),
    "MD": (39.1, -76.8), "MA": (42.3, -71.4), "MI": (42.7, -84.5), "MN": (45.0, -93.3),
    "MS": (32.3, -89.9), "MO": (38.6, -92.2), "MT": (46.9, -110.4), "NE": (41.1, -96.8),
    "NV": (36.2, -115.1), "NH": (43.2, -71.5), "NJ": (40.3, -74.5), "NM": (35.1, -106.6),
    "NY": (41.5, -74.2), "NC": (35.6, -79.4), "ND": (47.0, -98.0), "OH": (40.3, -82.8),
    "OK": (35.6, -97.0), "OR": (44.9, -122.9), "PA": (40.6, -76.9), "RI": (41.8, -71.4),
    "SC": (34.0, -81.0), "SD": (44.0, -99.0), "TN": (35.9, -86.4), "TX": (31.0, -97.5),
    "UT": (40.7, -111.9), "VT": (44.3, -72.8), "VA": (37.9, -77.6), "WA": (47.4, -122.0),
    "WV": (38.6, -80.6), "WI": (43.5, -89.0), "WY": (42.9, -107.5),
}

# Bay Area / Southern California etc. get their own point so 415 isn't treated as "middle of CA".
AREA_CENTER = {
    "415": (37.77, -122.42), "628": (37.77, -122.42), "650": (37.5, -122.25), "408": (37.34, -121.89),
    "669": (37.34, -121.89), "510": (37.8, -122.27), "341": (37.8, -122.27), "925": (37.9, -122.0),
    "707": (38.4, -122.7), "213": (34.05, -118.25), "310": (34.0, -118.4), "323": (34.05, -118.25),
    "818": (34.2, -118.5), "626": (34.1, -118.1), "562": (33.8, -118.2), "714": (33.8, -117.9),
    "949": (33.6, -117.8), "619": (32.7, -117.16), "858": (32.9, -117.2), "916": (38.58, -121.5),
}

STATE_OF = {code: st for st, codes in BY_STATE.items() for code in codes.split()}


def location(area_code: str | None):
    if not area_code:
        return None
    if area_code in AREA_CENTER:
        return AREA_CENTER[area_code]
    st = STATE_OF.get(area_code)
    return CENTER.get(st) if st else None


def distance(a, b) -> float:
    """Rough distance in km between two (lat, lon) points."""
    if not a or not b:
        return float("inf")
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


# Main time zone per state (states split across zones use the zone most people live in).
STATE_TZ = {
    "AL": "America/Chicago", "AK": "America/Anchorage", "AZ": "America/Phoenix", "AR": "America/Chicago",
    "CA": "America/Los_Angeles", "CO": "America/Denver", "CT": "America/New_York", "DE": "America/New_York",
    "DC": "America/New_York", "FL": "America/New_York", "GA": "America/New_York", "HI": "Pacific/Honolulu",
    "ID": "America/Boise", "IL": "America/Chicago", "IN": "America/Indiana/Indianapolis", "IA": "America/Chicago",
    "KS": "America/Chicago", "KY": "America/New_York", "LA": "America/Chicago", "ME": "America/New_York",
    "MD": "America/New_York", "MA": "America/New_York", "MI": "America/Detroit", "MN": "America/Chicago",
    "MS": "America/Chicago", "MO": "America/Chicago", "MT": "America/Denver", "NE": "America/Chicago",
    "NV": "America/Los_Angeles", "NH": "America/New_York", "NJ": "America/New_York", "NM": "America/Denver",
    "NY": "America/New_York", "NC": "America/New_York", "ND": "America/Chicago", "OH": "America/New_York",
    "OK": "America/Chicago", "OR": "America/Los_Angeles", "PA": "America/New_York", "RI": "America/New_York",
    "SC": "America/New_York", "SD": "America/Chicago", "TN": "America/Chicago", "TX": "America/Chicago",
    "UT": "America/Denver", "VT": "America/New_York", "VA": "America/New_York", "WA": "America/Los_Angeles",
    "WV": "America/New_York", "WI": "America/Chicago", "WY": "America/Denver",
}
STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "washington dc": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


def lead_timezone(state: str | None, area: str | None) -> str | None:
    """Best guess of the lead's time zone: their state if known, else their phone's area code."""
    st = (state or "").strip()
    st = STATE_NAMES.get(st.lower(), st.upper())
    if st not in STATE_TZ:
        st = STATE_OF.get(area or "")
    return STATE_TZ.get(st)
