from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

# 乙醇在约 20℃ 的密度。纯酒精克数 = 毫升 × 酒精度 × 0.789。
DENSITY = Decimal("0.789")

FORMULA = {
    "pure_alcohol_ml": "volume_ml * abv_percent / 100",
    "pure_alcohol_g": "pure_alcohol_ml * 0.789",
    "density_g_per_ml": 0.789,
    "timezone": "Asia/Shanghai",
}


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pure_alcohol_ml(volume_ml: Decimal, abv_percent: Decimal) -> Decimal:
    return _q(volume_ml * abv_percent / Decimal(100))


def pure_alcohol_g(volume_ml: Decimal, abv_percent: Decimal) -> Decimal:
    return _q(volume_ml * abv_percent * DENSITY / Decimal(100))


def canonical_abv(value: object) -> str:
    if isinstance(value, str):
        number = Decimal(value.strip())
    elif isinstance(value, int) and not isinstance(value, bool):
        number = Decimal(value)
    elif isinstance(value, float):
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif isinstance(value, Decimal):
        number = value
    else:
        raise ValueError("酒精度要是数字")
    if number <= 0 or number > 100:
        raise ValueError("酒精度要大于 0，并且不超过 100")
    text = format(number.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def abv_decimal(text: str) -> Decimal:
    return Decimal(text)


def as_float(number: Decimal) -> float:
    return float(number)
