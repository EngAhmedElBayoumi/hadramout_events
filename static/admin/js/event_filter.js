/**
 * Event Doctor Filtering & Delegates Company Filtering
 * Adds selected specialties to doctors autocomplete requests in Django Admin.
 * Intercepts delegates autocomplete requests and routes them to a custom API.
 */
(function () {
    'use strict';
    console.log('=== Event Filter: Script Loaded ===');

    // --- DOCTORS FILTERING ---
    function getSelectedSpecialtyIds(selectEl) {
        if (!selectEl) return [];
        return Array.from(selectEl.selectedOptions).map(opt => opt.value).filter(Boolean);
    }

    function shouldFilterDoctorsUrl(url) {
        return Boolean(url && url.indexOf('/admin/autocomplete/') !== -1 && url.indexOf('field_name=doctors') !== -1);
    }

    function buildUrlWithSpecialties(url, specialtyIds) {
        var urlObj = new URL(url, window.location.origin);
        if (specialtyIds.length) {
            urlObj.searchParams.set('specialties_ids', specialtyIds.join(','));
        } else {
            urlObj.searchParams.delete('specialties_ids');
        }
        return urlObj.toString();
    }

    // --- DELEGATES FILTERING ---
    function shouldFilterDelegatesUrl(url) {
        return Boolean(url && url.indexOf('/admin/autocomplete/') !== -1 && url.indexOf('field_name=delegates') !== -1);
    }

    function rerouteDelegatesUrl(originalUrl, originalData) {
        var companySelect = document.getElementById('id_company');
        var companyId = companySelect ? companySelect.value : '';
        
        var urlObj = new URL(originalUrl, window.location.origin);
        var term = urlObj.searchParams.get('term') || urlObj.searchParams.get('q') || '';
        
        if (!term && originalData && typeof originalData === 'string') {
            var dataParams = new URLSearchParams(originalData);
            term = dataParams.get('term') || dataParams.get('q') || '';
        }
        
        return '/api/admin/company-delegates/?company_id=' + encodeURIComponent(companyId) + '&term=' + encodeURIComponent(term);
    }

    function initDoctorFilter() {
        var specialtiesSelect = document.getElementById('id_specialties');
        var doctorsSelect = document.getElementById('id_doctors');

        if (specialtiesSelect && doctorsSelect) {
            specialtiesSelect.addEventListener('change', function () {
                doctorsSelect.value = '';
                doctorsSelect.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        // 1) Fetch interception
        var originalFetch = window.fetch;
        if (typeof originalFetch === 'function') {
            window.fetch = function (input, init) {
                try {
                    var rawUrl = (typeof input === 'string') ? input : (input instanceof Request ? input.url : '');
                    
                    if (shouldFilterDoctorsUrl(rawUrl)) {
                        var ids = getSelectedSpecialtyIds(document.getElementById('id_specialties'));
                        var nextUrl = buildUrlWithSpecialties(rawUrl, ids);
                        if (typeof input === 'string') input = nextUrl;
                        else if (input instanceof Request) input = new Request(nextUrl, input);
                    } else if (shouldFilterDelegatesUrl(rawUrl)) {
                        var nextUrl = rerouteDelegatesUrl(rawUrl, init ? init.body : null);
                        if (typeof input === 'string') input = nextUrl;
                        else if (input instanceof Request) input = new Request(nextUrl, input);
                    }
                } catch (e) { console.error('Event Filter [FETCH] ERR:', e); }
                return originalFetch.apply(this, arguments);
            };
        }

        // 2) jQuery ajax interception
        if (window.django && window.django.jQuery && window.django.jQuery.ajaxPrefilter) {
            window.django.jQuery.ajaxPrefilter(function (options) {
                try {
                    if (shouldFilterDoctorsUrl(options.url)) {
                        var ids = getSelectedSpecialtyIds(document.getElementById('id_specialties'));
                        options.url = buildUrlWithSpecialties(options.url, ids);
                    } else if (shouldFilterDelegatesUrl(options.url)) {
                        options.url = rerouteDelegatesUrl(options.url, options.data);
                        // Prevent term duplication in body
                        if (typeof options.data === 'string') {
                             var dataParams = new URLSearchParams(options.data);
                             dataParams.delete('term');
                             dataParams.delete('q');
                             options.data = dataParams.toString();
                        }
                    }
                } catch (e) { console.error('Event Filter [AJAX] ERR:', e); }
            });
        }

        // 3) XHR fallback interception
        var originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function (method, url) {
            try {
                if (shouldFilterDoctorsUrl(url)) {
                    var ids = getSelectedSpecialtyIds(document.getElementById('id_specialties'));
                    url = buildUrlWithSpecialties(url, ids);
                } else if (shouldFilterDelegatesUrl(url)) {
                    url = rerouteDelegatesUrl(url, null);
                }
            } catch (e) { console.error('Event Filter [XHR] ERR:', e); }
            return originalOpen.call(this, method, url);
        };
    }

    // --- DELEGATE -> SPECIALTY ASSIGNMENT (AUTO-ADD) ---
    function initCompanyDelegateFilter() {
        console.log('=== Event Filter: initCompanyDelegateFilter() ===');
        const delegatesAutocomplete = document.getElementById('id_delegates');
        const $jq = window.jQuery || (window.django && window.django.jQuery);
        
        if (delegatesAutocomplete && $jq) {
            console.log('Event Filter: Attached listener to Select2 delegates');
            $jq(delegatesAutocomplete).on('change', function() {
                const delegateIds = $jq(this).val();
                if (delegateIds && delegateIds.length > 0) {
                    const params = new URLSearchParams();
                    let idsArray = Array.isArray(delegateIds) ? delegateIds : [delegateIds];
                    idsArray.forEach(id => params.append('delegate_ids[]', id));
                    
                    fetch('/api/admin/delegate-specialties/?' + params.toString())
                        .then(res => res.json())
                        .then(data => {
                            const specAutocomplete = $jq('#id_specialties');
                            if (specAutocomplete.length && data.specialties) {
                                let changed = false;
                                const currentVals = specAutocomplete.val() || [];
                                
                                data.specialties.forEach(spec => {
                                    const specIdStr = String(spec.id);
                                    if (currentVals.indexOf(specIdStr) === -1) {
                                        if (specAutocomplete.find("option[value='" + specIdStr + "']").length) {
                                            specAutocomplete.find("option[value='" + specIdStr + "']").prop("selected", true);
                                        } else {
                                            const newOption = new Option(spec.text, spec.id, true, true);
                                            specAutocomplete.append(newOption);
                                        }
                                        changed = true;
                                    }
                                });
                                if (changed) {
                                    specAutocomplete.trigger('change');
                                }
                            }
                        })
                        .catch(err => console.error("Error fetching specialties:", err));
                }
            });
        } else {
             console.warn('Event Filter: delegatesAutocomplete or jQuery not found for auto-add specialties');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initDoctorFilter();
            initCompanyDelegateFilter();
        });
    } else {
        initDoctorFilter();
        initCompanyDelegateFilter();
    }
})();
