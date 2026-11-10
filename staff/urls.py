from django.urls import path

from . import views

urlpatterns = [
    path("api/staff/", views.staff_list),
    path("api/staff/me/", views.me),
    path("api/staff/create/", views.staff_create),
    path("api/staff/<int:pk>/", views.staff_detail),
    path("api/staff/<int:pk>/update/", views.staff_update),
    path("api/staff/<int:pk>/delete/", views.staff_delete),
    path("api/staff/<int:pk>/shift/", views.staff_shift),
    path("api/staff/<int:pk>/shift-schedule/", views.staff_schedule),
    path("api/staff/<int:pk>/role/", views.staff_role),
    path("staff/attendance/", views.attendance_list),
    path("staff/attendance/clock-in/", views.clock_in),
    path("staff/attendance/clock-out/", views.clock_out),
    path("staff/attendance/<int:pk>/", views.attendance_edit),
    path("staff/breaks/", views.breaks_list),
    path("staff/break/start/", views.break_start),
    path("staff/break/end/", views.break_end),
]
