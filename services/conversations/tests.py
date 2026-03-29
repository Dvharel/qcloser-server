from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from services.accounts.models import Organization, User
from .models import CallRecording, NotificationDelivery
from .tasks import sweep_stuck_deliveries


class SweepStuckDeliveriesTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(
            email="rep@example.com",
            password="testpass123",
            org=self.org,
        )
        self.recording = CallRecording.objects.create(
            org=self.org,
            audio_file="test/dummy.mp3",
        )

    def _make_delivery(self, status, kind=NotificationDelivery.Kind.FEEDBACK):
        return NotificationDelivery.objects.create(
            recording=self.recording,
            kind=kind,
            channel=NotificationDelivery.Channel.EMAIL,
            salesperson_email="rep@example.com",
            status=status,
        )

    def _backdate(self, delivery, minutes):
        """Force updated_at to a past value, bypassing auto_now."""
        NotificationDelivery.objects.filter(id=delivery.id).update(
            updated_at=timezone.now() - timedelta(minutes=minutes)
        )

    # ------------------------------------------------------------------
    # Stuck PENDING — older than 10 minutes
    # ------------------------------------------------------------------

    def test_stuck_pending_row_is_requeued(self):
        delivery = self._make_delivery(NotificationDelivery.Status.PENDING)
        self._backdate(delivery, minutes=11)
        with patch("services.conversations.tasks.send_delivery.delay") as mock_delay:
            sweep_stuck_deliveries()
        mock_delay.assert_called_once_with(delivery.id)

    # ------------------------------------------------------------------
    # Fresh PENDING — under 10 minutes
    # ------------------------------------------------------------------

    def test_fresh_pending_row_is_not_requeued(self):
        self._make_delivery(NotificationDelivery.Status.PENDING)
        with patch("services.conversations.tasks.send_delivery.delay") as mock_delay:
            sweep_stuck_deliveries()
        mock_delay.assert_not_called()

    # ------------------------------------------------------------------
    # Stuck RETRYING — older than 10 minutes
    # ------------------------------------------------------------------

    def test_stuck_retrying_row_is_requeued(self):
        delivery = self._make_delivery(NotificationDelivery.Status.RETRYING)
        self._backdate(delivery, minutes=11)
        with patch("services.conversations.tasks.send_delivery.delay") as mock_delay:
            sweep_stuck_deliveries()
        mock_delay.assert_called_once_with(delivery.id)

    # ------------------------------------------------------------------
    # SENT — never re-queued regardless of age
    # ------------------------------------------------------------------

    def test_sent_row_is_never_requeued(self):
        delivery = self._make_delivery(NotificationDelivery.Status.SENT)
        self._backdate(delivery, minutes=11)
        with patch("services.conversations.tasks.send_delivery.delay") as mock_delay:
            sweep_stuck_deliveries()
        mock_delay.assert_not_called()
