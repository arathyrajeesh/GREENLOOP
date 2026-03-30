from celery import shared_task
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
import logging
try:
    from weasyprint import HTML
except ImportError:
    HTML = None

from .models import RecyclingCertificate

logger = logging.getLogger(__name__)

@shared_task
def generate_recycling_certificate_pdf(certificate_id):
    """
    Generates a PDF for a RecyclingCertificate using WeasyPrint.
    """
    if HTML is None:
        logger.error("WeasyPrint is not installed. PDF generation failed.")
        return "WeasyPrint not installed"

    try:
        certificate = RecyclingCertificate.objects.get(id=certificate_id)
        
        # Calculate total weight (assuming all units are normalized or just sum quantity)
        total_weight = sum(p.quantity for p in certificate.purchases.all())
        
        # Context for template
        context = {
            'certificate': certificate,
            'total_weight': total_weight
        }
        
        # Render to HTML template
        html_string = render_to_string('recyclers/certificate.html', context)
        
        # Convert HTML to PDF
        pdf_bytes = HTML(string=html_string).write_pdf()
        
        # Save the generated PDF file to the model
        filename = f"certificate_{certificate.certificate_number}.pdf"
        certificate.certificate_file.save(filename, ContentFile(pdf_bytes), save=False)
        certificate.save()
        
        logger.info(f"Successfully generated PDF for certificate {certificate.certificate_number}")
        return f"Success: {filename}"
        
    except RecyclingCertificate.DoesNotExist:
        logger.error(f"Certificate {certificate_id} not found.")
        return "Certificate not found"
    except Exception as e:
        logger.exception(f"PDF generation error for cert {certificate_id}: {str(e)}")
        return f"Error: {str(e)}"
