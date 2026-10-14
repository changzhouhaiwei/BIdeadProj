from decimal import Decimal

from app.alcohol import pure_alcohol_g, pure_alcohol_ml


def test_formula_examples():
    # 500 ml × 4% × 0.789 = 15.78 g
    assert pure_alcohol_ml(Decimal(500), Decimal(4)) == Decimal("20.00")
    assert pure_alcohol_g(Decimal(500), Decimal(4)) == Decimal("15.78")
    assert pure_alcohol_g(Decimal(150), Decimal(12)) == Decimal("14.20")
    assert pure_alcohol_g(Decimal(50), Decimal(42)) == Decimal("16.57")
    assert pure_alcohol_g(Decimal(30), Decimal(53)) == Decimal("12.55")
