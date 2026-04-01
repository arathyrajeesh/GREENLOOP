from celery import shared_task
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.db.models import Count, Sum, Avg
import logging
import csv
import io
import datetime

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

logger = logging.getLogger(__name__)

@shared_task
def generate_ward_collection_report(report_id):
    """
    Generates a general ward collection summary.
    """
    from .models import WardCollectionReport
    if HTML is None:
        logger.error("WeasyPrint is not installed. PDF generation failed.")
        return "WeasyPrint not installed"

    try:
        report = WardCollectionReport.objects.select_related('ward', 'generated_by').get(id=report_id)
        report.status = 'PENDING'
        report.save(update_fields=['status'])

        ward = report.ward
        start = report.start_date
        end = report.end_date

        from apps.pickups.models import Pickup
        from apps.recyclers.models import RecyclerPurchase
        from apps.payments.models import FeeCollection
        from apps.complaints.models import Complaint
        from apps.reports.models import NPSSurvey
        from apps.users.models import User

        # 1. Pickups Data
        pickups = Pickup.objects.filter(ward=ward, scheduled_date__range=[start, end]).values('status').annotate(count=Count('id'))
        pickups_by_status = {p['status']: p['count'] for p in pickups}

        # 2. Material/Waste Data
        waste_data = RecyclerPurchase.objects.filter(source_ward=ward, purchase_date__date__range=[start, end]).values('material_type__name').annotate(total_qty=Sum('weight_kg'))

        # 3. Financial Data
        fees_qs = FeeCollection.objects.filter(ward=ward, payment_date__date__range=[start, end]).aggregate(total=Sum('amount'))
        total_fees = fees_qs['total'] or 0.0

        # 4. Complaints Data
        complaints_qs = Complaint.objects.filter(reporter__ward=ward, created_at__date__range=[start, end]).values('category').annotate(count=Count('id'))

        # 5. NPS and Onboarding
        nps_data = NPSSurvey.objects.filter(resident__ward=ward, submitted_at__date__range=[start, end]).aggregate(avg_score=Avg('score'), total_responses=Count('id'))
        onboarding_count = User.objects.filter(ward=ward, role='RESIDENT', created_at__date__range=[start, end]).count()
        
        report_data = {
            'pickups_by_status': pickups_by_status,
            'waste_by_material': list(waste_data),
            'total_fees': total_fees,
            'complaints_by_category': list(complaints_qs),
            'nps_avg': round(nps_data['avg_score'], 2) if nps_data['avg_score'] else "0.0",
            'nps_responses': nps_data['total_responses'],
            'onboarded_households': onboarding_count
        }

        # --- CSV Generation ---
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['Metric', 'Category/Status/Type', 'Value'])
        for s, c in pickups_by_status.items(): csv_writer.writerow(['Pickup', s.title(), c])
        for w in waste_data: csv_writer.writerow(['Waste Collected (kg)', w['material_type__name'], w['total_qty']])
        csv_writer.writerow(['Financial', 'Total Fees (INR)', total_fees])
        csv_writer.writerow(['Metrics', 'Avg NPS Score', report_data['nps_avg']])
        csv_writer.writerow(['Metrics', 'Households Onboarded', report_data['onboarded_households']])
        for cl in complaints_qs: csv_writer.writerow(['Complaint', cl['category'], cl['count']])
            
        csv_filename = f"ward_{ward.number}_report_{start}_{end}.csv"
        report.csv_file.save(csv_filename, ContentFile(csv_buffer.getvalue().encode('utf-8')), save=False)

        # --- PDF Generation ---
        context = {'report': report, 'data': report_data}
        html_string = render_to_string('reports/ward_report.html', context)
        pdf_bytes = HTML(string=html_string).write_pdf()
        pdf_filename = f"ward_{ward.number}_report_{start}_{end}.pdf"
        report.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=False)
        
        report.status = 'COMPLETED'
        report.save()

        from apps.notifications.tasks import notify_admin_report_ready
        notify_admin_report_ready.delay(report.id)
        return f"Success: {pdf_filename}"

    except Exception as e:
        logger.exception(f"Report generation error: {str(e)}")
        from .models import WardCollectionReport
        report = WardCollectionReport.objects.get(id=report_id)
        report.status = 'FAILED'
        report.save(update_fields=['status'])
        return f"Error: {str(e)}"

@shared_task
def generate_suchitwa_mission_report(report_id):
    """
    Generates a PDF report for Suchitwa Mission regulatory compliance.
    """
    from .models import WardCollectionReport
    if HTML is None:
        logger.error("WeasyPrint is not installed.")
        return "WeasyPrint not installed"

    try:
        report = WardCollectionReport.objects.select_related('ward').get(id=report_id)
        report.status = 'PENDING'
        report.save(update_fields=['status'])

        ward = report.ward
        start = report.start_date
        end = report.end_date
        total_days = (end - start).days + 1

        from apps.pickups.models import Pickup, PickupVerification
        from apps.attendance.models import AttendanceLog
        from apps.users.models import User
        from apps.payments.models import FeeCollection

        # 1. Household Coverage
        actual_households = User.objects.filter(ward=ward, role='RESIDENT', pickups__scheduled_date__range=[start, end]).distinct().count()
        coverage_pct = round((actual_households / ward.total_households) * 100, 1) if ward.total_households > 0 else 0.0

        # 2. Waste Weights & Segregation Accuracy
        pickups = Pickup.objects.filter(ward=ward, scheduled_date__range=[start, end], status='completed')
        total_weight = pickups.aggregate(total=Sum('weight_kg'))['total'] or 0.0
        
        waste_weights = []
        for code, label in Pickup.WASTE_CHOICES:
            p_cat = pickups.filter(waste_type=code)
            cat_weight = p_cat.aggregate(w=Sum('weight_kg'))['w'] or 0.0
            total_cat = p_cat.count()
            flagged = PickupVerification.objects.filter(pickup__in=p_cat, contamination_flag=True).count()
            accuracy = round(((total_cat - flagged) / total_cat) * 100, 1) if total_cat > 0 else 100.0
            waste_weights.append({'name': label, 'weight': float(cat_weight), 'accuracy': accuracy})

        # 3. Overall Accuracy
        total_pickups = pickups.count()
        total_flagged = PickupVerification.objects.filter(pickup__in=pickups, contamination_flag=True).count()
        overall_accuracy = round(((total_pickups - total_flagged) / total_pickups) * 100, 1) if total_pickups > 0 else 100.0

        # 4. Financials & Attendance
        total_fees = FeeCollection.objects.filter(ward=ward, payment_date__date__range=[start, end]).aggregate(total=Sum('amount'))['total'] or 0.0
        workers = User.objects.filter(ward=ward, role='HKS_WORKER')
        expected_logs = workers.count() * total_days
        actual_logs = AttendanceLog.objects.filter(worker__in=workers, date__range=[start, end], status='PRESENT').count()
        attendance_pct = round((actual_logs / expected_logs) * 100, 1) if expected_logs > 0 else 0.0

        data = {
            'household_coverage': {'actual': actual_households, 'percentage': coverage_pct},
            'waste_weights': waste_weights,
            'total_weight': float(total_weight),
            'overall_accuracy': overall_accuracy,
            'financials': {'total_fees': float(total_fees)},
            'attendance': {'percentage': attendance_pct}
        }

        # --- PDF Generation ---
        context = {'report': report, 'data': data}
        html_string = render_to_string('reports/suchitwa_mission_report.html', context)
        pdf_bytes = HTML(string=html_string).write_pdf()
        pdf_filename = f"suchitwa_mission_ward_{ward.number}_{start}.pdf"
        report.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=False)
        
        report.status = 'COMPLETED'
        report.save()

        from apps.notifications.tasks import notify_admin_report_ready
        notify_admin_report_ready.delay(report.id)
        return f"Success: {pdf_filename}"

    except Exception as e:
        logger.exception(f"Suchitwa Report generation error: {str(e)}")
        from .models import WardCollectionReport
        report = WardCollectionReport.objects.get(id=report_id)
        report.status = 'FAILED'
        report.save(update_fields=['status'])
        return f"Error: {str(e)}"
