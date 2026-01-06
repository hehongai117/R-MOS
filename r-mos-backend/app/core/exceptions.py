"""
自定义异常类（基础设施）
"""
from datetime import datetime
from typing import Optional, Dict, Any


class BusinessRuleViolation(Exception):
    """业务规则违反异常（409 Conflict）
    
    用于：
    - 步骤顺序错误
    - Task状态不符合要求
    - SOP被引用无法删除
    """
    
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class AdapterConnectionError(Exception):
    """Adapter连接错误（503 Service Unavailable）
    
    用于：
    - Adapter未连接
    - 硬件通信失败
    - ROS2节点不可用
    """
    
    def __init__(self, message: str):
        self.message = message
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class ResourceNotFoundError(Exception):
    """资源不存在异常（404 Not Found）
    
    用于：
    - Task不存在
    - SOP不存在
    - Snapshot不存在
    """
    
    def __init__(self, resource_type: str, resource_id: Any):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = f"{resource_type}不存在: {resource_id}"
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)
