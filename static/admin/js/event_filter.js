/**
 * Event Doctor Filtering - DEBUG VERSION
 * Adds selected specialties to doctors autocomplete requests in Django Admin.
 */
(function () {
    'use strict';
    console.log('=== Event Filter: Script Loaded ===');
    console.log('Event Filter: document.readyState =', document.readyState);

    function getSelectedSpecialtyIds(selectEl) {
        if (!selectEl) {
            console.log('Event Filter: selectEl is null/undefined');
            return [];
        }
        var ids = Array.from(selectEl.selectedOptions)
            .map(function (opt) { return opt.value; })
            .filter(Boolean);
        console.log('Event Filter: getSelectedSpecialtyIds() =', ids);
        return ids;
    }

    function shouldFilterDoctorsUrl(url) {
        var result = Boolean(
            url &&
            url.indexOf('/admin/autocomplete/') !== -1 &&
            url.indexOf('field_name=doctors') !== -1
        );
        if (url && url.indexOf('/admin/autocomplete/') !== -1) {
            console.log('Event Filter: shouldFilterDoctorsUrl("' + url + '") =', result);
        }
        return result;
    }

    function buildUrlWithSpecialties(url, specialtyIds) {
        var urlObj = new URL(url, window.location.origin);
        if (specialtyIds.length) {
            urlObj.searchParams.set('specialties_ids', specialtyIds.join(','));
        } else {
            urlObj.searchParams.delete('specialties_ids');
        }
        var newUrl = urlObj.toString();
        console.log('Event Filter: buildUrlWithSpecialties() =', newUrl);
        return newUrl;
    }

    function initDoctorFilter() {
        var specialtiesSelect = document.getElementById('id_specialties');
        var doctorsSelect = document.getElementById('id_doctors');

        console.log('=== Event Filter: initDoctorFilter() ===');
        console.log('Event Filter: #id_specialties found?', !!specialtiesSelect, specialtiesSelect ? specialtiesSelect.tagName : 'N/A');
        console.log('Event Filter: #id_doctors found?', !!doctorsSelect, doctorsSelect ? doctorsSelect.tagName : 'N/A');

        if (!specialtiesSelect || !doctorsSelect) {
            console.warn('Event Filter: ABORTED - missing specialties or doctors select element');
            return;
        }

        // Log what options are available
        console.log('Event Filter: specialties options count =', specialtiesSelect.options.length);
        console.log('Event Filter: doctors options count =', doctorsSelect.options.length);

        specialtiesSelect.addEventListener('change', function () {
            console.log('Event Filter: specialties CHANGED, new value =', Array.from(specialtiesSelect.selectedOptions).map(o => o.value + ':' + o.text));
            doctorsSelect.value = '';
            doctorsSelect.dispatchEvent(new Event('change', { bubbles: true }));
        });

        // 1) Fetch interception
        var originalFetch = window.fetch;
        console.log('Event Filter: window.fetch available?', typeof originalFetch === 'function');
        if (typeof originalFetch === 'function') {
            window.fetch = function (input, init) {
                try {
                    var rawUrl = (typeof input === 'string')
                        ? input
                        : (input instanceof Request ? input.url : '');

                    if (shouldFilterDoctorsUrl(rawUrl)) {
                        var ids = getSelectedSpecialtyIds(specialtiesSelect);
                        var nextUrl = buildUrlWithSpecialties(rawUrl, ids);
                        console.log('Event Filter [FETCH]: Intercepted! Original:', rawUrl);
                        console.log('Event Filter [FETCH]: Modified to:', nextUrl);

                        if (typeof input === 'string') {
                            input = nextUrl;
                        } else if (input instanceof Request) {
                            input = new Request(nextUrl, input);
                        }
                    }
                } catch (error) {
                    console.error('Event Filter [FETCH] ERROR:', error);
                }

                return originalFetch.call(this, input, init);
            };
            console.log('Event Filter: fetch interceptor installed ✅');
        }

        // 2) jQuery ajax interception
        var hasDjangoJQuery = !!(window.django && window.django.jQuery);
        console.log('Event Filter: django.jQuery available?', hasDjangoJQuery);
        if (hasDjangoJQuery) {
            console.log('Event Filter: django.jQuery.ajaxPrefilter available?', typeof window.django.jQuery.ajaxPrefilter === 'function');
            if (window.django.jQuery.ajaxPrefilter) {
                window.django.jQuery.ajaxPrefilter(function (options) {
                    try {
                        if (shouldFilterDoctorsUrl(options.url)) {
                            var ids = getSelectedSpecialtyIds(specialtiesSelect);
                            var newUrl = buildUrlWithSpecialties(options.url, ids);
                            console.log('Event Filter [AJAX]: Intercepted! Original:', options.url);
                            console.log('Event Filter [AJAX]: Modified to:', newUrl);
                            options.url = newUrl;
                        }
                    } catch (error) {
                        console.error('Event Filter [AJAX] ERROR:', error);
                    }
                });
                console.log('Event Filter: ajaxPrefilter interceptor installed ✅');
            }
        }

        // 3) XHR fallback interception
        var originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function (method, url) {
            try {
                if (shouldFilterDoctorsUrl(url)) {
                    var ids = getSelectedSpecialtyIds(specialtiesSelect);
                    var newUrl = buildUrlWithSpecialties(url, ids);
                    console.log('Event Filter [XHR]: Intercepted! Original:', url);
                    console.log('Event Filter [XHR]: Modified to:', newUrl);
                    url = newUrl;
                }
            } catch (error) {
                console.error('Event Filter [XHR] ERROR:', error);
            }

            return originalOpen.call(this, method, url);
        };
        console.log('Event Filter: XHR interceptor installed ✅');

        console.log('=== Event Filter: All interceptors ready ===');
    }

    if (document.readyState === 'loading') {
        console.log('Event Filter: Waiting for DOMContentLoaded...');
        document.addEventListener('DOMContentLoaded', initDoctorFilter);
    } else {
        console.log('Event Filter: DOM already ready, initializing now...');
        initDoctorFilter();
    }
})();
