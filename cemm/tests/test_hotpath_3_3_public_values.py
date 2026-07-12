from cemm.response.realization.public_values import public_value


def test_internal_identifiers_and_query_placeholders_are_not_public():
    assert public_value("uol_df9786baaf86521d") == ""
    assert public_value("topic", features={"source": "role_placeholder"}) == ""
    assert public_value("concept:president") == ""
    assert public_value("Chibueze Opata") == "Chibueze Opata"
