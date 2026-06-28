"""Protected and proxy attributes excluded from feature vectors (PRD §12)."""
EXCLUDED_FEATURES = frozenset({
    "gender",
    "age",
    "ethnicity",
    "name_implied_ethnicity",
    "photo",
    "date_of_birth",
    "race",
    "religion",
    "marital_status",
    "nationality",
})
