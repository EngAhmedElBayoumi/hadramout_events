from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from .models import User, Doctor, Specialty


class DoctorRegistrationView(View):
    """Public page for doctors to register themselves."""
    template_name = 'accounts/doctor_register.html'

    def get(self, request):
        specialties = Specialty.objects.all().order_by('name')
        return render(request, self.template_name, {'specialties': specialties})

    def post(self, request):
        # Get form data
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        specialty_id = request.POST.get('specialty')
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        specialties = Specialty.objects.all().order_by('name')
        context = {
            'specialties': specialties,
            'form_data': {
                'name': name,
                'phone': phone,
                'email': email,
                'username': username,
                'specialty_id': specialty_id,
            }
        }

        # Validation
        errors = []
        if not name:
            errors.append('يرجى إدخال الاسم.')
        if not phone:
            errors.append('يرجى إدخال رقم الهاتف.')
        if not email and not username:
            errors.append('يرجى إدخال البريد الإلكتروني أو اسم المستخدم.')
        if not password:
            errors.append('يرجى إدخال كلمة المرور.')
        if password and len(password) < 6:
            errors.append('كلمة المرور يجب أن تكون 6 أحرف على الأقل.')
        if password != password_confirm:
            errors.append('كلمتا المرور غير متطابقتين.')

        # Check uniqueness
        if email and User.objects.filter(email=email).exists():
            errors.append('البريد الإلكتروني مسجل مسبقاً.')
        if username and User.objects.filter(username=username).exists():
            errors.append('اسم المستخدم مسجل مسبقاً.')
        if phone and Doctor.objects.filter(phone=phone).exists():
            errors.append('رقم الهاتف مسجل مسبقاً.')

        if errors:
            context['errors'] = errors
            return render(request, self.template_name, context)

        try:
            with transaction.atomic():
                # Determine username
                if not username:
                    if email:
                        username = email.split('@')[0]
                    else:
                        username = phone
                # Ensure unique username
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email or '',
                    password=password,
                    type='DOCTOR',
                    phone=phone,
                )

                # Create Doctor profile
                specialty = None
                if specialty_id:
                    try:
                        specialty = Specialty.objects.get(id=specialty_id)
                    except Specialty.DoesNotExist:
                        pass

                doctor = Doctor.objects.create(
                    user=user,
                    name=name,
                    phone=phone,
                    email=email or None,
                    specialty=specialty,
                )

                # Send welcome email
                try:
                    send_mail(
                        'مرحباً بك في نظام حضرموت - تم إنشاء حسابك بنجاح',
                        f'مرحباً د. {name}،\n\n'
                        f'تم إنشاء حسابك بنجاح في نظام قسائم حضرموت.\n\n'
                        f'بيانات الدخول:\n'
                        f'- اسم المستخدم: {username}\n'
                        f'- البريد الإلكتروني: {email}\n\n'
                        f'يمكنك تسجيل الدخول من خلال الرابط التالي:\n'
                        f'{request.build_absolute_uri("/")}\n\n'
                        f'شكراً لانضمامك! 🎉',
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

                messages.success(request, f'تم إنشاء حسابك بنجاح! اسم المستخدم: {username}')
                return redirect('login')

        except Exception as e:
            context['errors'] = [f'حدث خطأ غير متوقع: {str(e)}']
            return render(request, self.template_name, context)


class SpecialtySearchView(View):
    """API endpoint for specialty search (used by searchable dropdown)."""
    def get(self, request):
        q = request.GET.get('q', '')
        specialties = Specialty.objects.filter(name__icontains=q).order_by('name')[:20]
        results = [{'id': s.id, 'name': s.name} for s in specialties]
        return JsonResponse({'results': results})


class RegistrationQRView(View):
    """Admin page to display QR code for doctor registration URL."""
    template_name = 'accounts/registration_qr.html'

    def get(self, request):
        from django.urls import reverse
        import qrcode
        import base64
        from io import BytesIO

        registration_url = request.build_absolute_uri(reverse('doctor_register'))
        
        # Generate QR Code in Backend
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(registration_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#800000", back_color="white")
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return render(request, self.template_name, {
            'registration_url': registration_url,
            'qr_base64': qr_base64,
        })
