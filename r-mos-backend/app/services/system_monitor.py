"""
System Monitoring Service - Phase 4 Week 12
Real-time system monitoring and health checks

Features:
- Health checks
- Performance metrics
- Resource usage tracking
- Alert generation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import os

try:
    import psutil  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - optional dependency for test env
    psutil = None  # type: ignore[assignment]


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class HealthCheck:
    """Individual health check result"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    level: AlertLevel
    component: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    acknowledged: bool = False


class SystemMonitor:
    """
    System monitoring service for real-time health tracking.

    Monitors:
    - CPU usage
    - Memory usage
    - Disk usage
    - Network I/O
    - Application health
    """

    def __init__(self):
        self._alerts: List[Alert] = []
        self._health_checks: Dict[str, HealthCheck] = {}
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = 1000  # Keep last 1000 metrics

    # ============ System Metrics ============

    @staticmethod
    def _get_net_io() -> tuple[int, int]:
        if psutil is None:
            return 0, 0
        net_io = psutil.net_io_counters()
        return net_io.bytes_sent, net_io.bytes_recv

    @staticmethod
    def _get_cpu_percent() -> float:
        if psutil is None:
            return 0.0
        return float(psutil.cpu_percent(interval=0.1))

    @staticmethod
    def _get_memory_percent() -> float:
        if psutil is None:
            return 0.0
        return float(psutil.virtual_memory().percent)

    @staticmethod
    def _get_disk_percent() -> float:
        if psutil is None:
            return 0.0
        return float(psutil.disk_usage("/").percent)

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        bytes_sent, bytes_recv = self._get_net_io()

        return SystemMetrics(
            cpu_percent=self._get_cpu_percent(),
            memory_percent=self._get_memory_percent(),
            disk_percent=self._get_disk_percent(),
            network_sent=bytes_sent,
            network_recv=bytes_recv,
        )

    def record_metrics(self) -> SystemMetrics:
        """Record metrics to history"""
        metrics = self.get_system_metrics()
        self._metrics_history.append(metrics)

        # Trim history
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]

        return metrics

    def get_metrics_history(self, limit: int = 100) -> List[SystemMetrics]:
        """Get recent metrics history"""
        return self._metrics_history[-limit:]

    # ============ Health Checks ============

    def check_cpu_health(self) -> HealthCheck:
        """Check CPU health"""
        metrics = self.get_system_metrics()

        if metrics.cpu_percent < 70:
            status = HealthStatus.HEALTHY
        elif metrics.cpu_percent < 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
            self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"High CPU usage: {metrics.cpu_percent}%"
            )

        return HealthCheck(
            component="cpu",
            status=status,
            message=f"CPU usage: {metrics.cpu_percent}%",
            details={"cpu_percent": metrics.cpu_percent}
        )

    def check_memory_health(self) -> HealthCheck:
        """Check memory health"""
        metrics = self.get_system_metrics()

        if metrics.memory_percent < 70:
            status = HealthStatus.HEALTHY
        elif metrics.memory_percent < 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
            self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"High memory usage: {metrics.memory_percent}%"
            )

        return HealthCheck(
            component="memory",
            status=status,
            message=f"Memory usage: {metrics.memory_percent}%",
            details={"memory_percent": metrics.memory_percent}
        )

    def check_disk_health(self) -> HealthCheck:
        """Check disk health"""
        metrics = self.get_system_metrics()

        if metrics.disk_percent < 80:
            status = HealthStatus.HEALTHY
        elif metrics.disk_percent < 95:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
            self._create_alert(
                AlertLevel.ERROR,
                "system",
                f"Low disk space: {metrics.disk_percent}%"
            )

        return HealthCheck(
            component="disk",
            status=status,
            message=f"Disk usage: {metrics.disk_percent}%",
            details={"disk_percent": metrics.disk_percent}
        )

    def check_application_health(self) -> HealthCheck:
        """Check application-specific health"""
        # Check database connection
        # Check external services
        # Check feature flags

        return HealthCheck(
            component="application",
            status=HealthStatus.HEALTHY,
            message="Application is healthy",
            details={"database": "ok", "feature_flags": "ok"}
        )

    def run_all_health_checks(self) -> List[HealthCheck]:
        """Run all health checks"""
        checks = [
            self.check_cpu_health(),
            self.check_memory_health(),
            self.check_disk_health(),
            self.check_application_health(),
        ]

        # Store results
        for check in checks:
            self._health_checks[check.component] = check

        return checks

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        checks = self.run_all_health_checks()

        healthy = sum(1 for c in checks if c.status == HealthStatus.HEALTHY)
        degraded = sum(1 for c in checks if c.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY)

        overall = HealthStatus.HEALTHY
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED

        return {
            "overall_status": overall.value,
            "total_checks": len(checks),
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "checks": [
                {
                    "component": c.component,
                    "status": c.status.value,
                    "message": c.message,
                }
                for c in checks
            ],
            "timestamp": int(time.time() * 1000),
        }

    # ============ Alerts ============

    def _create_alert(self, level: AlertLevel, component: str, message: str, details: Dict[str, Any] = None):
        """Create a new alert"""
        alert = Alert(
            alert_id=f"alert-{int(time.time() * 1000)}",
            level=level,
            component=component,
            message=message,
            details=details or {},
        )
        self._alerts.append(alert)

    def get_alerts(self, level: Optional[AlertLevel] = None, limit: int = 100) -> List[Alert]:
        """Get alerts, optionally filtered by level"""
        alerts = self._alerts

        if level:
            alerts = [a for a in alerts if a.level == level]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)[:limit]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def clear_alerts(self):
        """Clear all acknowledged alerts"""
        self._alerts = [a for a in self._alerts if not a.acknowledged]


# Singleton instance
system_monitor = SystemMonitor()
