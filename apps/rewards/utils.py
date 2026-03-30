from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from apps.pickups.models import Pickup

def calculate_streak(user):
    """
    Calculates the 'Perfect Segregation Streak' in weeks.
    A week is perfect if there was at least one completed pickup and zero contamination flags.
    The streak breaks if a week has no pickups or at least one contaminated pickup.
    """
    if user.role != 'RESIDENT':
        return 0

    now = timezone.now()
    # Find the start of the current week (Monday)
    current_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    streak = 0
    weeks_back = 0
    max_history_weeks = 52 # Look back up to a year

    while weeks_back < max_history_weeks:
        week_start = current_week_start - timedelta(weeks=weeks_back)
        week_end = week_start + timedelta(days=7)
        
        pickups = Pickup.objects.filter(
            resident=user,
            status='completed',
            completed_at__range=(week_start, week_end)
        )
        
        count = pickups.count()
        if count == 0:
            # If it's the current week and nothing happened yet, we don't break the streak, just keep looking back.
            # But if it's a past week and nothing happened, streak breaks.
            if weeks_back == 0:
                weeks_back += 1
                continue
            else:
                break
                
        # Check for contamination in this week's pickups
        has_contamination = pickups.filter(verification__contamination_flag=True).exists()
        
        if has_contamination:
            break
        else:
            streak += 1
            
        weeks_back += 1
        
    return streak
