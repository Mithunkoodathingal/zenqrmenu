# -----restaurant/views/staff.py

# =============================================================================
# Imports
# =============================================================================

from datetime import timezone

from rest_framework import status
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.response import Response
from restaurant.services.common import get_restaurant
from restaurant.services.staff import (
    clock_in,
    clock_out,
    get_staff_role,
    start_break,
    end_break,
    update_staff_role,
)
from restaurant.models import Restaurant, Staff
from restaurant.serializers import StaffListSerializer, StaffRoleSerializer, StaffSerializer, StaffShiftScheduleSerializer, StaffShiftSerializer


# =============================================================================
# Staff List API View
# =============================================================================

class StaffListAPIView(ListAPIView):
    """
    Returns all active staff members
    belonging to the authenticated
    user's restaurant.

    Endpoint

        GET /api/staff/
    """

    serializer_class = StaffListSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    # ==========================================================
    # Queryset
    # ==========================================================


    def get_queryset(self):

        restaurant = get_object_or_404(
            
            Restaurant,
            
            owner=self.request.user,
            
        )

        return (
            
            Staff.objects.filter(
                
                restaurant=restaurant,
                
                is_deleted=False,
                
            )
            .select_related(
                
                "user",
                
                "restaurant",
                
            )
            .order_by(
                
                "first_name",
                
                "last_name",
                
            )
        )
        
        
    # ==========================================================
    # List
    # ==========================================================

    def list(

        self,

        request,

        *args,

        **kwargs,

    ):

        queryset = self.get_queryset()

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

            status=status.HTTP_200_OK,

        )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Search
    #
    # • Role filter
    #
    # • Shift filter
    #
    # • Pagination
    #
    # • Ordering
    #
    # • Permission-based visibility
    #
    # ==========================================================
    
# =============================================================================
# Staff Create API View
# =============================================================================

class StaffCreateAPIView(CreateAPIView):
    
    """
    Creates a new staff member for the
    authenticated user's restaurant.

    Endpoint

        POST /api/staff/
    """

    serializer_class = StaffSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    # ==========================================================
    # Create
    # ==========================================================

    # This @transcaction.atomic becomes valuable later when you expand the flow to:

    # Create Staff
    # Create User (optional)
    # Send invitation
    # Create audit log
    # Assign permissions

    # All of those operations will succeed or fail together
    
    @transaction.atomic
    def create(
        
        self,
        
        request,
        
        *args,
        
        **kwargs,
        
    ):

        restaurant = get_object_or_404(

            Restaurant,

            owner=request.user,

        )

        serializer = self.get_serializer(

            data=request.data,

        )

        serializer.is_valid(

            raise_exception=True,

        )

        staff = serializer.save(
            
            restaurant=restaurant,
            
        )

        return Response(
            
            self.get_serializer(staff).data,
            
            status=status.HTTP_201_CREATED,
            
        )
        

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Automatically generate employee_id
    #
    # • Invite staff by email
    #
    # • Create linked Django User account
    #
    # • Assign default permissions
    #
    # • Send welcome notification
    #
    # • Audit logging
    #
    # ==========================================================
    
# =============================================================================
# Staff Detail API View
# =============================================================================

class StaffDetailAPIView(RetrieveAPIView):
    """
    Returns a single staff member
    belonging to the authenticated
    user's restaurant.

    Endpoint

        GET /api/staff/<id>/
    """

    serializer_class = StaffSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    # ==========================================================
    # Queryset
    # ==========================================================

    def get_queryset(self):

        restaurant = get_object_or_404(

            Restaurant,

            owner=self.request.user,

        )

        return (

            Staff.objects.filter(

                restaurant=restaurant,

                is_deleted=False,

            )

            .select_related(

                "user",

                "restaurant",

            )

        )

    # ==========================================================
    # Retrieve
    # ==========================================================

    def retrieve(

        self,

        request,

        *args,

        **kwargs,

    ):

        staff = self.get_object()

        serializer = self.get_serializer(

            staff,

        )

        return Response(

            serializer.data,

            status=status.HTTP_200_OK,

        )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Permission-based field visibility
    #
    # • Staff activity summary
    #
    # • Shift history
    #
    # • Login history
    #
    # • Performance metrics
    #
    # • Audit logs
    #
    # ==========================================================
    
# =============================================================================
# Staff Update API View
# =============================================================================

class StaffUpdateAPIView(UpdateAPIView):
    
    """
    Updates an existing staff member.

    Endpoint

        PATCH /api/staff/<id>/
    """

    serializer_class = StaffSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    http_method_names = [

        "patch",

    ]

    # ==========================================================
    # Queryset
    # ==========================================================

    def get_queryset(self):

        restaurant = get_object_or_404(

            Restaurant,

            owner=self.request.user,

        )

        return (

            Staff.objects.filter(

                restaurant=restaurant,

                is_deleted=False,

            )

            .select_related(

                "user",

                "restaurant",

            )

        )

    # ==========================================================
    # Partial Update
    # ==========================================================

    @transaction.atomic
    def partial_update(

        self,

        request,

        *args,

        **kwargs,

    ):

        staff = self.get_object()

        serializer = self.get_serializer(

            staff,

            data=request.data,

            partial=True,

        )

        serializer.is_valid(

            raise_exception=True,

        )

        staff = serializer.save()

        return Response(

            self.get_serializer(

                staff,

            ).data,

            status=status.HTTP_200_OK,

        )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Audit Log
    #
    # • Notify user when role changes
    #
    # • Notify when shift changes
    #
    # • Update last_modified_by
    #
    # • Optimistic locking
    #
    # ==========================================================
    
    # Later, when you build Activity Logs/Audit Logs, don't let the serializer handle everything directly. Instead, use a service function:

    # update_staff(
    #     staff,
    #     validated_data,
    #     updated_by=request.user,
    # )

    # That service can:

    # Log every field change
    # Record who updated the staff member
    # Send notifications if the role changes
    # Trigger analytics/events
    
    # ==========================================================
    
# =============================================================================
# Staff Delete API View
# =============================================================================

class StaffDeleteAPIView(DestroyAPIView):
    """
    Soft deletes a staff member.

    Endpoint

        DELETE /api/staff/<id>/
    """

    permission_classes = [

        IsAuthenticated,

    ]

    # ==========================================================
    # Queryset
    # ==========================================================

    def get_queryset(self):

        restaurant = get_object_or_404(

            Restaurant,

            owner=self.request.user,

        )

        return (

            Staff.objects.filter(

                restaurant=restaurant,

                is_deleted=False,

            )

            .select_related(

                "user",

                "restaurant",

            )

        )

    # ==========================================================
    # Destroy
    # ==========================================================

    @transaction.atomic
    def destroy(

        self,

        request,

        *args,

        **kwargs,

    ):

        staff = self.get_object()

        # ------------------------------------------
        # Prevent deleting the restaurant owner
        # ------------------------------------------

        if staff.role == "owner":

            return Response(

                {

                    "detail": (

                        "Restaurant owner "

                        "cannot be deleted."

                    )

                },

                status=status.HTTP_400_BAD_REQUEST,

            )

        # ------------------------------------------
        # Soft Delete
        # ------------------------------------------

        staff.is_deleted = True

        staff.is_active = False

        staff.is_on_shift = False

        staff.is_on_break = False

        staff.resigned_at = timezone.now()

        staff.save(

            update_fields=[

                "is_deleted",

                "is_active",

                "is_on_shift",

                "is_on_break",

                "resigned_at",

            ]

        )

        return Response(

            {

                "detail": (

                    "Staff member deleted "

                    "successfully."

                )

            },

            status=status.HTTP_200_OK,

        )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Audit logging
    #
    # • Email notification
    #
    # • Remove active sessions
    #
    # • Reassign pending work
    #
    # • Archive staff documents
    #
    # ==========================================================
    
    # Since you've been moving business logic into services.py (for example, assign_delivery_partner(), clock_in(), change_role()), I'd eventually create:

    # delete_staff(staff)

    # in services.py.

    # That service could handle:

    # Soft delete
    # Marking the staff inactive
    # Ending any active shift
    # Setting resigned_at
    # Clearing login sessions
    # Writing audit logs
    # Sending notifications

    # Then the view simply becomes:

    # staff = self.get_object()

    # delete_staff(staff)

    # return Response(
    #     {"detail": "Staff member deleted successfully."},
    #     status=status.HTTP_200_OK,
    # )

    # This keeps all business rules centralized and makes the codebase easier to maintain as the Staff module grows.
    
    # =====================================================================
        
# =============================================================================
# Staff Shift API View
# =============================================================================

class StaffShiftAPIView(UpdateAPIView):
    """
    Updates staff shift status.        
    
    Endpoint

        PATCH /api/staff/<id>/shift/

    Request Body

    {
        "action": "clock_in"
    }

    Supported Actions

    • clock_in

    • clock_out

    • start_break

    • end_break

    
    """

    serializer_class = StaffShiftSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    http_method_names = [

        "patch",

    ]

    # ==========================================================
    # Queryset
    # ==========================================================

    def get_queryset(self):

        restaurant = get_object_or_404(

            Restaurant,

            owner=self.request.user,

        )

        return (

            Staff.objects.filter(

                restaurant=restaurant,

                is_deleted=False,

            )

        )

    # ==========================================================
    # Partial Update
    # ==========================================================

    @transaction.atomic
    def partial_update(
        
        self,
        
        request,
        
        *args,
        
        **kwargs,
        
    ):

        staff = self.get_object()

        serializer = self.get_serializer(
            
            data=request.data,
            
        )

        serializer.is_valid(
            
            raise_exception=True,
            
        )

        action = serializer.validated_data["action"]

        if action == "clock_in":

            staff = clock_in(staff)

        elif action == "clock_out":

            staff = clock_out(staff)

        elif action == "start_break":

            staff = start_break(staff)

        elif action == "end_break":

            staff = end_break(staff)

        else:

            return Response(

                {

                    "detail": "Invalid action."

                },

                status=status.HTTP_400_BAD_REQUEST,

            )

        return Response(

            StaffSerializer(
                staff,
                context={
                    "request": request,
                },
            ).data,

            status=status.HTTP_200_OK,

        )
        
    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Shift approval workflow
    #
    # • GPS validation
    #
    # • Attendance integration
    #
    # • Shift history
    #
    # • Overtime calculation
    #
    # • Payroll integration
    #
    # ==========================================================
    
    # Keep shift timings separate

    # I would not mix schedule management with runtime actions.

    # Instead create a separate endpoint later:

    # PATCH /api/staff/<id>/shift-schedule/

    # using a StaffShiftScheduleSerializer for:

    # shift_start
    
    # shift_end

    # This keeps:

    # Shift schedule (planned working hours)
    
    # Shift actions (clock in/out, breaks)

    # as separate responsibilities
    
    # ==========================================================
    
# =============================================================================
# Staff Shift Schedule API View
# =============================================================================

class StaffShiftScheduleAPIView(UpdateAPIView):
    """
    Updates a staff member's planned
    working shift schedule.

    Endpoint

        PATCH /api/staff/<id>/shift-schedule/
    """

    serializer_class = StaffShiftScheduleSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    http_method_names = [

        "patch",

    ]

    # ==========================================================
    # Queryset
    # ==========================================================

    def get_queryset(self):

        restaurant = get_object_or_404(

            Restaurant,

            owner=self.request.user,

        )

        return (

            Staff.objects.filter(

                restaurant=restaurant,

                is_deleted=False,

            )

            .select_related(

                "restaurant",

                "user",

            )

        )

    # ==========================================================
    # Update
    # ==========================================================

    @transaction.atomic
    def update(

        self,

        request,

        *args,

        **kwargs,

    ):

        staff = self.get_object()

        serializer = self.get_serializer(

            staff,

            data=request.data,

            partial=True,

        )

        serializer.is_valid(

            raise_exception=True,

        )

        validated = serializer.validated_data

        staff = update_shift_schedule(

            staff=staff,

            shift_start=validated.get(

                "shift_start",

                staff.shift_start,

            ),

            shift_end=validated.get(

                "shift_end",

                staff.shift_end,

            ),

        )

        return Response(

            StaffSerializer(

                staff,

                context={

                    "request": request,

                },

            ).data,

            status=status.HTTP_200_OK,

        )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Future Improvements
    #
    # • Weekly shift schedules
    #
    # • Rotating shifts
    #
    # • Multiple shifts per day
    #
    # • Holiday schedules
    #
    # • Automatic overtime calculation
    #
    # • Shift templates
    #
    # • Shift approval workflow
    #
    # ==========================================================
    
# ==========================================================
# Staff Role API
# ==========================================================

class StaffRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, staff_id):

        restaurant = get_restaurant(request)

        staff = get_staff_role(
            restaurant=restaurant,
            staff_id=staff_id,
        )

        serializer = StaffRoleSerializer(staff)

        return Response(serializer.data)

    def patch(self, request, staff_id):

        restaurant = get_restaurant(request)

        serializer = StaffRoleSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        staff = update_staff_role(
            restaurant=restaurant,
            staff_id=staff_id,
            role=serializer.validated_data["role"],
        )

        return Response(
            StaffRoleSerializer(staff).data
        )
        
        
