"""Configurable education-level, degree, specialization, and subject catalog."""

EDUCATION_CATALOG = {
    "10th": {
        "streams": ["Science", "Commerce", "Arts/Humanities", "Diploma/Vocational"],
        "degrees": [], "specializations": {},
        "subjects": {"default": ["mathematics", "science", "english", "social_science", "computer_science"]},
    },
    "12th": {
        "streams": ["Science PCB", "Science PCM", "Commerce", "Arts/Humanities", "Vocational/Diploma"],
        "degrees": [], "specializations": {},
        "subjects": {
            "Science PCB": ["physics", "chemistry", "biology", "english"],
            "Science PCM": ["physics", "chemistry", "mathematics", "english"],
            "Commerce": ["accountancy", "business_studies", "economics", "mathematics", "english"],
            "Arts/Humanities": ["history", "geography", "political_science", "sociology", "english"],
            "Vocational/Diploma": ["mathematics", "computer_science", "business_studies", "english"],
        },
    },
    "Bachelor's": {
        "streams": ["Science", "Commerce", "Business", "Engineering", "Arts/Humanities", "Pharmacy", "Other"],
        "degrees": ["BCA", "B.Com", "BBA", "B.Sc", "B.Tech/BE", "BA", "B.Pharm", "Other"],
        "specializations": {
            "BCA": ["Computer Applications", "Software Development", "Data Analytics", "Other"],
            "B.Com": ["Accounting", "Finance", "Taxation", "Economics", "Other"],
            "BBA": ["Marketing", "Human Resources", "Business Analytics", "Finance", "Entrepreneurship", "Other"],
            "B.Sc": ["Computer Science", "Mathematics", "Physics", "Chemistry", "Biology", "Other"],
            "B.Tech/BE": ["Computer Science", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Electronics Engineering", "Other"],
            "BA": ["English", "Psychology", "History", "Economics", "Political Science", "Other"],
            "B.Pharm": ["Pharmaceutics", "Pharmacology", "Pharmaceutical Chemistry", "Other"],
            "Other": ["Other"],
        },
        "subjects": {
            "BCA": ["programming", "data_structures", "database_management", "computer_networks", "operating_systems", "web_development", "mathematics"],
            "B.Com": ["financial_accounting", "cost_accounting", "business_law", "taxation", "auditing", "economics", "financial_management"],
            "BBA": ["principles_of_management", "marketing", "human_resource_management", "business_analytics", "finance", "entrepreneurship", "business_communication"],
            "B.Sc|Computer Science": ["programming", "data_structures", "algorithms", "database_systems", "computer_networks", "mathematics"],
            "B.Sc|Mathematics": ["calculus", "linear_algebra", "statistics", "differential_equations", "abstract_algebra"],
            "B.Sc|Physics": ["classical_mechanics", "electromagnetism", "quantum_physics", "thermodynamics", "mathematics"],
            "B.Sc|Chemistry": ["organic_chemistry", "inorganic_chemistry", "physical_chemistry", "analytical_chemistry", "mathematics"],
            "B.Sc|Biology": ["cell_biology", "genetics", "ecology", "biochemistry", "microbiology"],
            "B.Tech/BE|Computer Science": ["programming", "data_structures_algorithms", "operating_systems", "database_systems", "computer_networks", "software_engineering", "mathematics"],
            "B.Tech/BE|Mechanical Engineering": ["engineering_mechanics", "thermodynamics", "manufacturing", "machine_design", "fluid_mechanics"],
            "B.Tech/BE|Civil Engineering": ["structural_engineering", "construction_materials", "geotechnical_engineering", "surveying", "hydraulics"],
            "B.Tech/BE|Electrical Engineering": ["circuit_theory", "electrical_machines", "power_systems", "control_systems", "electronics"],
            "B.Tech/BE|Electronics Engineering": ["digital_electronics", "analog_circuits", "signals_systems", "communication_systems", "microprocessors"],
            "B.Pharm": ["pharmaceutics", "pharmacology", "pharmaceutical_chemistry", "pharmacognosy", "human_anatomy"],
            "BA": ["major_subject", "research_methods", "academic_writing", "social_science"],
            "Other": ["major_subject", "research_methods", "academic_writing"],
        },
    },
    "Master's": {
        "streams": ["Computing", "Commerce", "Business", "Science", "Engineering", "Arts/Humanities", "Other"],
        "degrees": ["MCA", "M.Com", "MBA", "M.Sc", "M.Tech/ME", "MA", "Other"],
        "specializations": {
            "MCA": ["Software Engineering", "Data Science", "Artificial Intelligence", "Cybersecurity", "Other"],
            "M.Com": ["Accounting", "Finance", "Taxation", "Business Analytics", "Other"],
            "MBA": ["Finance", "Marketing", "Human Resources", "Operations", "Business Analytics", "Entrepreneurship", "Other"],
            "M.Sc": ["Computer Science", "Mathematics", "Physics", "Chemistry", "Biology", "Other"],
            "M.Tech/ME": ["Computer Science", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Electronics Engineering", "Other"],
            "MA": ["English", "Psychology", "Economics", "History", "Political Science", "Other"],
            "Other": ["Other"],
        },
        "subjects": {
            "MCA": ["advanced_programming", "software_architecture", "database_systems", "cloud_computing", "machine_learning", "research_methods"],
            "M.Com": ["advanced_accounting", "corporate_finance", "advanced_taxation", "auditing", "research_methods"],
            "MBA": ["strategic_management", "corporate_finance", "marketing_strategy", "operations_management", "business_analytics", "leadership"],
            "M.Sc|Computer Science": ["advanced_algorithms", "distributed_systems", "machine_learning", "research_methods", "advanced_mathematics"],
            "M.Sc|Mathematics": ["real_analysis", "abstract_algebra", "topology", "statistics", "research_methods"],
            "M.Sc|Physics": ["quantum_mechanics", "electrodynamics", "statistical_physics", "research_methods"],
            "M.Sc|Chemistry": ["advanced_organic_chemistry", "spectroscopy", "physical_chemistry", "research_methods"],
            "M.Sc|Biology": ["molecular_biology", "genomics", "bioinformatics", "research_methods"],
            "M.Tech/ME|Computer Science": ["advanced_algorithms", "distributed_systems", "ai_systems", "research_methods", "software_architecture"],
            "M.Tech/ME": ["advanced_engineering_design", "systems_analysis", "research_methods", "specialization_project"],
            "MA": ["advanced_theory", "research_methods", "dissertation", "academic_writing"],
            "Other": ["advanced_theory", "research_methods", "dissertation"],
        },
    },
}

def subjects_for(level, degree="", specialization="", custom_subjects=None):
    catalog = EDUCATION_CATALOG.get(level, {})
    if level in ("10th", "12th"):
        subjects = catalog.get("subjects", {}).get(degree or "default", [])
    else:
        lookup = f"{degree}|{specialization}" if specialization else degree
        subjects = catalog.get("subjects", {}).get(lookup, catalog.get("subjects", {}).get(degree, catalog.get("subjects", {}).get("Other", [])))
    return list(dict.fromkeys([*subjects, *(custom_subjects or [])]))

