/**
 * SmartPrintKiosk - Master Frontend JavaScript
 * Handles dynamic price calculation, form interactions, and live status polling.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss Bootstrap alert messages after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 6000);
    });

    // 2. Dynamic Price Calculator for Print Preferences Page
    initPriceCalculator();

    // 3. Live Order Tracking Status Poller
    initLiveTrackingPoller();
});

/**
 * Initializes interactive price estimation on the preferences page.
 */
function initPriceCalculator() {
    const preferencesForm = document.getElementById('printPreferencesForm');
    if (!preferencesForm) return;

    const uploadToken = preferencesForm.dataset.uploadToken;
    const customRangeWrapper = document.getElementById('customRangeWrapper');
    const customRangeInput = document.getElementById('customRangeInput');
    const copiesInput = document.getElementById('copiesInput');
    const pageModeRadios = document.querySelectorAll('input[name="page_selection_mode"]');

    // UI elements to update
    const displayTotal = document.getElementById('displayTotalAmount');
    const displaySubtotal = document.getElementById('displaySubtotal');
    const displayDiscount = document.getElementById('displayDiscount');
    const displayPagesPerCopy = document.getElementById('displayPagesPerCopy');
    const displayTotalPrinted = document.getElementById('displayTotalPrinted');
    const displaySheetsUsed = document.getElementById('displaySheetsUsed');
    const displayRate = document.getElementById('displayRatePerPage');
    const priceErrorAlert = document.getElementById('priceErrorAlert');

    function toggleCustomRange() {
        const isCustom = document.querySelector('input[name="page_selection_mode"]:checked')?.value === 'CUSTOM';
        if (customRangeWrapper) {
            customRangeWrapper.style.display = isCustom ? 'block' : 'none';
        }
    }

    function fetchPriceEstimate() {
        if (!uploadToken) return;

        const formData = new FormData(preferencesForm);
        const params = new URLSearchParams();

        for (const [key, value] of formData.entries()) {
            params.append(key, value);
        }

        fetch(`/api/price/${uploadToken}/?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (priceErrorAlert) priceErrorAlert.classList.add('d-none');
                    if (displayTotal) displayTotal.innerText = '₹' + parseFloat(data.total_amount).toFixed(2);
                    if (displaySubtotal) displaySubtotal.innerText = '₹' + parseFloat(data.subtotal).toFixed(2);
                    if (displayDiscount) displayDiscount.innerText = '-₹' + parseFloat(data.discount).toFixed(2);
                    if (displayPagesPerCopy) displayPagesPerCopy.innerText = data.pages_per_copy;
                    if (displayTotalPrinted) displayTotalPrinted.innerText = data.total_pages_printed;
                    if (displaySheetsUsed) displaySheetsUsed.innerText = data.total_sheets;
                    if (displayRate) displayRate.innerText = '₹' + parseFloat(data.rate_per_page).toFixed(2);
                } else {
                    if (priceErrorAlert) {
                        priceErrorAlert.innerText = data.error || 'Invalid print options entered.';
                        priceErrorAlert.classList.remove('d-none');
                    }
                }
            })
            .catch(err => {
                console.warn('Price calculation fetch error:', err);
            });
    }

    // Attach listeners
    preferencesForm.addEventListener('change', function () {
        toggleCustomRange();
        fetchPriceEstimate();
    });

    if (customRangeInput) {
        customRangeInput.addEventListener('input', debounce(fetchPriceEstimate, 400));
    }

    if (copiesInput) {
        copiesInput.addEventListener('input', debounce(fetchPriceEstimate, 300));
    }

    // Initial run
    toggleCustomRange();
}

/**
 * Live poll order tracking status every 3.5 seconds until ready or completed.
 */
function initLiveTrackingPoller() {
    const trackingContainer = document.getElementById('liveTrackingContainer');
    if (!trackingContainer) return;

    const token = trackingContainer.dataset.token;
    const statusBadge = document.getElementById('orderStatusBadge');
    const jobBadge = document.getElementById('jobStatusBadge');
    const readyAlert = document.getElementById('orderReadyAlert');

    if (!token) return;

    let pollInterval = setInterval(() => {
        fetch(`/api/status/${token}/`)
            .then(res => res.json())
            .then(data => {
                if (statusBadge) {
                    statusBadge.innerText = data.order_status_display;
                    statusBadge.className = `badge fs-5 px-3 py-2 badge-status-${data.order_status.toLowerCase()}`;
                }
                if (jobBadge && data.job_status) {
                    jobBadge.innerText = 'Print Queue: ' + data.job_status;
                }
                if (data.is_ready && readyAlert) {
                    readyAlert.classList.remove('d-none');
                }
                if (data.is_completed) {
                    clearInterval(pollInterval);
                }
            })
            .catch(err => console.warn('Status poll error:', err));
    }, 3500);
}

/**
 * Simple debounce utility to prevent flooding server requests on keystrokes.
 */
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
