
from lib.feature2 import recommend_career

profiles = {
    "Backend": (
        "Backend Developer with 4 years experience "
        "building Python Django FastAPI PostgreSQL "
        "REST API Docker and microservices applications."
    ),
    "Frontend": (
        "Frontend Developer with 3 years experience "
        "using JavaScript TypeScript React HTML CSS "
        "Tailwind CSS and responsive web development."
    ),
    "Data Science": (
        "Data Scientist with 3 years experience "
        "using Python SQL pandas NumPy statistics "
        "machine learning and predictive modeling."
    ),
    "UI/UX": (
        "UI UX Designer with 3 years experience "
        "using Figma wireframing prototyping user "
        "research usability testing and design systems."
    ),
    "DevOps": (
        "DevOps Engineer with 4 years experience "
        "using Docker Kubernetes AWS Terraform "
        "CI/CD Jenkins and infrastructure automation."
    ),
    "Cybersecurity": (
        "Cybersecurity Analyst with 3 years experience "
        "in SIEM Splunk incident response threat "
        "detection penetration testing and network security."
    ),
}

for profile_name, cv_text in profiles.items():
    result = recommend_career(cv_text)

    print(f"\n{'=' * 55}")
    print(f"CV PROFILE: {profile_name}")
    print(f"STATUS: {result.get('status')}")
    print(
        "DOMINANT CATEGORY:",
        result.get("predicted_category")
    )

    for rec in result.get("top_recommendations", []):
        print(
            f"Rank {rec['rank']}: "
            f"{rec['role_title']} | "
            f"AI Probability: "
            f"{rec['category_probability'] * 100:.2f}% | "
            f"Skill Match: {rec['match_percentage']:.2f}% | "
            f"Source: {rec['source']}"
        )

    if result.get("status") != "success":
        print("ERROR:", result.get("error"))
