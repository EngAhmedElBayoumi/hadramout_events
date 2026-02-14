from django.contrib.admin.apps import AdminConfig

class HandramoutAdminConfig(AdminConfig):
    default_site = 'core.admin_site.HandramoutAdminSite'
