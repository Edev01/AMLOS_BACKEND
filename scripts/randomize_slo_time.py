import os
import sys
import django
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AMLOS.settings')
django.setup()

from curriculum.models import SLO

def randomize_slo_times():
    print("🎲 Randomizing estimated_time for all SLOs...")
    
    slos = SLO.objects.all()
    count = slos.count()
    
    if count == 0:
        print("Empty table. No SLOs to update.")
        return

    updated_count = 0
    for slo in slos:
        random_time = random.randint(20, 60)
        
        slo.estimated_time = random_time
        slo.save()
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"  Processed {updated_count}/{count} SLOs...")

    print(f" Successfully updated {updated_count} SLOs with random estimated times.")

if __name__ == "__main__":
    randomize_slo_times()
