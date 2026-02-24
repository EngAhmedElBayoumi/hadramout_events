import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from accounts.models import Doctor, Specialty

def migrate_specialties():
    doctors = Doctor.objects.all()
    created_count = 0
    updated_count = 0
    
    for doctor in doctors:
        # Check if specialty is still a string (this happens when ForeignKey points to non-existent ID or 
        # when we are in a middle of a messy migration)
        # However, because it's a ForeignKey now, if it failed it might be null.
        # But wait, the IntegrityError showed it had a value '...'. 
        # This usually happens during the actual migration.
        pass

    print("Note: This script should be run via a data migration or manually before applying the FK change if data exists.")

if __name__ == "__main__":
    migrate_specialties()
