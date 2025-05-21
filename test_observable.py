import os
import django

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Observable
from organizations.models import Organization
from django.db import IntegrityError

def test_create_duplicate_observable():
    org = Organization.objects.first()
    
    # Create first observable
    obs1 = Observable.objects.create(
        value='1.2.3.4', 
        type='ip', 
        organization=org
    )
    print(f"Created first observable with ID: {obs1.id}")
    
    try:
        # Try to create a second observable with same value and type
        obs2 = Observable.objects.create(
            value='1.2.3.4', 
            type='ip', 
            organization=org
        )
        print(f"Success! Created second identical observable with ID: {obs2.id}")
    except IntegrityError as e:
        print(f"Error: {e}")
        print("Failed to create duplicate observable - constraint still exists!")

if __name__ == "__main__":
    test_create_duplicate_observable() 