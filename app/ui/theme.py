# app/ui/theme.py

class AppColors:
    # Primary (Vibrant Blue)
    PRIMARY = "#3B82F6"
    PRIMARY_DARK = "#2563EB"
    PRIMARY_LIGHT = "#60A5FA"

    # Status Light
    PRESENT = "#10B981"
    LATE = "#F59E0B"
    INCOMPLETE = "#EF4444"

    # Status Dark
    PRESENT_DARK = "#059669"
    LATE_DARK = "#D97706"
    INCOMPLETE_DARK = "#DC2626"

    # Background Light
    BACKGROUND = "#F8FAFC"
    SURFACE = "#FFFFFF"

    # Background Dark (Sleek Slate)
    BACKGROUND_DARK = "#0F172A"
    SURFACE_DARK = "#1E293B"

    # Text Light
    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#475569"
    TEXT_HINT = "#94A3B8"
    TEXT_INVERSE = "#FFFFFF"

    # Text Dark
    TEXT_PRIMARY_DARK = "#F8FAFC"
    TEXT_SECONDARY_DARK = "#94A3B8"
    TEXT_HINT_DARK = "#64748B"
    TEXT_INVERSE_DARK = "#000000"

    # Border
    BORDER = "#E2E8F0"
    BORDER_DARK = "#334155"

    # Error
    ERROR = "#EF4444"
    ERROR_DARK = "#F87171"


class AppTheme:
    DARK = {
        "background": AppColors.BACKGROUND_DARK,
        "surface": AppColors.SURFACE_DARK,
        "primary": AppColors.PRIMARY,
        "primary_dark": AppColors.PRIMARY_DARK,
        "primary_light": AppColors.PRIMARY_LIGHT,
        "text_primary": AppColors.TEXT_PRIMARY_DARK,
        "text_secondary": AppColors.TEXT_SECONDARY_DARK,
        "text_hint": AppColors.TEXT_HINT_DARK,
        "border": AppColors.BORDER_DARK,
        "error": AppColors.ERROR_DARK,
        "success": AppColors.PRESENT,
        "warning": AppColors.LATE,
    }

    LIGHT = {
        "background": AppColors.BACKGROUND,
        "surface": AppColors.SURFACE,
        "primary": AppColors.PRIMARY,
        "primary_dark": AppColors.PRIMARY_DARK,
        "primary_light": AppColors.PRIMARY_LIGHT,
        "text_primary": AppColors.TEXT_PRIMARY,
        "text_secondary": AppColors.TEXT_SECONDARY,
        "text_hint": AppColors.TEXT_HINT,
        "border": AppColors.BORDER,
        "error": AppColors.ERROR,
        "success": AppColors.PRESENT,
        "warning": AppColors.LATE,
    }