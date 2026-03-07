from app.core.resource_parser import (
    ResourceAccessLevel,
    ResourceParser,
    ResourceRef,
    ResourceType,
)


def test_validate_resource_access_denies_other_user_personal_resource() -> None:
    parser = ResourceParser()
    ref = ResourceRef(
        resource_type=ResourceType.KNOWLEDGE,
        resource_id="kb-1234ABCD",
        access_level=ResourceAccessLevel.READ,
        scope="personal",
        owner_id="owner-1",
    )

    ok, errors = parser.validate_resource_access(user_id="owner-2", resource_refs=[ref])

    assert ok is False
    assert errors and "cannot access personal resource" in errors[0]


def test_validate_resource_access_uses_resource_exists_lookup() -> None:
    parser = ResourceParser()
    parser.set_resource_exists_lookup(lambda _ref: False)
    ref = ResourceRef(
        resource_type=ResourceType.KNOWLEDGE,
        resource_id="kb-1234ABCD",
        access_level=ResourceAccessLevel.READ,
    )

    ok, errors = parser.validate_resource_access(user_id="user-1", resource_refs=[ref])

    assert ok is False
    assert errors and "Resource not found or unavailable" in errors[0]


def test_validate_resource_access_falls_back_to_metadata_exists_flag() -> None:
    parser = ResourceParser()
    ref = ResourceRef(
        resource_type=ResourceType.KNOWLEDGE,
        resource_id="kb-1234ABCD",
        access_level=ResourceAccessLevel.READ,
        metadata={"exists": False},
    )

    ok, errors = parser.validate_resource_access(user_id="user-1", resource_refs=[ref])

    assert ok is False
    assert errors and "Resource not found or unavailable" in errors[0]
