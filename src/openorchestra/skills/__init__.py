"""Skill definitions and templates for OpenOrchestra."""

# Domain-specific skill templates
# These will be loaded and used by the orchestration system

SKILL_TEMPLATES = {
    "backend": {
        "primary_skill": "clean-code",
        "secondary_skills": ["security", "database-design"],
        "evaluation_focus": ["code_quality", "security_standards", "maintainability"],
    },
    "frontend_ui_ux": {
        "primary_skill": "ui-ux-pro-max",
        "secondary_skills": ["design-taste-frontend", "accessibility"],
        "evaluation_focus": [
            "design_system_compliance",
            "accessibility_standards",
            "responsive_behavior",
        ],
    },
}

__all__ = ["SKILL_TEMPLATES"]
