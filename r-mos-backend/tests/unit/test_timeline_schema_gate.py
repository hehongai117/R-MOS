"""Gate-3 I-001：Timeline 基础表契约门禁测试。"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.models import Base
import app.models as app_models  # noqa: F401  # 确保模型全部注册


def test_i001_timeline_tables_and_indexes_exist_in_metadata() -> None:
    """I-001 最小契约：三张表 + 关键索引 + 关键外键必须存在。"""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())
    assert {"multimodal_timelines", "timeline_segments", "alignment_map"}.issubset(table_names)

    timeline_columns = {column["name"] for column in inspector.get_columns("multimodal_timelines")}
    assert {"id", "scope_type", "scope_id", "created_at"}.issubset(timeline_columns)

    segment_columns = {column["name"] for column in inspector.get_columns("timeline_segments")}
    assert {"id", "timeline_id", "segment_type", "start_ts_ms", "end_ts_ms", "created_at"}.issubset(
        segment_columns
    )

    alignment_columns = {column["name"] for column in inspector.get_columns("alignment_map")}
    assert {"id", "timeline_id", "anchor_key", "segment_id", "created_at"}.issubset(alignment_columns)

    timeline_indexes = {index["name"] for index in inspector.get_indexes("multimodal_timelines")}
    assert "ix_timeline_scope" in timeline_indexes

    segment_indexes = {index["name"] for index in inspector.get_indexes("timeline_segments")}
    assert "ix_segments_timeline_start" in segment_indexes

    alignment_indexes = {index["name"] for index in inspector.get_indexes("alignment_map")}
    assert "ix_alignment_anchor" in alignment_indexes

    segment_fk_tables = {fk["referred_table"] for fk in inspector.get_foreign_keys("timeline_segments")}
    assert "multimodal_timelines" in segment_fk_tables

    alignment_fk_tables = {fk["referred_table"] for fk in inspector.get_foreign_keys("alignment_map")}
    assert {"multimodal_timelines", "timeline_segments"}.issubset(alignment_fk_tables)
