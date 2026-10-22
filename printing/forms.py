"""
printing/forms.py
=================
Forms for document upload, print options configuration, guest order tracking,
and shop owner pricing/settings administration.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Document, PrintOrder, Shop, PricingSetting
from .validators import validate_uploaded_document, detect_document_page_count
from .pricing import parse_page_range


class DocumentUploadForm(forms.Form):
    """
    Step 1 Form: File upload with customer contact info.
    """
    document_file = forms.FileField(
        label="Select Document to Print",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control form-control-lg',
            'id': 'documentFileInput',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
        }),
        help_text="Supported formats: PDF, Word (.docx, .doc), Images (.jpg, .png). Maximum 15 MB."
    )
    customer_name = forms.CharField(
        label="Your Name (Optional)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. John Doe'
        }),
        help_text="Used to label your printed document package."
    )
    customer_phone = forms.CharField(
        label="Phone Number (Optional)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 9876543210'
        }),
        help_text="For pickup verification and tracking."
    )

    def clean_document_file(self):
        uploaded_file = self.cleaned_data.get('document_file')
        if not uploaded_file:
            raise ValidationError("Please select a file to upload.")

        # Runs extension, size, and header signature checks
        file_type = validate_uploaded_document(uploaded_file)
        self.cleaned_data['file_type'] = file_type
        return uploaded_file


class PrintPreferencesForm(forms.Form):
    """
    Step 2 Form: Print preferences configuration.
    Allows customer to select B&W/Color, copies, page range, duplex, and orientation.
    """
    color_mode = forms.ChoiceField(
        label="Color Option",
        choices=PrintOrder.COLOR_CHOICES,
        initial=PrintOrder.COLOR_BW,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
    )
    copies = forms.IntegerField(
        label="Number of Copies",
        min_value=1,
        max_value=50,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center fs-5 fw-bold',
            'min': '1',
            'max': '50',
            'id': 'copiesInput'
        })
    )
    page_selection_mode = forms.ChoiceField(
        label="Page Range",
        choices=PrintOrder.PAGE_MODE_CHOICES,
        initial=PrintOrder.PAGE_MODE_ALL,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    custom_page_range = forms.CharField(
        label="Specify Page Range",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 1-3, 5, 8',
            'id': 'customRangeInput'
        }),
        help_text="Example: '1-3, 5' prints pages 1, 2, 3, and 5."
    )
    duplex_mode = forms.ChoiceField(
        label="Sides",
        choices=PrintOrder.DUPLEX_CHOICES,
        initial=PrintOrder.DUPLEX_SINGLE,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'})
    )
    orientation = forms.ChoiceField(
        label="Orientation",
        choices=PrintOrder.ORIENT_CHOICES,
        initial=PrintOrder.ORIENT_PORTRAIT,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'})
    )

    def __init__(self, *args, total_pages=1, max_copies=50, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_pages = total_pages
        self.max_copies = max_copies
        self.fields['copies'].max_value = max_copies

    def clean(self):
        cleaned_data = super().clean()
        page_mode = cleaned_data.get('page_selection_mode')
        custom_range = cleaned_data.get('custom_page_range')
        copies = cleaned_data.get('copies') or 1

        if copies > self.max_copies:
            self.add_error('copies', f"The shop allows maximum {self.max_copies} copies per order.")

        if page_mode == PrintOrder.PAGE_MODE_CUSTOM:
            if not custom_range or not custom_range.strip():
                self.add_error('custom_page_range', "Please enter the page numbers or ranges to print.")
            else:
                try:
                    # Validate and parse range against actual document pages
                    pages = parse_page_range(custom_range, self.total_pages)
                    cleaned_data['parsed_pages'] = pages
                    cleaned_data['calculated_pages_per_copy'] = len(pages)
                except ValueError as exc:
                    self.add_error('custom_page_range', str(exc))
        else:
            cleaned_data['calculated_pages_per_copy'] = self.total_pages

        return cleaned_data


class GuestOrderLookupForm(forms.Form):
    """
    Search form for guest customers to track their order using Order ID.
    """
    order_number = forms.CharField(
        label="Order Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-uppercase',
            'placeholder': 'SPK-YYYYMMDD-XXXXXX'
        }),
        help_text="Find this on your payment confirmation screen."
    )


class PricingSettingsForm(forms.ModelForm):
    """
    Dashboard form for the shop owner to adjust pricing rates and policies.
    """
    class Meta:
        model = PricingSetting
        fields = ['bw_rate_per_page', 'color_rate_per_page', 'duplex_discount_per_sheet', 'max_copies_limit']
        widgets = {
            'bw_rate_per_page': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'color_rate_per_page': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50'}),
            'duplex_discount_per_sheet': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10'}),
            'max_copies_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '200'}),
        }


class ShopSettingsForm(forms.ModelForm):
    """
    Dashboard form for basic shop details and physical printer configuration.
    """
    class Meta:
        model = Shop
        fields = ['name', 'address', 'contact_number', 'contact_email', 'configured_printer_name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'configured_printer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. HP LaserJet Pro M404'
            }),
        }
