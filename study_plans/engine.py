from datetime import timedelta, date
from django.db.models import Sum
from curriculum.models import SLO
from .models import StudyPlan, StudyPlanSLO
from rest_framework.exceptions import ValidationError
from django.utils import timezone

class StudyPlanEngine:
    def __init__(self, plan_data):
        """
        plan_data is a dictionary containing:
        - slo_ids
        - mode
        - start_date
        - end_date
        - min_study_time_daily
        - max_study_time_daily
        - subject_order (for SEQUENTIAL, now can be list of lists for phases)
        - custom_pattern (for CUSTOM)
        """
        self.slo_ids = plan_data.get('slo_ids', [])
        self.mode = plan_data.get('mode')
        self.start_date = plan_data.get('start_date')
        self.end_date = plan_data.get('end_date')
        self.min_study_time_daily = plan_data.get('min_study_time_daily', 120)
        self.max_study_time_daily = plan_data.get('max_study_time_daily', 300)
        self.subject_order = plan_data.get('subject_order', [])
        self.custom_pattern = plan_data.get('custom_pattern', {})

    def calculate_total_slo_time(self, slo_ids=None):
        ids = slo_ids or self.slo_ids
        result = SLO.objects.filter(id__in=ids).aggregate(total_time=Sum('estimated_time'))
        return result.get('total_time') or 0

    def calculate_available_time(self, start_date=None, end_date=None):
        start = start_date or self.start_date
        end = end_date or self.end_date
        total_days = (end - start).days + 1
        max_time = total_days * self.max_study_time_daily
        min_time = total_days * self.min_study_time_daily
        return min_time, max_time, total_days

    def validate_load(self, total_slo_time, max_available_time, total_days):
        if total_slo_time > max_available_time:
            required_daily = total_slo_time / total_days
            raise ValidationError(
                f"Your plan requires {required_daily/60:.2f} hours/day but your limit is {self.max_study_time_daily/60:.1f} hours"
            )

    def group_slos_by_phases(self, slos):
        """
        Groups SLOs into phases based on subject_order.
        If subject_order is ['Math', 'Physics'], phases are [['Math'], ['Physics']].
        If subject_order is [['Math', 'Physics'], ['Chem']], phases are [['Math', 'Physics'], ['Chem']].
        """
        phases = []
        if not self.subject_order:
            return [slos] # Single phase if no order

        for item in self.subject_order:
            phase_subjects = item if isinstance(item, list) else [item]
            phase_slos = [s for s in slos if s.chapter.subject.name in phase_subjects]
            if phase_slos:
                phases.append(phase_slos)
        
        # Catch any slos not in the phases (if subject_order is incomplete)
        assigned_ids = [s.id for p in phases for s in p]
        remaining = [s for s in slos if s.id not in assigned_ids]
        if remaining:
            phases.append(remaining)
            
        return phases

    def get_sorted_slos(self, slos=None):
        if slos is None:
            slos = list(SLO.objects.filter(id__in=self.slo_ids).select_related('chapter', 'chapter__subject'))
        
        if self.mode == StudyPlan.Mode.SEQUENTIAL:
            # Flattened order for simple sorting, though recalculate uses Phases directly
            # For initial sorting, we just use the phase structure
            phases = self.group_slos_by_phases(slos)
            sorted_slos = []
            for phase in phases:
                # Inside phase, sort by subject name, then chapter, then id
                phase.sort(key=lambda x: (x.chapter.subject.name, x.chapter_id, x.id))
                sorted_slos.extend(phase)
            return sorted_slos
            
        elif self.mode == StudyPlan.Mode.PARALLEL:
            slos_by_subject = {}
            for slo in slos:
                sub_name = slo.chapter.subject.name
                if sub_name not in slos_by_subject:
                    slos_by_subject[sub_name] = []
                slos_by_subject[sub_name].append(slo)
            
            sorted_slos = []
            max_len = max(len(v) for v in slos_by_subject.values()) if slos_by_subject else 0
            for i in range(max_len):
                for sub in sorted(slos_by_subject.keys()):
                    if i < len(slos_by_subject[sub]):
                        sorted_slos.append(slos_by_subject[sub][i])
            return sorted_slos

        elif self.mode == StudyPlan.Mode.CUSTOM:
            slos_by_subject = {}
            for slo in slos:
                sub_name = slo.chapter.subject.name
                if sub_name not in slos_by_subject:
                    slos_by_subject[sub_name] = []
                slos_by_subject[sub_name].append(slo)
            
            pointers = {sub: 0 for sub in slos_by_subject}
            sorted_slos = []
            
            while any(pointers[sub] < len(slos_by_subject[sub]) for sub in slos_by_subject):
                for sub, count_to_pick in self.custom_pattern.items():
                    if sub in slos_by_subject:
                        for _ in range(count_to_pick):
                            if pointers[sub] < len(slos_by_subject[sub]):
                                sorted_slos.append(slos_by_subject[sub][pointers[sub]])
                                pointers[sub] += 1
                
                for sub in sorted(slos_by_subject.keys()):
                    if sub not in self.custom_pattern:
                        if pointers[sub] < len(slos_by_subject[sub]):
                            sorted_slos.append(slos_by_subject[sub][pointers[sub]])
                            pointers[sub] += 1
            return sorted_slos
            
        return slos

    def generate_schedule(self, study_plan, slos=None, start_date=None):
        """
        Main distribution logic.
        start_date allows for recalculation starting from today.
        """
        current_slos = slos if slos is not None else list(SLO.objects.filter(id__in=self.slo_ids).select_related('chapter', 'chapter__subject'))
        target_start = start_date or self.start_date
        
        total_time = sum(s.estimated_time for s in current_slos)
        _, max_available, total_days = self.calculate_available_time(target_start, self.end_date)
        
        if total_days <= 0:
            study_plan.is_completable = False
            study_plan.save()
            return 0
            
        # Initial validation (mostly for creation)
        if slos is None:
             self.validate_load(total_time, max_available, total_days)

        # Implementation of Weight-based Phase Allocation for SEQUENTIAL
        if self.mode == StudyPlan.Mode.SEQUENTIAL:
            phases = self.group_slos_by_phases(current_slos)
            phase_weights = [sum(s.estimated_time for s in p) for p in phases]
            total_weight = sum(phase_weights)
            
            schedule_entries = []
            phase_start_date = target_start
            
            for i, phase in enumerate(phases):
                # Calculate how many days this phase gets based on weight
                proportion = phase_weights[i] / total_weight if total_weight > 0 else 0
                phase_days = max(1, round(total_days * proportion))
                
                # Check if we have enough days left
                days_left = (self.end_date - phase_start_date).days + 1
                phase_days = min(phase_days, days_left)
                
                phase_end_date = phase_start_date + timedelta(days=phase_days - 1)
                
                # Sort within phase
                sorted_phase_slos = self.get_sorted_slos(phase)
                
                # Distribute phase slos within its window
                entries = self._distribute_into_window(
                    study_plan, sorted_phase_slos, phase_start_date, phase_end_date
                )
                
                # Overflow check: If Phase i ends LATER than phase_end_date, we need to push next phase start
                if entries:
                    last_date = entries[-1].scheduled_date
                    phase_start_date = last_date + timedelta(days=1)
                else:
                    # If phase was empty or couldn't fit any (unlikely), just move start
                    phase_start_date = phase_end_date + timedelta(days=1)
                
                schedule_entries.extend(entries)
        else:
            # Parallel or Custom: standard distribution over the whole window
            sorted_slos = self.get_sorted_slos(current_slos)
            schedule_entries = self._distribute_into_window(
                study_plan, sorted_slos, target_start, self.end_date
            )

        # Check completability
        if schedule_entries:
            last_date = schedule_entries[-1].scheduled_date
            if last_date > self.end_date:
                study_plan.is_completable = False
            else:
                study_plan.is_completable = True
        else:
            study_plan.is_completable = total_time == 0

        # Bulk Save
        StudyPlanSLO.objects.bulk_create(schedule_entries)
        
        # Update metadata
        study_plan.total_slo_time = total_time
        study_plan.total_available_time = max_available
        study_plan.save()
        
        return len(schedule_entries)

    def _distribute_into_window(self, plan, slos, start_date, end_date):
        entries = []
        current_date = start_date
        daily_used = 0
        order = 1
        
        for slo in slos:
            if daily_used + slo.estimated_time > self.max_study_time_daily:
                current_date += timedelta(days=1)
                daily_used = 0
                order = 1
            
            # Note: We allow current_date to exceed end_date during calculation 
            # so we can detect uncompletableness afterwards.
            entries.append(StudyPlanSLO(
                plan=plan,
                slo=slo,
                scheduled_date=current_date,
                order_in_day=order,
                subject_name=slo.chapter.subject.name,
                chapter_name=slo.chapter.name,
                estimated_time=slo.estimated_time,
                is_completed=False
            ))
            daily_used += slo.estimated_time
            order += 1
            
        return entries

    def recalculate_if_needed(self, plan_obj):
        today = date.today()
        # 24h Sync logic: check if last_recalculated_at is before today
        if plan_obj.last_recalculated_at < today:
            # Plan needs sync
            # 1. Fetch all incomplete SLOs
            incomplete_slos = list(StudyPlanSLO.objects.filter(
                plan=plan_obj, is_completed=False
            ).select_related('slo', 'slo__chapter', 'slo__chapter__subject'))
            
            # Map back to original SLO models for the engine
            base_slos = [s.slo for s in incomplete_slos]
            
            # 2. Clear old scheduled entries for these incomplete SLOs
            StudyPlanSLO.objects.filter(plan=plan_obj, is_completed=False).delete()
            
            # 3. Re-run distribution from today
            self.generate_schedule(plan_obj, slos=base_slos, start_date=today)
            
            # 4. Update sync date
            plan_obj.last_recalculated_at = today
            plan_obj.save()
            return True
        return False
