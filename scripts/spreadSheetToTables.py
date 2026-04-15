import os
import sys
import pandas as pd
import django
import re

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AMLOS.settings')
django.setup()

from curriculum.models import Subject, Chapter, SLO

def convert_google_sheets_url(url):
    """
    Converts a Google Sheets sharing URL to a CSV export URL.
    """
    if "docs.google.com/spreadsheets" in url:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            spreadsheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    return url

def map_difficulty(level):
    """
    Maps spreadsheet cognitive levels to model Difficulty choices.
    """
    level_str = str(level).strip().lower()
    if "knowledge" in level_str:
        return SLO.Difficulty.LOW
    elif "understanding" in level_str:
        return SLO.Difficulty.MEDIUM
    elif "application" in level_str:
        return SLO.Difficulty.HIGH
    return SLO.Difficulty.MEDIUM 

def migrate_spreadsheet(subject_id, sheet_url):
    try:
        subject = Subject.objects.get(id=subject_id)
        print(f"Found Subject: {subject.name} (Grade: {subject.grade})")
    except Subject.DoesNotExist:
        print(f"Error: Subject with ID {subject_id} does not exist.")
        return

    export_url = convert_google_sheets_url(sheet_url)
    print(f"Downloading data from: {export_url}")
    
    try:
        df_full = pd.read_csv(export_url, header=None)
        
        header_idx = -1
        for i, row in df_full.iterrows():
            row_vals = [str(x).lower() for x in row.values]
            if any("content domain" in val for val in row_vals):
                header_idx = i
                break
        
        if header_idx == -1:
            print("Error: Could not find the table header 'Content Domain / Area' in the spreadsheet.")
            return

        print(f"Table found at row {header_idx + 1}")
        
        df = pd.read_csv(export_url, skiprows=header_idx)
        
        df.columns = [re.sub(r'\s+', ' ', col).strip() for col in df.columns]
        
        domain_col = df.columns[0]
        df[domain_col] = df[domain_col].ffill()
        
        print(f"Processing {len(df)} rows...")
        
        created_chapters = 0
        created_slos = 0
        current_chapter = None

        for idx, row in df.iterrows():
            domain_name = str(row.get('Content Domain / Area', '')).strip()
            if not domain_name or domain_name.lower() in ['nan', 'practical slos', 'x']:
                continue
            
            if current_chapter is None or current_chapter.name != domain_name:
                current_chapter, created = Chapter.objects.get_or_create(
                    subject=subject,
                    name=domain_name
                )
                if created:
                    created_chapters += 1
                    print(f"Created Chapter: {domain_name}")
            
            description = str(row.get('Description', '')).strip()
            if not description or description.lower() == 'nan':
                continue
            
            slo_no = str(row.get('SLO No.', '')).strip()
            assessment = str(row.get('Form of Assessment', '')).strip()
            cognitive = str(row.get('Cognitive Level (Knowledge, Understanding, Application)', '')).strip()
            remarks = str(row.get('Remarks', '')).strip()
            drive_link = str(row.get('Google Drive Link', '')).strip()
            site_link = str(row.get('Google Site', '')).strip()
            priority = row.get('priority score', 0)
            time_val = row.get('time', 0)

            try:
                priority = int(float(priority)) if not pd.isna(priority) else 0
            except:
                priority = 0
                
            try:
                time_val = int(float(time_val)) if not pd.isna(time_val) else 0
            except:
                time_val = 0

            slo, created = SLO.objects.get_or_create(
                chapter=current_chapter,
                name=description,
                defaults={
                    'slo_no': slo_no,
                    'difficulty_frequency': map_difficulty(cognitive),
                    'estimated_time': time_val,
                    'form_of_assessment': assessment,
                    'remarks': remarks,
                    'google_drive_link': drive_link if "http" in drive_link else None,
                    'google_site': site_link if "http" in site_link else None,
                    'priority_score': priority
                }
            )
            
            if created:
                created_slos += 1
            else:
                slo.slo_no = slo_no
                slo.difficulty_frequency = map_difficulty(cognitive)
                slo.estimated_time = time_val
                slo.form_of_assessment = assessment
                slo.remarks = remarks
                slo.google_drive_link = drive_link if "http" in drive_link else None
                slo.google_site = site_link if "http" in site_link else None
                slo.priority_score = priority
                slo.save()

        print(f"Migration Complete!")
        print(f"Summary: {created_chapters} Chapters created, {created_slos} SLOs created.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    root = tk.Tk()
    root.withdraw()

    class InputDialog(simpledialog.Dialog):
        def body(self, master):
            tk.Label(master, text="Subject ID:").grid(row=0)
            tk.Label(master, text="Google Sheets URL:").grid(row=1)

            self.e1 = tk.Entry(master, width=50)
            self.e2 = tk.Entry(master, width=50)

            self.e1.grid(row=0, column=1, padx=10, pady=5)
            self.e2.grid(row=1, column=1, padx=10, pady=5)
            
            return self.e1 
            
        def apply(self):
            self.result = (self.e1.get(), self.e2.get())

    if len(sys.argv) > 2:
        subject_id = sys.argv[1]
        sheet_url = sys.argv[2]
        migrate_spreadsheet(subject_id, sheet_url)
    else:
        dialog = InputDialog(root, title="AMLOS Spreadsheet Migrator")
        if dialog.result:
            sid, url = dialog.result
            if sid and url:
                migrate_spreadsheet(sid, url)
                messagebox.showinfo("Complete", "Migration process finished. Check console for details.")
            else:
                messagebox.showwarning("Incomplete", "Both Subject ID and URL are required.")
    
    root.destroy()
