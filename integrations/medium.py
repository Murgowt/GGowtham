"""Map transactions to a payment-medium identity for UI badges."""


def resolve_medium(
    *,
    source: str,
    institution_name: str | None = None,
    account_name: str | None = None,
    subtype: str | None = None,
) -> dict[str, str]:
    haystack = " ".join(filter(None, [institution_name, account_name])).lower()

    if source == "splitwise":
        return {
            "medium_key": "splitwise",
            "medium_label": "Splitwise",
            "medium_short": "SW",
        }

    is_card = source == "card" or subtype in {
        "credit card",
        "credit",
        "paypal",
        "line of credit",
    }

    if "chase" in haystack:
        if is_card:
            label = account_name or "Chase Credit Card"
            return {
                "medium_key": "chase_card",
                "medium_label": label if "chase" in label.lower() else f"Chase · {label}",
                "medium_short": "CH",
            }
        return {
            "medium_key": "chase_bank",
            "medium_label": account_name or "Chase Bank",
            "medium_short": "CH",
        }

    if "discover" in haystack:
        return {
            "medium_key": "discover",
            "medium_label": account_name or "Discover",
            "medium_short": "DISC",
        }

    if "amex" in haystack or "american express" in haystack:
        return {
            "medium_key": "amex",
            "medium_label": account_name or "American Express",
            "medium_short": "AMEX",
        }

    if "capital one" in haystack or "capitalone" in haystack:
        return {
            "medium_key": "capital_one",
            "medium_label": account_name or "Capital One",
            "medium_short": "C1",
        }

    if "citi" in haystack or "citibank" in haystack:
        return {
            "medium_key": "citi",
            "medium_label": account_name or "Citi",
            "medium_short": "CITI",
        }

    if "wells fargo" in haystack:
        return {
            "medium_key": "wells_fargo",
            "medium_label": account_name or "Wells Fargo",
            "medium_short": "WF",
        }

    if "bank of america" in haystack or "bofa" in haystack:
        return {
            "medium_key": "bofa",
            "medium_label": account_name or "Bank of America",
            "medium_short": "BoA",
        }

    if is_card:
        return {
            "medium_key": "card_generic",
            "medium_label": account_name or "Credit Card",
            "medium_short": "CARD",
        }

    return {
        "medium_key": "bank_generic",
        "medium_label": account_name or institution_name or "Bank",
        "medium_short": "BANK",
    }


LOGO_SLUGS = {
    "capital_one": "capitalone",
    "wells_fargo": "wellsfargo",
    "bofa": "bankofamerica",
}


LOGO_PATHS = {
    "chase_bank": "/static/logos/chase.svg",
    "chase_card": "/static/logos/chase_card.png",
    "discover": "/static/logos/discover.svg",
    "amex": "/static/logos/amex.png",
    "splitwise": "/static/logos/splitwise.png",
    "capital_one": "/static/logos/capitalone.svg",
    "citi": "/static/logos/citi.svg",
    "wells_fargo": "/static/logos/wellsfargo.svg",
    "bofa": "/static/logos/bankofamerica.svg",
    "bank_generic": "/static/logos/bank_generic.svg",
    "card_generic": "/static/logos/card_generic.svg",
}


def static_logo_path(medium_key: str) -> str:
    if medium_key in LOGO_PATHS:
        return LOGO_PATHS[medium_key]
    slug = LOGO_SLUGS.get(medium_key, medium_key)
    return f"/static/logos/{slug}.svg"
