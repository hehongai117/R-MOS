"""Gradual fault scenario definitions for demo mode."""
import time
from dataclasses import dataclass, field


@dataclass
class GradualFault:
    """A fault that ramps up over a duration rather than appearing instantly."""
    fault_type: str
    joint_id: str
    start_time: float = field(default_factory=time.time)
    ramp_duration: float = 30.0  # seconds to reach full effect
    target_temp_increase: float = 30.0  # degrees C
    target_torque_noise: float = 2.0  # Nm noise amplitude

    def progress(self) -> float:
        """Return 0.0-1.0 indicating how far through the ramp we are."""
        elapsed = time.time() - self.start_time
        return min(elapsed / self.ramp_duration, 1.0)

    def current_temp_increase(self) -> float:
        return self.target_temp_increase * self.progress()

    def current_torque_noise(self) -> float:
        return self.target_torque_noise * self.progress()

    @property
    def is_complete(self) -> bool:
        return self.progress() >= 1.0


DEMO_SCENARIOS = {
    'knee_overheat': {
        'fault_type': 'knee_overheat',
        'joint_id': 'knee_left',
        'ramp_duration': 30.0,
        'target_temp_increase': 30.0,
        'target_torque_noise': 2.0,
    },
}
