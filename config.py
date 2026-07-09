"""
Central constants and project configuration for EVOFORGE.

Move constants from legacy/runtime.py into this file over time.
"""

APP_NAME = "EVOFORGE"
APP_TAGLINE = "BODY-TO-BUILD ENGINE"

PRIMARY_PAGES = ["Home", "Today", "Avatar", "Progress", "Physique", "Cardio", "Goals", "Data Manager"]
MORE_PAGES = ["Profile", "Measurements", "Achievements", "Body Fat", "Bodyweight", "Routine", "Delete Data"]
ALL_PAGES = PRIMARY_PAGES + MORE_PAGES

PAGE_LABELS = {
    "Home": "🏠 Base",
    "Today": "⚔️ Missions",
    "Avatar": "🧬 Evolution",
    "Progress": "📊 Analytics",
    "Physique": "🤖 Oracle",
    "Cardio": "❤️ Engine",
    "Goals": "🎯 Quests",
    "Data Manager": "📂 Data",
    "Profile": "🪪 Profile",
    "Measurements": "📏 Measurements",
    "Achievements": "🏆 Achievements",
    "Body Fat": "🔥 Body Fat",
    "Bodyweight": "⚖️ Bodyweight",
    "Routine": "📋 Routine",
    "Delete Data": "🗑️ Delete Data",
}
