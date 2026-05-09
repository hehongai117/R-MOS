"""RobotAsset ORM model — tracks files belonging to a robot model."""
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AssetType(str, enum.Enum):
    MODEL_GLB = "model_glb"
    MANIFEST = "manifest"
    THUMBNAIL = "thumbnail"
    UPLOAD_ORIGINAL = "upload_original"


class RobotAsset(Base, TimestampMixin):
    """机器人资产文件记录。"""
    __tablename__ = "robot_assets"

    id = Column(Integer, primary_key=True, index=True)
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    asset_type = Column(Enum(AssetType), nullable=False, comment="资产类型")
    file_path = Column(String(500), nullable=False, comment="相对存储路径")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    asset_metadata = Column(JSON, nullable=True, comment="元数据（顶点数、节点数等）")

    robot_model = relationship("RobotModel", back_populates="assets")

    def __repr__(self):
        return f"<RobotAsset(id={self.id}, type={self.asset_type}, path={self.file_path})>"
