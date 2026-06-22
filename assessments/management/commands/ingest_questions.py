import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from assessments.models import Question

class Command(BaseCommand):
    help = 'Ingest questions from the assessment Excel spreadsheet'

    def handle(self, *args, **options):
        file_path = "/Users/mac/Downloads/AMLOS_Assessment_Module_Test_Data_2.xlsx"
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"Excel file not found at {file_path}"))
            return

        xls = pd.ExcelFile(file_path)
        self.stdout.write(f"Found sheets: {xls.sheet_names}")

        # Fetch all existing questions in a single query to optimize lookups
        self.stdout.write("Loading existing questions from database into memory...")
        existing_qs = {
            (q.subject, q.question_id): q 
            for q in Question.objects.all()
        }
        self.stdout.write(f"Loaded {len(existing_qs)} existing questions.")

        total_created = 0
        total_updated = 0

        for sheet_name in xls.sheet_names:
            self.stdout.write(f"Processing sheet: {sheet_name}...")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            questions_to_create = []
            questions_to_update = []
            
            for _, row in df.iterrows():
                q_id = str(row.get('Question_ID', '')).strip()
                subject = str(row.get('Subject', '')).strip()
                chapter = str(row.get('Chapter', '')).strip()
                q_type = str(row.get('Question_Type', '')).strip()
                cognitive = str(row.get('Cognitive_Level', '')).strip()
                category = str(row.get('Category', '')).strip()
                q_text = str(row.get('Question_Text', '')).strip()
                
                # Image URL
                q_image = row.get('Question_Image_URL')
                q_image_url = str(q_image).strip() if pd.notna(q_image) and str(q_image).strip().lower() != 'nan' else None
                
                # Options
                opt_a = str(row.get('Option_A')).strip() if pd.notna(row.get('Option_A')) else None
                opt_b = str(row.get('Option_B')).strip() if pd.notna(row.get('Option_B')) else None
                opt_c = str(row.get('Option_C')).strip() if pd.notna(row.get('Option_C')) else None
                opt_d = str(row.get('Option_D')).strip() if pd.notna(row.get('Option_D')) else None
                
                correct_opt = str(row.get('Correct_Option', '')).strip() if pd.notna(row.get('Correct_Option')) else None
                short_expl = str(row.get('Short_Explanation', '')).strip() if pd.notna(row.get('Short_Explanation')) else None
                
                ans_text = str(row.get('Answer_Text', '')).strip()
                
                ans_image = row.get('Answer_Image_URL')
                ans_image_url = str(ans_image).strip() if pd.notna(ans_image) and str(ans_image).strip().lower() != 'nan' else None
                
                try:
                    marks = int(float(row.get('Marks', 1)))
                except:
                    marks = 1
                    
                try:
                    time_allowed = int(float(row.get('Time_Allowed_Minutes', 1)))
                except:
                    time_allowed = 1
                    
                diff = str(row.get('Difficulty_Level', '')).strip()
                tags = str(row.get('Tags', '')).strip() if pd.notna(row.get('Tags')) else ""

                key = (subject, q_id)
                if key in existing_qs:
                    existing_q = existing_qs[key]
                    existing_q.chapter = chapter
                    existing_q.question_type = q_type
                    existing_q.cognitive_level = cognitive
                    existing_q.category = category
                    existing_q.question_text = q_text
                    existing_q.question_image_url = q_image_url
                    existing_q.option_a = opt_a
                    existing_q.option_b = opt_b
                    existing_q.option_c = opt_c
                    existing_q.option_d = opt_d
                    existing_q.correct_option = correct_opt
                    existing_q.short_explanation = short_expl
                    existing_q.answer_text = ans_text
                    existing_q.answer_image_url = ans_image_url
                    existing_q.marks = marks
                    existing_q.time_allowed_minutes = time_allowed
                    existing_q.difficulty_level = diff
                    existing_q.tags = tags
                    questions_to_update.append(existing_q)
                else:
                    new_q = Question(
                        question_id=q_id,
                        subject=subject,
                        chapter=chapter,
                        question_type=q_type,
                        cognitive_level=cognitive,
                        category=category,
                        question_text=q_text,
                        question_image_url=q_image_url,
                        option_a=opt_a,
                        option_b=opt_b,
                        option_c=opt_c,
                        option_d=opt_d,
                        correct_option=correct_opt,
                        short_explanation=short_expl,
                        answer_text=ans_text,
                        answer_image_url=ans_image_url,
                        marks=marks,
                        time_allowed_minutes=time_allowed,
                        difficulty_level=diff,
                        tags=tags
                    )
                    questions_to_create.append(new_q)
                    # Add to local map to prevent duplicate inserts in the same run
                    existing_qs[key] = new_q

            # Perform bulk DB operations per sheet
            with transaction.atomic():
                if questions_to_create:
                    Question.objects.bulk_create(questions_to_create)
                    total_created += len(questions_to_create)
                if questions_to_update:
                    Question.objects.bulk_update(questions_to_update, [
                        'chapter', 'question_type', 'cognitive_level', 'category',
                        'question_text', 'question_image_url', 'option_a', 'option_b',
                        'option_c', 'option_d', 'correct_option', 'short_explanation',
                        'answer_text', 'answer_image_url', 'marks', 'time_allowed_minutes',
                        'difficulty_level', 'tags'
                    ])
                    total_updated += len(questions_to_update)

            self.stdout.write(self.style.SUCCESS(
                f"Sheet {sheet_name}: Created {len(questions_to_create)}, Updated {len(questions_to_update)}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Ingestion completed! Total Created: {total_created}, Total Updated: {total_updated} questions."
        ))
