from rest_framework import serializers
from .models import ReportCategory, Report, WardCollectionReport

class ReportCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCategory
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class WardCollectionReportSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.name', read_only=True)

    class Meta:
        model = WardCollectionReport
        fields = '__all__'
        read_only_fields = ['status', 'pdf_file', 'csv_file', 'generated_by', 'created_at']
