/**
 * Event Doctor Filtering (Native JS)
 * Intercepts Fetch API calls to append specialties_ids to the doctors autocomplete request.
 */
(function () {
    'use strict';

    function initDoctorFilter() {
        const specialtiesSelect = document.getElementById('id_specialties');
        const doctorsSelect = document.getElementById('id_doctors');

        if (!specialtiesSelect || !doctorsSelect) return;

        // Reset doctors selection when specialties change
        specialtiesSelect.addEventListener('change', function () {
            // Trigger a change to clear the Select2 internal state
            // Native way for Select2 to notice:
            doctorsSelect.value = '';
            const event = new Event('change', { bubbles: true });
            doctorsSelect.dispatchEvent(event);
            console.log('Event Filter: Specialties changed, cleared doctors');
        });

        // Intercept Fetch API
        const originalFetch = window.fetch;
        window.fetch = function (input, init) {
            let url = (typeof input === 'string') ? input : (input instanceof Request ? input.url : null);

            if (url && url.includes('/admin/autocomplete/') && url.includes('model_name=doctor') && url.includes('app_label=accounts')) {
                try {
                    const urlObj = new URL(url, window.location.origin);
                    const selectedOptions = Array.from(specialtiesSelect.selectedOptions).map(opt => opt.value);

                    if (selectedOptions.length > 0) {
                        urlObj.searchParams.set('specialties_ids', selectedOptions.join(','));
                        const newUrl = urlObj.toString();
                        console.log('Event Filter: Appending specialties_ids to:', newUrl);

                        // Handle the different types of input to fetch
                        if (typeof input === 'string') {
                            input = newUrl;
                        } else if (input instanceof Request) {
                            // Request objects are immutable in some contexts, so we create a new one
                            input = new Request(newUrl, input);
                        }
                    } else {
                        // Clear param if no specialties selected
                        urlObj.searchParams.delete('specialties_ids');
                        if (typeof input === 'string') {
                            input = urlObj.toString();
                        } else if (input instanceof Request) {
                            input = new Request(urlObj.toString(), input);
                        }
                    }
                } catch (e) {
                    console.error('Event Filter: Error modifying fetch URL', e);
                }
            }
            return originalFetch.call(this, input, init);
        };

        console.log('Event Filter: Fetch API Interception Initialized');
    }

    // Wait for the document to be ready and for Django Admin's potential late-init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDoctorFilter);
    } else {
        initDoctorFilter();
    }
})();
