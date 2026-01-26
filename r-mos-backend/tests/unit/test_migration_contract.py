import pytest

from app.core.migration_contract import check_migration_contract
from app.models import teaching  # noqa: F401


@pytest.mark.asyncio
async def test_migration_contract_has_required_schema(db_session):
    missing_tables, missing_columns = await check_migration_contract(db_session)
    assert missing_tables == []
    assert missing_columns == []
