from django import forms
from .models import JobOrder


class JobOrderForm(forms.ModelForm):
    class Meta:
        model = JobOrder
        fields = [
            'customer_name',
            'phone',
            'email',
            'company',
            'delivery_address',
            'product_service',
            'title_description',
            'quantity',
            'size_dimension',
            'color_mode',
            'paper_type',
            'paper_weight',
            'binding',
            'lamination',
            'total_pages',
            'design_needed',
            'design_concepts',
            'design_style',
            'font_type',
            'font_size',
            'line_spacing',
            'isbn_required',
            'special_instructions',
            'delivery_mode',
            'expected_delivery_date',
            'urgency_level',
            'source_of_deal',
            'estimated_budget',
            'agreed_amount',
            'part_payment',
            'balance_due',
            'invoice_file',
            'manuscript_file',
        ]
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
            'special_instructions': forms.Textarea(attrs={'rows': 4}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'estimated_budget': forms.NumberInput(attrs={'step': '0.01'}),
            'agreed_amount': forms.NumberInput(attrs={'step': '0.01'}),
            'part_payment': forms.NumberInput(attrs={'step': '0.01'}),
            'balance_due': forms.NumberInput(attrs={'step': '0.01'}),
        }
        labels = {
            'title_description': 'Product Title / Description',
            'company': 'Company / Organization',
            'delivery_address': 'Delivery Address',
            'design_needed': 'Design Service Needed?',
            'expected_delivery_date': 'Expected Delivery Date',
            'urgency_level': 'Urgency Level',
            'source_of_deal': 'Source of Deal',
            'estimated_budget': 'Estimated Budget (₦)',
            'agreed_amount': 'Agreed Amount (₦)',
            'part_payment': 'Part Payment (₦)',
            'balance_due': 'Balance Due (₦)',
        }
