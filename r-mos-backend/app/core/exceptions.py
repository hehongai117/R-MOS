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


class AccessDeniedError(Exception):
    """统一访问拒绝异常基类。"""

    status_code: int = 403
    error_code: str = "ACCESS_DENIED"

    def __init__(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: Any,
        reason: str,
        message: str,
    ):
        self.action = action
        self.resource_type = resource_type
        self.resource_id = str(resource_id) if resource_id is not None else None
        self.reason = reason
        self.message = message
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class ReadAccessDeniedError(AccessDeniedError):
    """对象级 READ 越权（对外 404）。"""

    status_code = 404
    error_code = "READ_ACCESS_DENIED"

    def __init__(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: Any,
        reason: str,
        message: str = "资源不存在",
    ):
        super().__init__(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason=reason,
            message=message,
        )


class WriteAccessDeniedError(AccessDeniedError):
    """对象级 WRITE 越权（对外 403）。"""

    status_code = 403
    error_code = "WRITE_ACCESS_DENIED"

    def __init__(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: Any,
        reason: str,
        message: str = "权限不足",
    ):
        super().__init__(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason=reason,
            message=message,
        )
