from dataclasses import replace

from src.models.supplier import operator_host
from tests.fakes.domain import make_supplier

OPERATORS = frozenset({"productcenter.ru", "pulscen.ru"})


def test_operator_site_and_mail_are_not_the_supplier_contacts() -> None:
    supplier = replace(
        make_supplier("alpha"),
        website="https://www.productcenter.ru/producers/1",
        contacts={"email": "info@spb.pulscen.ru", "phone": "+7 812 000-00-00"},
    )
    clean = supplier.without_operator_contacts(OPERATORS)
    assert clean.website == ""
    assert dict(clean.contacts) == {"phone": "+7 812 000-00-00"}


def test_own_contacts_are_kept_untouched() -> None:
    supplier = make_supplier("alpha")
    assert supplier.without_operator_contacts(OPERATORS) is supplier
    assert supplier.without_operator_contacts(frozenset()) is supplier


def test_operator_host_is_normalized() -> None:
    assert operator_host("https://www.ProductCenter.ru/catalog") == "productcenter.ru"
    assert operator_host("file:///data/task/suppliers.csv") == ""
    assert operator_host("http://[bad") == ""
