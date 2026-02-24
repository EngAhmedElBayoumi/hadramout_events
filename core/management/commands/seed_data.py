"""
Seeder management command for Hadramout Events System
Creates: 20 companies, 2000 doctors, 50 vendors, 200 events, ~5000 transactions
"""
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction as db_transaction

from accounts.models import User, Doctor, Vendor
from core.models import PharmaceuticalCompany, Transaction, VendorSettlement
from events.models import Event, Voucher


# ─── Arabic Data Lists ───────────────────────────────────────────────

FIRST_NAMES = [
    'أحمد', 'محمد', 'علي', 'عمر', 'خالد', 'يوسف', 'إبراهيم', 'حسن', 'حسين', 'سعيد',
    'عبدالله', 'عبدالرحمن', 'طارق', 'ياسر', 'مصطفى', 'كريم', 'سامي', 'رامي', 'هشام', 'وليد',
    'ماجد', 'فهد', 'سلطان', 'ناصر', 'بدر', 'فيصل', 'تركي', 'سعود', 'منصور', 'راشد',
    'نبيل', 'أنور', 'جمال', 'صالح', 'زياد', 'عادل', 'حمزة', 'بلال', 'أيمن', 'شريف',
    'هاني', 'باسم', 'ثامر', 'مروان', 'عمار', 'حاتم', 'غسان', 'وسام', 'معاذ', 'أسامة',
]

LAST_NAMES = [
    'الأحمد', 'المحمد', 'العلي', 'الحسن', 'العمري', 'الشريف', 'البكري', 'الغامدي', 'القحطاني', 'الحربي',
    'الدوسري', 'العتيبي', 'المطيري', 'الشهري', 'الزهراني', 'السبيعي', 'البلوي', 'السلمي', 'الثقفي', 'الحارثي',
    'المالكي', 'الجهني', 'العنزي', 'الشمري', 'الرشيدي', 'الخالدي', 'السعدي', 'الهاشمي', 'العباسي', 'النعيمي',
    'الكندي', 'اليافعي', 'الحضرمي', 'الباعبود', 'بن محفوظ', 'المهري', 'السقاف', 'العطاس', 'باحارث', 'الكثيري',
]

SPECIALTIES = [
    'طب القلب', 'طب العيون', 'جراحة عامة', 'طب الأطفال', 'طب النساء والتوليد',
    'طب الأسنان', 'الأمراض الجلدية', 'الطب الباطني', 'العظام', 'المسالك البولية',
    'الأنف والأذن والحنجرة', 'الأعصاب', 'الطب النفسي', 'التخدير', 'الأشعة',
    'طب الطوارئ', 'أمراض الدم', 'الغدد الصماء', 'الروماتيزم', 'طب الأسرة',
]

PHARMA_COMPANIES = [
    'فارما مصر', 'النيل للأدوية', 'الدواء للصناعات الدوائية', 'جلاكسو العربية',
    'المتحدة للأدوية', 'الحكمة للأدوية', 'سبيماكو الدوائية', 'تبوك الدوائية',
    'الدوائية المتقدمة', 'رام فارما', 'أكديما للأدوية', 'سيجما للأدوية',
    'أمون للأدوية', 'ابن سينا فارما', 'المهجر للأدوية', 'الرازي للأدوية',
    'العربية للأدوية', 'الخليج للأدوية', 'ميدي فارما', 'الشرق للصناعات الدوائية',
]

VENDOR_NAMES = [
    'سوبرماركت الخير', 'ميني ماركت النور', 'سوبرماركت البركة', 'هايبر ماركت الأمل',
    'متجر الأسرة', 'سوق الطازج', 'ماركت السعادة', 'سوبرماركت الوفاء',
    'مطعم الشرق', 'مطعم بن حمودة', 'مطعم السلطان', 'مطعم الفردوس',
    'صيدلية الشفاء', 'صيدلية الحياة', 'صيدلية الأمان', 'صيدلية الدواء',
    'مخبز الفرن الذهبي', 'مخبز الأصالة', 'حلويات النجمة', 'حلويات الأمير',
    'جزارة اللحوم الطازجة', 'جزارة الجودة', 'سمك البحر الطازج', 'أسواق الريف',
    'متجر الفواكه الطازجة', 'خضار وفواكه الحديقة', 'بقالة الحي', 'بقالة الأمانة',
    'مطعم بيت الكبسة', 'مطعم المندي الحضرمي', 'مطعم هنا', 'مطعم الديوان',
    'كافيه القهوة العربية', 'كافيه المساء', 'عصائر الطبيعة', 'عصائر الفاكهة',
    'محل العطارة', 'محل البهارات', 'متجر العسل الطبيعي', 'متجر التمور',
    'مطبخ أم علي', 'مطبخ الست حياة', 'مأكولات بحرية السندباد', 'شاورما الشام',
    'فطائر ومعجنات الخير', 'بيتزا الفرن', 'مطعم المشويات', 'مطعم الطازج',
    'سوبرماركت الجزيرة', 'سوبرماركت اليمن',
]

VENDOR_CATEGORIES = [
    'سوبرماركت', 'مطعم', 'صيدلية', 'مخبز', 'حلويات',
    'جزارة', 'أسماك', 'خضار وفواكه', 'بقالة', 'كافيه',
]

EVENT_NAMES = [
    'مؤتمر القلب السنوي', 'ملتقى أطباء العيون', 'ندوة طب الأطفال',
    'ورشة عمل جراحية', 'مؤتمر الطب الباطني', 'ملتقى أطباء الأسنان',
    'ندوة الأمراض الجلدية', 'مؤتمر العظام الدولي', 'ملتقى المسالك البولية',
    'ندوة الأعصاب', 'مؤتمر الطب النفسي', 'ملتقى التخدير',
    'ندوة الأشعة', 'مؤتمر طب الطوارئ', 'ملتقى أمراض الدم',
    'ندوة الغدد الصماء', 'مؤتمر الروماتيزم', 'ملتقى طب الأسرة',
    'مؤتمر الأنف والأذن', 'ندوة طب النساء', 'ملتقى الجراحة التجميلية',
    'مؤتمر المناعة', 'ندوة الأورام', 'ملتقى الأمراض المعدية',
    'مؤتمر التغذية العلاجية', 'ندوة العلاج الطبيعي', 'ملتقى الطب البديل',
    'مؤتمر طب الرياضة', 'ندوة طب المسنين', 'ملتقى الصحة العامة',
]

CITIES = [
    'القاهرة', 'الإسكندرية', 'المكلا', 'عدن', 'صنعاء',
    'جدة', 'الرياض', 'دبي', 'المنامة', 'مسقط',
]

ITEMS_DESCRIPTIONS = [
    'مواد غذائية متنوعة', 'لحوم ودواجن طازجة', 'خضار وفواكه', 'مشروبات وعصائر',
    'وجبة غداء كاملة', 'وجبة عشاء عائلية', 'مستلزمات طبية', 'أدوية ومكملات',
    'حلويات ومعجنات', 'مخبوزات طازجة', 'قهوة ومشروبات ساخنة', 'مشويات',
    'أسماك طازجة', 'بهارات وتوابل', 'عسل طبيعي وتمور', 'فطائر ومعجنات',
]


class Command(BaseCommand):
    help = 'Seeds the database with realistic test data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear all existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('🗑️  Clearing existing data...'))
            self._clear_data()

        self.stdout.write(self.style.SUCCESS('🌱 Starting database seeding...'))
        self.stdout.write('')

        # Step 1: Create Superuser
        self._create_superuser()

        # Step 2: Create Pharmaceutical Companies
        companies = self._create_companies()

        # Step 3: Create Doctors (2000)
        doctors = self._create_doctors(2000)

        # Step 4: Create Vendors (50)
        vendors = self._create_vendors(50)

        # Step 5: Create Events (200) and assign Doctors (auto-creates Vouchers via signal)
        events = self._create_events(200, companies, doctors)

        # Step 6: Create Transactions (5000)
        self._create_transactions(5000, doctors, vendors)

        # Step 7: Create some Vendor Settlements
        self._create_settlements(vendors)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ Seeding complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self._print_summary()

    def _clear_data(self):
        """Clear all data in proper order to respect FK constraints"""
        VendorSettlement.objects.all().delete()
        Transaction.objects.all().delete()
        Voucher.objects.all().delete()
        Event.objects.all().delete()
        Doctor.objects.all().delete()
        Vendor.objects.all().delete()
        PharmaceuticalCompany.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('  ✓ Data cleared'))

    def _create_superuser(self):
        """Create admin superuser"""
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@hadramout.com',
                password='admin123',
                type='ADMIN'
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Superuser created (admin / admin123)'))
        else:
            self.stdout.write('  ℹ️  Superuser already exists')

    def _create_companies(self):
        """Create 20 pharmaceutical companies"""
        self.stdout.write('📦 Creating pharmaceutical companies...')
        companies = []
        for i, name in enumerate(PHARMA_COMPANIES):
            company, created = PharmaceuticalCompany.objects.get_or_create(
                name=name,
                defaults={
                    'contact_person': f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                    'phone': f'02{random.randint(10000000, 99999999)}',
                    'email': f'contact{i}@{name.replace(" ", "").lower()[:8]}.com',
                    'address': f'{random.choice(CITIES)} - شارع {random.randint(1, 100)}',
                }
            )
            companies.append(company)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(companies)} companies ready'))
        return companies

    def _create_doctors(self, count):
        """Create doctors with user accounts"""
        self.stdout.write(f'👨‍⚕️ Creating {count} doctors...')
        doctors = []
        existing_count = Doctor.objects.count()

        batch_size = 200
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            for i in range(batch_start, batch_end):
                idx = existing_count + i
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                username = f'doc_{idx}'

                if User.objects.filter(username=username).exists():
                    continue

                user = User.objects.create_user(
                    username=username,
                    password='pass1234',
                    email=f'doctor{idx}@med.com',
                    type='DOCTOR'
                )
                doctor = Doctor.objects.create(
                    user=user,
                    name=f'د. {first} {last}',
                    phone=f'01{random.choice(["0", "1", "2", "5"])}{random.randint(10000000, 99999999)}',
                    email=f'd{idx}@clinic.com',
                    specialty=random.choice(SPECIALTIES),
                )
                doctors.append(doctor)

            progress = min(batch_end, count)
            self.stdout.write(f'  ... {progress}/{count}')

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(doctors)} doctors created'))
        return doctors

    def _create_vendors(self, count):
        """Create vendors with user accounts"""
        self.stdout.write(f'🏪 Creating {count} vendors...')
        vendors = []
        existing_count = Vendor.objects.count()

        for i in range(count):
            idx = existing_count + i
            name = VENDOR_NAMES[i] if i < len(VENDOR_NAMES) else f'متجر رقم {idx}'
            username = f'vendor_{idx}'

            if User.objects.filter(username=username).exists():
                continue

            user = User.objects.create_user(
                username=username,
                password='pass1234',
                email=f'vendor{idx}@store.com',
                type='VENDOR'
            )
            vendor = Vendor.objects.create(
                user=user,
                name=name,
                contact_person=f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                phone=f'01{random.choice(["0", "1", "2", "5"])}{random.randint(10000000, 99999999)}',
                email=f'v{idx}@vendors.com',
                address=f'{random.choice(CITIES)} - حي {random.randint(1, 20)}',
                category=random.choice(VENDOR_CATEGORIES),
            )
            vendors.append(vendor)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(vendors)} vendors created'))
        return vendors

    def _create_events(self, count, companies, doctors):
        """Create events and assign doctors (triggers voucher creation signal)"""
        self.stdout.write(f'🎉 Creating {count} events and distributing vouchers...')
        events = []
        today = date.today()

        for i in range(count):
            # Events spread across last 6 months
            event_date = today - timedelta(days=random.randint(0, 180))
            voucher_value = Decimal(str(random.choice([500, 750, 1000, 1500, 2000, 2500, 3000, 5000])))
            expiry_days = random.choice([30, 60, 90, 120, 180])

            event_name_base = random.choice(EVENT_NAMES)
            event_name = f'{event_name_base} {i + 1}'

            event = Event.objects.create(
                name=event_name,
                date=event_date,
                company=random.choice(companies),
                voucher_value=voucher_value,
                voucher_expiry_days=expiry_days,
            )
            events.append(event)

            # Assign 5-20 random doctors to each event
            num_doctors = random.randint(5, min(20, len(doctors)))
            selected_doctors = random.sample(doctors, num_doctors)
            event.doctors.add(*selected_doctors)  # This triggers the signal!

            if (i + 1) % 50 == 0:
                self.stdout.write(f'  ... {i + 1}/{count} events')

        total_vouchers = Voucher.objects.count()
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(events)} events created with {total_vouchers} vouchers'))
        return events

    def _create_transactions(self, target_count, doctors, vendors):
        """Create transactions by directly inserting records (faster than process_transaction)"""
        self.stdout.write(f'📄 Creating {target_count} transactions...')

        # We'll create transactions directly for speed, but still update voucher balances
        created = 0
        errors = 0
        today = timezone.now()

        # Get all doctors who have active vouchers with balance
        doctors_with_vouchers = list(
            Doctor.objects.filter(
                vouchers__is_active=True,
                vouchers__current_balance__gt=0
            ).distinct()
        )

        if not doctors_with_vouchers:
            self.stdout.write(self.style.ERROR('  ✗ No doctors with active vouchers found!'))
            return

        self.stdout.write(f'  ℹ️  {len(doctors_with_vouchers)} doctors have active vouchers')

        while created < target_count:
            doctor = random.choice(doctors_with_vouchers)

            # Get active vouchers for this doctor ordered by expiry (FIFO)
            active_vouchers = list(
                Voucher.objects.filter(
                    doctor=doctor,
                    is_active=True,
                    current_balance__gt=0
                ).order_by('expiry_date')
            )

            if not active_vouchers:
                # Remove this doctor from the pool
                doctors_with_vouchers.remove(doctor)
                if not doctors_with_vouchers:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  All vouchers exhausted at {created} transactions'))
                    break
                continue

            total_balance = sum(v.current_balance for v in active_vouchers)

            # Random amount between 50-500, but capped at available balance / 1.25
            max_spendable = float(total_balance / Decimal('1.25'))
            if max_spendable < 50:
                # Remove this doctor - balance too low
                doctors_with_vouchers.remove(doctor)
                if not doctors_with_vouchers:
                    break
                continue

            amount_spent = Decimal(str(round(random.uniform(50, min(500, max_spendable)), 2)))
            management_fee_pct = Decimal('0.25')
            management_fee_amount = amount_spent * management_fee_pct
            total_deducted = amount_spent + management_fee_amount

            # FIFO deduction
            remaining = total_deducted
            first_voucher = None

            try:
                with db_transaction.atomic():
                    for voucher in active_vouchers:
                        if remaining <= 0:
                            break
                        if not first_voucher:
                            first_voucher = voucher

                        if voucher.current_balance >= remaining:
                            voucher.current_balance -= remaining
                            remaining = Decimal('0')
                            if voucher.current_balance == 0:
                                voucher.is_active = False
                        else:
                            remaining -= voucher.current_balance
                            voucher.current_balance = Decimal('0')
                            voucher.is_active = False
                        voucher.save()

                    # Random transaction date in last 60 days
                    trx_date = today - timedelta(
                        days=random.randint(0, 60),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )

                    Transaction.objects.create(
                        voucher=first_voucher,
                        vendor=random.choice(vendors),
                        doctor=doctor,
                        amount_spent=amount_spent,
                        management_fee_percentage=Decimal('25.00'),
                        management_fee_amount=management_fee_amount,
                        total_deducted=total_deducted,
                        transaction_date=trx_date,
                        items_description=random.choice(ITEMS_DESCRIPTIONS),
                        invoice_number=str(uuid.uuid4()),
                    )
                    created += 1

                    if created % 500 == 0:
                        self.stdout.write(f'  ... {created}/{target_count}')

            except Exception as e:
                errors += 1
                if errors > 100:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  Too many errors, stopping at {created}'))
                    break

        self.stdout.write(self.style.SUCCESS(f'  ✓ {created} transactions created'))

    def _create_settlements(self, vendors):
        """Create some vendor settlements for realism"""
        self.stdout.write('💰 Creating vendor settlements...')
        count = 0

        for vendor in vendors:
            # 60% chance of having a settlement
            if random.random() < 0.6:
                total_vendor_sales = Transaction.objects.filter(vendor=vendor).count()
                if total_vendor_sales == 0:
                    continue

                from django.db.models import Sum
                total_amount = Transaction.objects.filter(
                    vendor=vendor, settlement__isnull=True
                ).aggregate(total=Sum('amount_spent'))['total']

                if total_amount and total_amount > 0:
                    # Settle 50-80% of outstanding amount
                    settle_pct = Decimal(str(round(random.uniform(0.5, 0.8), 2)))
                    settle_amount = total_amount * settle_pct

                    settlement = VendorSettlement.objects.create(
                        vendor=vendor,
                        amount_settled=settle_amount,
                        settlement_date=date.today() - timedelta(days=random.randint(1, 30)),
                    )

                    # Link some transactions to this settlement
                    unsettled = Transaction.objects.filter(
                        vendor=vendor, settlement__isnull=True
                    ).order_by('transaction_date')

                    running_total = Decimal('0')
                    for trx in unsettled:
                        if running_total + trx.amount_spent > settle_amount:
                            break
                        trx.settlement = settlement
                        trx.save()
                        running_total += trx.amount_spent

                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} vendor settlements created'))

    def _print_summary(self):
        """Print final counts"""
        self.stdout.write('')
        self.stdout.write(f'  📊 Summary:')
        self.stdout.write(f'     Users:         {User.objects.count()}')
        self.stdout.write(f'     Companies:     {PharmaceuticalCompany.objects.count()}')
        self.stdout.write(f'     Doctors:       {Doctor.objects.count()}')
        self.stdout.write(f'     Vendors:       {Vendor.objects.count()}')
        self.stdout.write(f'     Events:        {Event.objects.count()}')
        self.stdout.write(f'     Vouchers:      {Voucher.objects.count()}')
        self.stdout.write(f'     Transactions:  {Transaction.objects.count()}')
        self.stdout.write(f'     Settlements:   {VendorSettlement.objects.count()}')
        self.stdout.write('')
        self.stdout.write(f'  🔐 Login: admin / admin123')
        self.stdout.write(f'  🔐 Vendor login: vendor_0 / pass1234')
