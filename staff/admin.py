from django.contrib import admin

from .models import Attendance, StaffBreak, StaffMember

for m in (StaffMember, Attendance, StaffBreak):
    admin.site.register(m)
