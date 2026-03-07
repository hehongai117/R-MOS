"""
P2-5: Locust Load Test Script
Locust 压测脚本

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Run with headless mode:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 30m --csv=results/load_test
"""

import random
import json
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Test configuration
API_BASE = "/api/v1"

# Global stats for reporting
stats = {
    "total_requests": 0,
    "failed_requests": 0,
    "p95_latency": 0,
}


class RMOSUser(HttpUser):
    """R-MOS Load Test User"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts"""
        # Login to get auth token (if needed)
        # self.client.post(f"{API_BASE}/auth/login", json={"email": "test@example.com", "password": "password"})
        pass

    @task(10)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get(
            f"{API_BASE}/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(5)
    def list_sops(self):
        """List SOPs"""
        with self.client.get(
            f"{API_BASE}/sops",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List SOPs failed: {response.status_code}")

    @task(3)
    def get_task(self):
        """Get task details"""
        # Use a random task ID for testing
        task_id = random.randint(1, 100)
        with self.client.get(
            f"{API_BASE}/tasks/{task_id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get task failed: {response.status_code}")

    @task(2)
    def create_task(self):
        """Create a new task"""
        payload = {
            "title": f"Load Test Task {random.randint(1000, 9999)}",
            "sop_id": random.randint(1, 10),
        }
        with self.client.post(
            f"{API_BASE}/tasks",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Create task failed: {response.status_code}")

    @task(1)
    def agent_execute(self):
        """Test agent execute endpoint"""
        payload = {
            "message": "测试消息",
            "context": {"task_id": random.randint(1, 10)},
        }
        with self.client.post(
            f"{API_BASE}/agent/execute",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Agent execute failed: {response.status_code}")


class APIPerformanceUser(HttpUser):
    """API Performance focused user"""

    wait_time = between(0.5, 1.5)

    @task(1)
    def critical_endpoint(self):
        """Test critical endpoints with higher priority"""
        # Test health
        self.client.get(f"{API_BASE}/health")

        # Test task list
        self.client.get(f"{API_BASE}/tasks")

        # Test SOP list
        self.client.get(f"{API_BASE}/sops")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print(f"Starting load test with {environment.runner.user_count if hasattr(environment.runner, 'user_count') else 'N/A'} users")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("Load test completed")

    # Print summary
    if hasattr(environment.stats, 'total'):
        stats = environment.stats.total
        print(f"\n{'='*50}")
        print("LOAD TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Requests: {stats.num_requests}")
        print(f"Failed Requests: {stats.num_failures}")
        print(f"Failure Rate: {(stats.num_failures / stats.num_requests * 100):.2f}%")
        print(f"Average Response Time: {stats.avg_response_time:.2f}ms")
        print(f"P95 Response Time: {stats.get_response_time_percentile(0.95):.2f}ms")
        print(f"P99 Response Time: {stats.get_response_time_percentile(0.99):.2f}ms")
        print(f"{'='*50}\n")

        # SLO Check
        p95 = stats.get_response_time_percentile(0.95)
        failure_rate = (stats.num_failures / stats.num_requests * 100) if stats.num_requests > 0 else 0

        print("SLO VERIFICATION:")
        print(f"  P95 Latency < 5s: {'PASS' if p95 < 5000 else 'FAIL'} ({p95:.2f}ms)")
        print(f"  Error Rate < 0.1%: {'PASS' if failure_rate < 0.1 else 'FAIL'} ({failure_rate:.2f}%)")


# Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
