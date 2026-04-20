import os
import sys
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AMLOS.settings')
django.setup()

from curriculum.models import SLO

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_slo_urls.py <url>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    slos_updated_count = SLO.objects.update(google_drive_link=target_url)
    print(f"Successfully updated google_drive_link to '{target_url}' for {slos_updated_count} SLO entries.")

if __name__ == '__main__':
    main()
