from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, Doctor, Specialty, Delegate
from core.models import PharmaceuticalCompany
from events.models import Event, Voucher

class EventEnhancementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='password', type='ADMIN')
        self.company = PharmaceuticalCompany.objects.create(
            name="Pharma Co", contact_person="John", phone="123", email="j@j.com", address="Addr"
        )
        self.specialty = Specialty.objects.create(name="Cardiology")
        self.delegate = Delegate.objects.create(name="Delegate 1", phone="999")
        self.doctor = Doctor.objects.create(
            user=User.objects.create_user(username='doctor', password='password', type='DOCTOR'),
            name="Dr. Smith", phone="011", email="d@d.com", specialty=self.specialty
        )

    def test_event_multi_selection(self):
        event = Event.objects.create(
            name="Health Event", date=timezone.now().date(), company=self.company, voucher_value=100
        )
        event.delegates.add(self.delegate)
        event.specialties.add(self.specialty)
        
        self.assertEqual(event.delegates.count(), 1)
        self.assertEqual(event.specialties.count(), 1)

    def test_automatic_voucher_creation_for_new_doctors(self):
        # Create event
        event = Event.objects.create(
            name="Workshop", date=timezone.now().date(), company=self.company, voucher_value=200
        )
        # Add doctor
        event.doctors.add(self.doctor)
        
        # Verify voucher created
        voucher = Voucher.objects.filter(doctor=self.doctor, event=event).first()
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher.initial_value, 200)

        # Add another doctor
        doctor2 = Doctor.objects.create(
            user=User.objects.create_user(username='doctor2', password='password', type='DOCTOR'),
            name="Dr. Jones", phone="012", email="d2@d.com", specialty=self.specialty
        )
        event.doctors.add(doctor2)
        
        # Verify only one voucher for doctor2, and no extra for doctor1
        self.assertEqual(Voucher.objects.filter(doctor=doctor2, event=event).count(), 1)
        self.assertEqual(Voucher.objects.filter(doctor=self.doctor, event=event).count(), 1)

    def test_custom_voucher_without_event(self):
        voucher = Voucher.objects.create(
            doctor=self.doctor,
            initial_value=500,
            current_balance=500
        )
        self.assertIsNone(voucher.event)
        self.assertEqual(voucher.initial_value, 500)
        # Expiry should be 90 days from now (custom logic in save)
        expected_expiry = timezone.now().date() + timedelta(days=90)
        self.assertEqual(voucher.expiry_date, expected_expiry)
