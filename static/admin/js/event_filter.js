/**
 * Event Doctor Filtering
 * Adds selected specialties to doctors autocomplete requests in Django Admin.
 */
(function () {
    'use strict';

    function getSelectedSpecialtyIds(selectEl) {
        if (!selectEl) return [];
        return Array.from(selectEl.selectedOptions)
            .map(function (opt) { return opt.value; })
            .filter(Boolean);
    }

    function shouldFilterDoctorsUrl(url) {
        return Boolean(
            url &&
            url.indexOf('/admin/autocomplete/') !== -1 &&
            url.indexOf('app_label=accounts') !== -1 &&
            url.indexOf('model_name=doctor') !== -1
        );
    }

    function buildUrlWithSpecialties(url, specialtyIds) {
        var urlObj = new URL(url, window.location.origin);

        if (specialtyIds.length) {
            urlObj.searchParams.set('specialties_ids', specialtyIds.join(','));
        } else {
            // No specialty selected => backend should return all doctors.
            urlObj.searchParams.delete('specialties_ids');
        }

        return urlObj.toString();
    }

    function initDoctorFilter() {
        var specialtiesSelect = document.getElementById('id_specialties');
        var doctorsSelect = document.getElementById('id_doctors');

        if (!specialtiesSelect || !doctorsSelect) return;

        specialtiesSelect.addEventListener('change', function () {
            // Clear currently selected doctors whenever specialties change.
            doctorsSelect.value = '';
            doctorsSelect.dispatchEvent(new Event('change', { bubbles: true }));
        });

        // 1) Fetch interception (for modern admin integrations).
        var originalFetch = window.fetch;
        if (typeof originalFetch === 'function') {
            window.fetch = function (input, init) {
                try {
                    var rawUrl = (typeof input === 'string')
                        ? input
                        : (input instanceof Request ? input.url : '');

                    if (shouldFilterDoctorsUrl(rawUrl)) {
                        var ids = getSelectedSpecialtyIds(specialtiesSelect);
                        var nextUrl = buildUrlWithSpecialties(rawUrl, ids);

                        if (typeof input === 'string') {
                            input = nextUrl;
                        } else if (input instanceof Request) {
                            input = new Request(nextUrl, input);
                        }
                    }
                } catch (error) {
                    console.error('Event Filter (fetch):', error);
                }

                return originalFetch.call(this, input, init);
            };
        }

        // 2) jQuery ajax interception (used by Django Admin Select2).
        if (window.django && window.django.jQuery && window.django.jQuery.ajaxPrefilter) {
            window.django.jQuery.ajaxPrefilter(function (options) {
                try {
                    if (shouldFilterDoctorsUrl(options.url)) {
                        var ids = getSelectedSpecialtyIds(specialtiesSelect);
                        options.url = buildUrlWithSpecialties(options.url, ids);
                    }
                } catch (error) {
                    console.error('Event Filter (ajax):', error);
                }
            });
        }

        // 3) XHR fallback interception.
        var originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function (method, url) {
            try {
                if (shouldFilterDoctorsUrl(url)) {
                    var ids = getSelectedSpecialtyIds(specialtiesSelect);
                    url = buildUrlWithSpecialties(url, ids);
                }
            } catch (error) {
                console.error('Event Filter (xhr):', error);
            }

            return originalOpen.call(this, method, url);
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDoctorFilter);
    } else {
        initDoctorFilter();
    }
})();
