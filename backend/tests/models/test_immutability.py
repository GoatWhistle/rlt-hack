from dataclasses import replace
from typing import cast

import pytest

from src.models.catalog.normalization import Normalization
from tests.fakes.domain import make_offer, make_supplier


def test_supplier_is_hashable_and_its_contacts_are_read_only() -> None:
    supplier = make_supplier()
    assert hash(supplier) == hash(make_supplier())
    assert supplier == make_supplier()
    with pytest.raises(TypeError):
        cast(dict[str, str], supplier.contacts)["email"] = "spoof@example.org"


def test_contacts_are_copied_from_the_given_mapping() -> None:
    contacts = {"email": "sales@alpha.example.org"}
    supplier = replace(make_supplier(), contacts=contacts)
    contacts["email"] = "changed@example.org"
    assert supplier.contacts["email"] == "sales@alpha.example.org"


def test_offer_and_normalization_attributes_are_read_only() -> None:
    offer = replace(make_offer(), attributes={"color": "white"})
    assert hash(offer) == hash(replace(make_offer(), attributes={"color": "black"}))
    with pytest.raises(TypeError):
        cast(dict[str, str], offer.attributes)["color"] = "black"
    normalization = Normalization(attributes={"length_mm": "19"})
    with pytest.raises(TypeError):
        cast(dict[str, str], normalization.attributes)["length_mm"] = "20"
