from celery import shared_task
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.db.models import Count, Sum
import logging
import csv
import io
try:
    from weasyprint import HTML
except ImportError:
    HTML = None

from .models import WardCollectionReport

logger = logging.getLogger(__name__)

@shared_task
def generate_ward_collection_report(report_id):
    if HTML is None:
        logger.error("WeasyPrint is not installed. PDF generation failed.")
        return "WeasyPrint not installed"

    try:
        report = WardCollectionReport.objects.select_related('ward', 'generated_by').get(id=report_id)
        report.status = 'PENDING' # Ensure it starts as pending
        report.save(update_fields=['status'])

        ward = report.ward
        start = report.start_date
        end = report.end_date

        from apps.pickups.models import Pickup
        from apps.recyclers.models import RecyclerPurchase
        from apps.payments.models import FeeCollection
        from apps.complaints.models import Complaint

        # 1. Pickups Data
        pickups = Pickup.objects.filter(
            ward=ward, scheduled_date__range=[start, end]
        ).values('status').annotate(count=Count('id'))
        pickups_by_status = {p['status']: p['count'] for p in pickups}

        # 2. Material/Waste Data
        waste_data = RecyclerPurchase.objects.filter(
            source_ward=ward, purchase_date__date__range=[start, end]
        ).values('material_type__name').annotate(total_qty=Sum('weight_kg'))

        # 3. Financial Data
        fees_qs = FeeCollection.objects.filter(
            ward=ward, payment_date__date__range=[start, end]
        ).aggregate(total=Sum('amount'))
        total_fees = fees_qs['total'] or 0.0

        # 4. Complaints Data
        complaints_qs = Complaint.objects.filter(
            reporter__ward=ward, created_at__date__range=[start, end]
        ).values('category').annotate(count=Count('id'))
        
        # Combine data for context
        report_data = {
            'pickups_by_status': pickups_by_status,
            'waste_by_material': list(waste_data),
            'total_fees': total_fees,
            'complaints_by_category': list(complaints_qs)
        }

        # --- Generate CSV ---
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['Metric', 'Category/Status/Type', 'Value'])
        
        for status, count in pickups_by_status.items():
            csv_writer.writerow(['Pickup', status.title(), count])
            
        for w in waste_data:
            csv_writer.writerow(['Waste Collected (kg)', w['material_type__name'], w['total_qty']])
            
        csv_writer.writerow(['Financial', 'Total Fees (INR)', total_fees])
        
        for c in complaints_qs:
            csv_writer.writerow(['Complaint', c['category'], c['count']])
            
        csv_filename = f"ward_{ward.number}_report_{start}_{end}.csv"
        report.csv_file.save(csv_filename, ContentFile(csv_buffer.getvalue().encode('utf-8')), save=False)

        # --- Generate PDF ---
        context = {
            'report': report,
            'data': report_data
        }
        html_string = render_to_string('reports/ward_report.html', context)
        pdf_bytes = HTML(string=html_string).write_pdf()
        
        pdf_filename = f"ward_{ward.number}_report_{start}_{end}.pdf"
        report.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=False)
        
        # Update Status
        report.status = 'COMPLETED'
        report.save()

        # Notify Admin
        from apps.notifications.tasks import notify_admin_report_ready
        notify_admin_report_ready.delay(report.id)

        return f"Success: {pdf_filename}"

    except Exception as e:
        logger.exception(f"Report generation error for {report_id}: {str(e)}")
        report = WardCollectionReport.objects.get(id=report_id)
        report.status = 'FAILED'
        report.save(update_fields=['status'])
        return f"Error: {str(e)}"
