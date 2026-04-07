import logging
import os
import random

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask

from tests.locust.config import HEADERS, SAMPLE_QUESTIONS

logger = logging.getLogger(__name__)


class DocuQueryUser(HttpUser):
    wait_time = between(1, 3)  # wait 1-3 seconds between tasks

    def on_start(self) -> None:
        """Upload a document before starting tasks."""
        self.session_id: str | None = None
        pdf_path = os.getenv("TEST_PDF_PATH", "tests/locust/sample.pdf")

        if not os.path.exists(pdf_path):
            logger.error("Test PDF not found at %s", pdf_path)
            raise RescheduleTask()

        try:
            with open(pdf_path, "rb") as f:
                response = self.client.post(
                    "/upload",
                    files={"file": ("sample.pdf", f, "application/pdf")},
                    headers={"X-API-Key": HEADERS["X-API-Key"]},
                    name="/upload [setup]",
                )

            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id")
                if not self.session_id:
                    logger.warning("Upload response missing session_id")
                logger.info("Upload successful: %s", data.get("message"))
            else:
                logger.error("Upload failed with status: %s", response.status_code)
                raise RescheduleTask()
        except Exception as e:
            logger.error("Upload failed with exception: %s", e)
            raise RescheduleTask()

    @task(3)
    def ask_question(self) -> None:
        """Ask a random question -- weighted 3x more than other tasks."""
        question = random.choice(SAMPLE_QUESTIONS)
        payload: dict[str, str | None] = {"message": question}

        if self.session_id:
            payload["session_id"] = self.session_id

        with self.client.post(
            "/ask",
            json=payload,
            headers=HEADERS,
            name="/ask",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id") or self.session_id
                response.success()
            elif response.status_code == 429:
                # rate limited by gateway -- not a failure
                response.success()
                logger.warning("Rate limited by gateway")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def ask_cached_question(self) -> None:
        """Ask the same question repeatedly to test cache performance."""
        with self.client.post(
            "/ask",
            json={"message": "What is the main topic of this document?"},
            headers=HEADERS,
            name="/ask [cached]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache hit failed: {response.status_code}")

    @task(1)
    def upload_duplicate(self) -> None:
        """Upload same PDF again to test duplicate detection performance."""
        pdf_path = os.getenv("TEST_PDF_PATH", "tests/locust/sample.pdf")

        try:
            with open(pdf_path, "rb") as f:
                with self.client.post(
                    "/upload",
                    files={"file": ("sample.pdf", f, "application/pdf")},
                    headers={"X-API-Key": HEADERS["X-API-Key"]},
                    name="/upload [duplicate]",
                    catch_response=True,
                ) as response:
                    if response.status_code in (200, 202):
                        response.success()
                    else:
                        response.failure(
                            f"Duplicate upload failed: {response.status_code}"
                        )
        except FileNotFoundError:
            logger.error("Test PDF not found at %s", pdf_path)

    def on_stop(self) -> None:
        """Clean up session after testing."""
        logger.info("Session %s finished testing", self.session_id)


class GatewayUser(HttpUser):
    """Tests traffic through the Spring Boot gateway instead of FastAPI directly."""

    wait_time = between(1, 2)
    host = os.getenv("GATEWAY_HOST", "http://localhost:8080")

    def on_start(self) -> None:
        """Upload a document via gateway before starting tasks."""
        pdf_path = os.getenv("TEST_PDF_PATH", "tests/locust/sample.pdf")

        if not os.path.exists(pdf_path):
            logger.error("Test PDF not found at %s", pdf_path)
            raise RescheduleTask()

        try:
            with open(pdf_path, "rb") as f:
                self.client.post(
                    "/doc/upload",
                    files={"file": ("sample.pdf", f, "application/pdf")},
                    headers={"X-API-Key": HEADERS["X-API-Key"]},
                    name="/doc/upload [setup]",
                )
        except Exception as e:
            logger.error("Gateway upload failed: %s", e)
            raise RescheduleTask()

    @task
    def ask_via_gateway(self) -> None:
        with self.client.post(
            "/doc/ask",
            json={"message": random.choice(SAMPLE_QUESTIONS)},
            headers=HEADERS,
            name="/doc/ask [gateway]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success()  # rate limit is expected behaviour
            else:
                response.failure(f"Gateway ask failed: {response.status_code}")


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    exception: Exception | None,
    **kwargs: object,
) -> None:
    """Log slow requests and track errors for bottleneck analysis."""
    if response_time > 5000:  # over 5 seconds
        logger.warning("Slow request: %s took %.0fms", name, response_time)
    if exception:
        logger.error("Request failed: %s - %s", name, exception)
