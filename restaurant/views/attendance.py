# -----restaurant/views/attendance.py

from rest_framework import status

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework.views import APIView

from restaurant.serializers import (
    
    StaffAttendanceSerializer,
    
    AttendanceClockInSerializer,
    
    AttendanceClockOutSerializer,
    
    StaffAttendanceUpdateSerializer,
    
)

from restaurant.services.attendance import (
    
    clock_in_staff,
    
    clock_out_staff,
    
    get_staff_attendance,
    
    update_staff_attendance,
    
)

from restaurant.services.common import get_restaurant


# ==========================================================
# Staff Attendance API
# ==========================================================

class StaffAttendanceAPIView(APIView):
    """
    List staff attendance.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        staff_id = request.query_params.get("staff_id")

        attendance_date = request.query_params.get(
            "attendance_date"
        )

        attendance = get_staff_attendance(
            restaurant=restaurant,
            staff_id=staff_id,
            attendance_date=attendance_date,
        )

        serializer = StaffAttendanceSerializer(
            attendance,
            many=True,
        )

        return Response(serializer.data)

# ==========================================================
# Staff Clock In API
# ==========================================================

class StaffClockInAPIView(APIView):
    """
    Clock in a staff member.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = get_restaurant(request)

        serializer = AttendanceClockInSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        attendance = clock_in_staff(
            restaurant=restaurant,
            staff_id=serializer.validated_data["staff_id"],
        )

        return Response(
            StaffAttendanceSerializer(
                attendance
            ).data,
            status=status.HTTP_200_OK,
        )

# ==========================================================
# Staff Clock Out API
# ==========================================================

class StaffClockOutAPIView(APIView):
    """
    Clock out a staff member.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = get_restaurant(request)

        serializer = AttendanceClockOutSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        attendance = clock_out_staff(
            restaurant=restaurant,
            staff_id=serializer.validated_data["staff_id"],
        )

        return Response(
            StaffAttendanceSerializer(
                attendance
            ).data,
            status=status.HTTP_200_OK,
        )

# ==========================================================
# Staff Attendance Update API
# ==========================================================

class StaffAttendanceUpdateAPIView(APIView):
    """
    Update attendance record.
    """

    permission_classes = [IsAuthenticated]

    def patch(
        self,
        request,
        attendance_id,
    ):

        restaurant = get_restaurant(request)

        serializer = StaffAttendanceUpdateSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        attendance = update_staff_attendance(
            restaurant=restaurant,
            attendance_id=attendance_id,
            **serializer.validated_data,
        )

        return Response(
            StaffAttendanceSerializer(attendance).data,
            status=status.HTTP_200_OK,
        )
        
        
        
