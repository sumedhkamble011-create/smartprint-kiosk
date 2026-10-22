"""
printing/pricing.py
===================
Server-side pricing engine for SmartPrintKiosk.

Why this is needed:
Never trust a price calculated in JavaScript on the browser!
Browsers can be manipulated. All financial computations MUST be strictly
calculated, validated, and rounded on the server using Python's Decimal type.

Pricing Formula:
1. Base Rate:
   - Black & White: ₹2.00 / printed side (configurable per shop)
   - Colour:        ₹10.00 / printed side (configurable per shop)
2. Pages selected:
   - 'ALL': all pages of the document
   - 'CUSTOM': specific pages parsed (e.g., '1-3, 5' = 4 pages)
3. Total Printed Sides:
   - total_pages_printed = pages_per_copy * copies
4. Duplex (Double-sided) Sheets:
   - In Single-Sided: sheets_used = pages_per_copy * copies
   - In Double-Sided: sheets_used = ceil(pages_per_copy / 2) * copies
   - Sheets saved = (pages_per_copy * copies) - sheets_used
   - If duplex discount is configured: discount = sheets_saved * duplex_discount_per_sheet
5. Final Price:
   - Subtotal = total_pages_printed * rate_per_page
   - Total = max(0.00, Subtotal - discount)
"""

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any


def parse_page_range(range_str: str, max_pages: int) -> list:
    """
    Parses a user-entered page range string like '1-3, 5, 8-10' and returns
    a sorted unique list of valid 1-based page numbers.

    Raises ValueError if range is malformed or exceeds max_pages.
    """
    if not range_str or not range_str.strip():
        # Default to all pages
        return list(range(1, max_pages + 1))

    selected_pages = set()
    parts = range_str.split(',')

    for raw_part in parts:
        part = raw_part.strip()
        if not part:
            continue

        if '-' in part:
            bounds = part.split('-')
            if len(bounds) != 2:
                raise ValueError(f"Invalid page range token: '{part}'. Format should be like '1-5'.")
            try:
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
            except ValueError:
                raise ValueError(f"Invalid page numbers in range: '{part}'. Numbers must be integers.")

            if start < 1:
                raise ValueError(f"Page numbers must be 1 or greater. Found: {start}.")
            if start > end:
                raise ValueError(f"Start page {start} cannot be greater than end page {end}.")
            if max_pages and end > max_pages:
                raise ValueError(f"Page {end} exceeds the document's total of {max_pages} pages.")

            for p in range(start, end + 1):
                selected_pages.add(p)
        else:
            try:
                p = int(part)
            except ValueError:
                raise ValueError(f"Invalid page number: '{part}'. Must be an integer.")

            if p < 1:
                raise ValueError(f"Page number must be 1 or greater. Found: {p}.")
            if max_pages and p > max_pages:
                raise ValueError(f"Page {p} exceeds the document's total of {max_pages} pages.")

            selected_pages.add(p)

    if not selected_pages:
        raise ValueError("No valid pages were specified in the custom range.")

    return sorted(list(selected_pages))


def calculate_print_price(
    pricing_setting,
    total_document_pages: int,
    color_mode: str = 'BW',
    copies: int = 1,
    page_selection_mode: str = 'ALL',
    custom_page_range: str = '',
    duplex_mode: str = 'SINGLE'
) -> Dict[str, Any]:
    """
    Computes full price breakdown and returns a dictionary with Decimal values.
    """
    # 1. Validate copies
    if copies < 1:
        copies = 1
    max_copies = getattr(pricing_setting, 'max_copies_limit', 50)
    if copies > max_copies:
        raise ValueError(f"Number of copies exceeds shop maximum limit of {max_copies}.")

    # 2. Determine pages per copy
    if page_selection_mode == 'CUSTOM' and custom_page_range:
        selected_pages = parse_page_range(custom_page_range, total_document_pages)
        pages_per_copy = len(selected_pages)
    else:
        pages_per_copy = max(1, total_document_pages)

    # 3. Rate determination
    if color_mode == 'COLOR':
        rate_per_page = Decimal(str(pricing_setting.color_rate_per_page))
        mode_label = "Colour Printing"
    else:
        rate_per_page = Decimal(str(pricing_setting.bw_rate_per_page))
        mode_label = "Black & White (B&W)"

    # 4. Total printed sides
    total_pages_printed = pages_per_copy * copies
    subtotal = (Decimal(total_pages_printed) * rate_per_page).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # 5. Sheet calculations and duplex discount
    if duplex_mode == 'DOUBLE':
        sheets_per_copy = math.ceil(pages_per_copy / 2)
        total_sheets = sheets_per_copy * copies
        sheets_saved = (pages_per_copy * copies) - total_sheets

        duplex_discount_rate = getattr(pricing_setting, 'duplex_discount_per_sheet', Decimal('0.00'))
        discount = (Decimal(sheets_saved) * Decimal(str(duplex_discount_rate))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    else:
        total_sheets = total_pages_printed
        sheets_saved = 0
        discount = Decimal('0.00')

    # 6. Final total
    total_amount = max(Decimal('1.00'), subtotal - discount).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    return {
        'color_mode': color_mode,
        'mode_label': mode_label,
        'rate_per_page': rate_per_page,
        'pages_per_copy': pages_per_copy,
        'copies': copies,
        'total_pages_printed': total_pages_printed,
        'duplex_mode': duplex_mode,
        'total_sheets': total_sheets,
        'sheets_saved': sheets_saved,
        'subtotal': subtotal,
        'discount': discount,
        'total_amount': total_amount,
    }
