# restaurants/services/permissions.py


from restaurant.models import Staff


# ==========================================================
# Staff Management
# ==========================================================

def user_can_manage_staff(staff):
    """
    Staff management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

    ]


# ==========================================================
# Kitchen Display System
# ==========================================================

def user_can_manage_kds(staff):
    """
    Kitchen management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.CHEF,

    ]


# ==========================================================
# Dashboard
# ==========================================================

def user_can_manage_dashboard(staff):
    """
    Dashboard access.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.CHEF,

        Staff.Role.CASHIER,

        Staff.Role.WAITER,

    ]


# ==========================================================
# Orders
# ==========================================================

def user_can_manage_orders(staff):
    """
    Order management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.CHEF,

        Staff.Role.CASHIER,

        Staff.Role.WAITER,

    ]


# ==========================================================
# Tables
# ==========================================================

def user_can_manage_tables(staff):
    """
    Table management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.WAITER,

    ]


# ==========================================================
# Menu
# ==========================================================

def user_can_manage_menu(staff):
    """
    Menu management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.CHEF,

    ]


# ==========================================================
# Delivery
# ==========================================================

def user_can_manage_delivery(staff):
    """
    Delivery management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.DELIVERY_MANAGER,

    ]


# ==========================================================
# Inventory
# ==========================================================

def user_can_manage_inventory(staff):
    """
    Inventory management permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

        Staff.Role.INVENTORY_MANAGER,

    ]


# ==========================================================
# Payments
# ==========================================================

def user_can_manage_payments(staff):
    """
    Payment management permissions.
    """

    return staff.role == Staff.Role.OWNER


# ==========================================================
# Reports
# ==========================================================

def user_can_view_reports(staff):
    """
    Reporting permissions.
    """

    return staff.role in [

        Staff.Role.OWNER,

        Staff.Role.MANAGER,

    ]


# ==========================================================
# Restaurant Settings
# ==========================================================

def user_can_manage_restaurant(staff):
    """
    Restaurant settings permissions.
    """

    return staff.role == Staff.Role.OWNER