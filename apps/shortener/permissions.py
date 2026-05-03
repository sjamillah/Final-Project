from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwner(BasePermission):
    """
    Object-level permission.
    Write and read access is only allowed to the owner of the object.
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission.
    Read access is allowed to anyone.
    Write access is only allowed to the owner of the URL.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsPremiumUser(BasePermission):
    """
    Allows access only to users with is_premium=True or tier=ADMIN.
    Used to gate premium-only features like custom aliases and analytics.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_premium or request.user.tier == request.user.Tier.ADMIN
            )
        )
