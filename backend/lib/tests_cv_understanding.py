"""Run from backend: python -m unittest lib.tests_cv_understanding -v"""
import unittest
from pathlib import Path
from .cv_understanding import understand_cv_from_file

DB = Path(__file__).with_name("skills_database.json")


class CVUnderstandingTests(unittest.TestCase):
    def analyze(self, text):
        return understand_cv_from_file(text, DB)

    def skills(self, text):
        return {s["name"]: s for s in self.analyze(text)["skills"]}

    def test_listed_skills(self):
        skills = self.skills("Skills: Python, PostgreSQL, Docker")
        self.assertTrue({"python", "postgresql", "docker"}.issubset(skills))
        self.assertEqual(skills["docker"]["source"], "skills")

    def test_negative_english(self):
        self.assertNotIn("docker", self.skills("Skills: No experience with Docker"))

    def test_negative_indonesian(self):
        self.assertNotIn("docker", self.skills("Skills: Belum pernah menggunakan Docker"))

    def test_positive_after_contrast(self):
        skills = self.skills("Skills: No Docker, but used Python")
        self.assertNotIn("docker", skills)
        self.assertIn("python", skills)

    def test_future_aspiration(self):
        self.assertNotIn("docker", self.skills("Objective: I want to learn Docker"))

    def test_projects_distinct_from_work(self):
        result = self.analyze("Projects\nBuilt REST API with Django and PostgreSQL for 6 months")
        self.assertEqual(result["experience"]["professional_years"], None)
        self.assertEqual(result["skills"][0]["source"], "projects")
        self.assertEqual(len(result["experience"]["work_entries"]), 0)

    def test_internship_distinct_from_work(self):
        result = self.analyze("Internship\nBackend Developer, Jan 2025 - Jun 2025\nDjango")
        self.assertEqual(result["experience"]["professional_years"], None)
        self.assertGreater(len(result["experience"]["internships"]), 0)

    def test_education(self):
        result = self.analyze("Education\nBachelor of Computer Science")
        self.assertEqual(result["education"]["level"], "bachelor")
        self.assertEqual(result["education"]["field"], "computer science")

    def test_no_education_unknown(self):
        result = self.analyze("Skills: Python")
        self.assertIsNone(result["education"]["level"])

    def test_alias(self):
        skills = self.skills("Skills: Google Cloud Platform and RESTful API")
        self.assertIn("gcp", skills)
        self.assertIn("rest api", skills)

    def test_ambiguous_go_not_general_prose(self):
        self.assertNotIn("go", self.skills("Summary\nI go to work every day"))

    def test_canonical_case(self):
        self.assertIn("c++", self.skills("Skills: C++"))

    def test_job_aspiration_not_skill_evidence(self):
        skills = self.skills("Objective: Looking for a Docker role")
        self.assertNotIn("docker", skills)

    def test_existing_skill_preserved_with_aspiration(self):
        skills = self.skills(
        "Skills: Python\n"
        "Objective: Interested in Docker")
        self.assertIn("python", skills)
        self.assertNotIn("docker", skills)

    def test_summary_positive_and_aspiration(self):
        skills = self.skills(
            "Summary:\n"
            "Experienced Python Developer.\n"
            "Interested in learning Docker."
        )
        self.assertIn("python", skills)
        self.assertNotIn("docker", skills)


    def test_project_skill_and_future_learning(self):
        skills = self.skills(
            "Projects:\n"
            "Built REST APIs using Django.\n"
            "Planning to learn Kubernetes."
        )
        self.assertIn("django", skills)
        self.assertNotIn("kubernetes", skills)


    def test_skill_evidence_overrides_separate_aspiration(self):
        skills = self.skills(
            "Skills: Docker\n"
            "Objective: Interested in Kubernetes"
        )
        self.assertIn("docker", skills)
        self.assertNotIn("kubernetes", skills)


    def test_internship_inside_experience_section(self):
        from lib.cv_understanding import understand_cv_from_file

        profile = understand_cv_from_file(
            "Experience:\n"
            "Internship as Backend Developer using Python and Django."
        )

        skills = {
            item["name"]: item
            for item in profile["skills"]
        }

        self.assertEqual(
            skills["python"]["source"],
            "internship",
        )

        self.assertEqual(
            skills["django"]["evidence_type"],
            "internship",
        )

        self.assertEqual(
            len(profile["experience"]["work_entries"]),
            0,
        )

        self.assertEqual(
            len(profile["experience"]["internships"]),
            1,
        )


    def test_negated_and_aspirational_lists_preserve_scope(self):
        for text, reason in (
            ("Skills: No experience with Docker, Kubernetes and AWS.", "negation"),
            ("Summary: Interested in learning Docker, Kubernetes and AWS.", "aspiration"),
            ("Keahlian: Belum menguasai Docker, Kubernetes dan AWS.", "negation"),
            ("Skills: Docker and Kubernetes are not used.", "negation"),
        ):
            with self.subTest(text=text):
                profile = self.analyze(text)
                self.assertEqual(profile["skills"], [])
                self.assertTrue(profile["excluded_skill_mentions"])
                self.assertEqual({m["reason"] for m in profile["excluded_skill_mentions"]}, {reason})

    def test_positive_evidence_and_rejected_mentions_can_coexist(self):
        profile = self.analyze("Skills: Docker\nSummary: No commercial experience with Docker. Planning to learn Kubernetes.")
        self.assertEqual([s["name"] for s in profile["skills"]], ["docker"])
        self.assertEqual({(m["name"], m["reason"]) for m in profile["excluded_skill_mentions"]},
                         {("docker", "negation"), ("kubernetes", "aspiration")})

    def test_positive_sources_and_aliases(self):
        cases = (
            ("Skills: ReactJS, Postgres, k8s", "skills", {"react", "postgresql", "kubernetes"}),
            ("Projects: Built an API with Python and Django", "projects", {"python", "django"}),
            ("Pengalaman Kerja: Mengembangkan aplikasi menggunakan Python dan Django", "work_experience", {"python", "django"}),
            ("Experience\nBackend Developer Intern using Python and Django", "internship", {"python", "django"}),
        )
        for text, source, expected in cases:
            with self.subTest(source=source):
                profile = self.analyze(text)
                self.assertEqual({s["name"] for s in profile["skills"]}, expected)
                for skill in profile["skills"]:
                    self.assertEqual(skill["source"], source)
                    self.assertTrue(skill["evidence"])
                    self.assertGreater(skill["line"], 0)
                    self.assertTrue(skill["evidence_items"])

    def test_line_numbers_and_late_skill_excerpt_remain_traceable(self):
        profile = self.analyze("\n\nSkills: Python\nProjects:\n" + "description " * 80 + "used Django.")
        skills = {s["name"]: s for s in profile["skills"]}
        self.assertEqual(skills["python"]["line"], 3)
        self.assertIn("django", skills["django"]["evidence"].lower())
        self.assertLessEqual(len(skills["django"]["evidence"]), 400)

    def test_project_and_internship_blocks_inside_work_heading(self):
        profile = self.analyze(
            "Experience\nPersonal Project Jan 2022 - Dec 2023\nUsed Django.\n"
            "Backend Developer Intern Jan 2024 - Jun 2024\nUsed Python.\n"
            "Backend Developer Jul 2024 - Dec 2024\nUsed PostgreSQL."
        )
        skills = {s["name"]: s for s in profile["skills"]}
        self.assertEqual(skills["django"]["source"], "projects")
        self.assertEqual(skills["python"]["source"], "internship")
        self.assertEqual(skills["postgresql"]["source"], "work_experience")

    def test_education_without_supported_degree_remains_unknown(self):
        for text in (
            "Skills: Python\nSummary: Scrum Master and backend developer.",
            "Summary: No bachelor degree; want to master Python.",
            "Objective: Want to earn a Bachelor of Computer Science.",
            "Education: Currently pursuing Bachelor of Computer Science.",
            "Education\nBachelor of Computer Science\nExpected graduation in 2028",
            "Education: Computer Science coursework only",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.analyze(text)["education"]["level"])

    def test_unheaded_declared_degree_and_completed_degree_are_supported(self):
        for text in ("Bachelor in Computer Science", "Pendidikan: Lulus S1 Teknik Informatika"):
            with self.subTest(text=text):
                edu = self.analyze(text)["education"]
                self.assertEqual(edu["level"], "bachelor")
                self.assertTrue(edu["evidence"])
                self.assertIn(edu["status"], ("reported", "completed"))

    def test_contractions_aspiring_and_nonexclusive_not_only(self):
        for text in (
            "Summary: I haven't used Docker or Kubernetes.",
            "Skills: I don't know Docker.",
            "Summary: Aspiring Python Developer.",
            "Target Role: Python Developer",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.analyze(text)["skills"], [])
        self.assertIn("python", self.skills("Skills: Not only Python but Django"))

    def test_completed_degree_is_not_erased_by_a_separate_negated_degree(self):
        education = self.analyze("Education: Graduated Bachelor of Computer Science; no Master degree.")["education"]
        self.assertEqual(education["level"], "bachelor")
        self.assertEqual(education["status"], "completed")
        self.assertEqual({e["status"] for e in education["entries"]}, {"completed", "negated"})

    def test_unicode_contraction_is_rejected(self):
        profile = self.analyze("Skills: I haven’t used Docker or Kubernetes.")
        self.assertEqual(profile["skills"], [])
        self.assertEqual({m["reason"] for m in profile["excluded_skill_mentions"]}, {"negation"})

    def test_wrapped_negative_and_learning_statements_keep_context(self):
        for text in (
            "Skills: No experience with\nDocker, Kubernetes",
            "Summary: Interested in learning\nDocker, Kubernetes",
            "Keahlian: Belum menguasai\nDocker dan Kubernetes",
        ):
            with self.subTest(text=text):
                profile = self.analyze(text)
                self.assertEqual(profile["skills"], [])
                self.assertEqual({m["name"] for m in profile["excluded_skill_mentions"]}, {"docker", "kubernetes"})
                self.assertTrue(all(m["context_evidence"]["line"] == 1 for m in profile["excluded_skill_mentions"]))
        skills = self.skills("Skills: No experience with\nDocker, but used Python.\nSkills: Django")
        self.assertEqual(set(skills), {"python", "django"})

if __name__ == "__main__":
    unittest.main()


class SharedTaxonomyRegressionTests(unittest.TestCase):
    def skills(self, text):
        return {s['name']: s for s in understand_cv_from_file(text, DB)['skills']}

    def test_requirements_headings_inline_and_multiline(self):
        headings = ['Job Requirements', 'Job Description', 'Desired Skills',
                    'Target Position Requirements', 'Skills Required',
                    'Persyaratan Lowongan', 'Kualifikasi yang Dibutuhkan']
        for heading in headings:
            for separator in [': ', '\n']:
                with self.subTest(heading=heading, separator=separator):
                    text = 'Skills: Python, Django\n'+heading+separator+'AWS, Docker,\nKubernetes\nProjects\nUsed PostgreSQL in a project.'
                    self.assertEqual(set(self.skills(text)), {'python','django','postgresql'})
                    rejected = understand_cv_from_file(text, DB)['excluded_skill_mentions']
                    self.assertEqual({x['name'] for x in rejected}, {'aws','docker','kubernetes'})
                    self.assertTrue(all(x['reason']=='job_requirement_context' for x in rejected))

    def test_positive_project_overrides_separate_requirement_mention(self):
        text = 'Job Requirements: Docker, AWS\nProjects\nUsed Docker and Python in a project.\nWork Experience\nUsed PostgreSQL where reliability was required.'
        self.assertEqual(set(self.skills(text)), {'docker','python','postgresql'})

    def test_job_parser_still_detects_external_requirements(self):
        from .feature1 import extract_skills, load_skills_database
        self.assertEqual(extract_skills('Job Requirements: AWS, Docker, Kubernetes',load_skills_database()), ['aws','docker','kubernetes'])

    def test_shared_aliases_boundaries_and_no_spark_duplicate(self):
        skills=self.skills('Skills: SPARK, Apache Spark, PySpark, Kafka, Apache Kafka, Airflow, Google BigQuery, Postgres, RESTful APIs')
        self.assertEqual(set(skills), {'apache spark','pyspark','apache kafka','apache airflow','bigquery','postgresql','rest api'})
        self.assertEqual(self.skills('Summary\nWe go forward with Pandasaurus and rediscover new approaches.'), {})
        self.assertEqual(set(self.skills('Skills: PySpark')), {'pyspark'})

    def test_domains_do_not_replace_technical_evidence(self):
        vocabulary={'test':['e-commerce','analytics','database','scripting','microservices','big data','Python']}
        from .cv_understanding import understand_cv
        profile=understand_cv('Projects\nStream Analytics E-Commerce\nUsed Python, database partitioning, scripting and microservices.',vocabulary)
        skills={x['name']:x for x in profile['skills']}
        self.assertNotIn('e-commerce',skills)
        self.assertEqual(skills['database']['skill_kind'],'general_concept')
        self.assertEqual(skills['scripting']['skill_kind'],'technical_method')
        explicit=understand_cv('Skills: e-commerce',vocabulary)['skills']
        self.assertEqual(explicit[0]['skill_kind'],'industry_domain')

    def test_basic_claim_metadata_does_not_infer_advanced(self):
        aws=self.skills('Skills: AWS Basics')['aws']
        self.assertEqual(aws['proficiency'],'basic')
        self.assertEqual(aws['claim_status'],'reported_positive')
        self.assertEqual(self.skills('Skills: Python')['python']['proficiency'],'unspecified')

    def test_both_features_use_shared_canonical_skills(self):
        from .feature1 import extract_skills, load_skills_database
        from .feature2 import _evidence_profile, normalize_skill
        text='Skills: Spark, PySpark, Airflow, Pandas, BigQuery, Snowflake, Grafana, Kafka'
        expected={'apache spark','pyspark','apache airflow','pandas','bigquery','snowflake','grafana','apache kafka'}
        self.assertEqual(set(self.skills(text)), expected)
        self.assertEqual(set(extract_skills(text,load_skills_database())), expected)
        self.assertEqual({x['name'] for x in _evidence_profile(text)['skills']},expected)
        self.assertEqual(normalize_skill('Spark'),'apache spark')


class SharedEducationPolicyTests(unittest.TestCase):
    def education(self,text):
        from .cv_understanding import understand_education,understand_cv
        import json
        skills=json.loads(DB.read_text(encoding='utf-8'))
        expected=understand_education(text)
        self.assertEqual(understand_cv(text,skills)['education'],expected)
        self.assertEqual(understand_cv(text,skills,matching_context=True)['education'],expected)
        return expected

    def test_completed_degree_and_unspecified_completion_are_distinct(self):
        completed=self.education("Education: Completed Bachelor's degree in Computer Science")
        self.assertEqual(completed['level'],'bachelor')
        self.assertEqual(completed['completion_status'],'completed')
        reported=self.education('Education: Bachelor of Computer Science')
        self.assertEqual(reported['level'],'bachelor')
        self.assertEqual(reported['status'],'reported')
        self.assertEqual(reported['completion_status'],'unknown')
        self.assertEqual(self.education('Summary: Backend Developer with Bachelor in Computer Science')['level'],'bachelor')

    def test_in_progress_level_is_reported_but_not_a_held_qualification(self):
        for text in ["Education: Currently pursuing Bachelor's degree in Computer Science", 'Pendidikan: Sedang menempuh S1 Teknik Informatika','Pendidikan: Belum lulus S1 Teknik Informatika']:
            with self.subTest(text=text):
                edu=self.education(text)
                self.assertIsNone(edu['level'])
                self.assertEqual(edu['reported_level'],'bachelor')
                self.assertEqual(edu['status'],'in_progress')
                self.assertEqual(edu['completion_status'],'in_progress')
                self.assertIsNotNone(edu['field'])

    def test_course_training_and_degree_level_are_not_degrees(self):
        for text in ['Bachelor-level Python course','Bachelor level Python training','Bachelor-level','Sertifikasi: Certified in Data Engineering','Courses\nBachelor in Computer Science','Education and Certifications\nBachelor-level Python course','Pendidikan & Sertifikasi\nPelatihan setara Sarjana']:
            with self.subTest(text=text):
                edu=self.education(text)
                self.assertIsNone(edu['level'])
                self.assertEqual(edu['completion_status'],'unknown')

    def test_field_only_does_not_invent_degree_or_completion(self):
        edu=self.education('Summary: Fresh graduate in Data Science')
        self.assertIsNone(edu['level'])
        self.assertEqual(edu['field'],'data science')
        self.assertEqual(edu['completion_status'],'unknown')
        bilingual=self.education('Profil: Lulusan baru Sains Data dan Informatika')
        self.assertIsNone(bilingual['level'])
        self.assertEqual(bilingual['fields'],['data science','informatika'])

    def test_positive_degree_is_not_erased_by_separate_course(self):
        edu=self.education("Education: Completed Bachelor's degree in Computer Science; Python training course.")
        self.assertEqual(edu['level'],'bachelor')
        self.assertEqual(edu['completion_status'],'completed')
        self.assertTrue(edu['non_degree_claims'])
        self.assertEqual(edu['non_degree_claims'][0]['kind'],'course')
        self.assertEqual(edu['non_degree_claims'][0]['kinds'],['course','training'])
        self.assertEqual(self.education('Certified in Data Engineering')['non_degree_claims'][0]['kind'],'certification')
        self.assertEqual(self.education('Bachelor-level Python course')['non_degree_claims'][0]['kind'],'course')

    def test_aspiration_and_target_requirements_are_not_degrees(self):
        for text in ["Objective: I want to pursue Bachelor's degree in Computer Science", 'Education: Applying for Bachelor of Computer Science', 'Job Requirements: Bachelor in Computer Science']:
            with self.subTest(text=text):
                edu=self.education(text)
                self.assertIsNone(edu['level'])
                self.assertEqual(edu['completion_status'],'unknown')
                self.assertTrue(edu['entries'])
                self.assertIn(edu['entries'][0]['status'],['aspiration','requirement_reference'])

    def test_mixed_degree_statuses_keep_completed_bachelor(self):
        edu=self.education('Education: Graduated Bachelor of Computer Science; pursuing Master in Data Science')
        self.assertEqual(edu['level'],'bachelor')
        self.assertEqual(edu['completion_status'],'completed')
        self.assertEqual([e['status'] for e in edu['entries']],['completed','in_progress'])

    def test_legacy_helpers_have_no_keyword_only_fallback(self):
        from .feature1 import get_education_level,get_education_field
        self.assertEqual(get_education_level('Bachelor-level Python course'),0)
        self.assertEqual(get_education_level('Scrum Master certification'),0)
        self.assertEqual(get_education_level('Bachelor in Computer Science'),2)
        self.assertEqual(get_education_field('Fresh graduate in Data Science'),'data science')

    def test_both_feature_profiles_share_education_without_rank_or_skill_changes(self):
        from . import feature1,feature2
        from unittest.mock import patch
        text='Education: Bachelor-level Python course.\nSkills: Python, Django, SQL.\nProjects: Used Python in a student project.'
        direct=feature2.predict_career_categories(text)
        with patch.object(feature1,'calculate_semantic_score',return_value=80):
            first=feature1.analyze_cv_job(text,'Required: Python. Bachelor in Computer Science required.')
        second=feature2.recommend_career(text)
        self.assertEqual(first['cv_understanding']['education'],second['profile_summary']['cv_understanding']['education'])
        self.assertIsNone(first['scores']['education'])
        self.assertEqual(second['profile_summary']['category_probabilities'],direct['probabilities'])
        self.assertTrue({'python','django','sql'} <= set(second['detected_skills']))


    def test_mentions_of_other_peoples_degrees_do_not_verify_candidate_degree(self):
        for text in ['Work Experience: Mentored Bachelor students in Computer Science', 'Summary: I evaluate Bachelor programs.', 'Education: Bachelor degree requirements for applicants', "Work Experience: Built an app for Bachelor's students."]:
            with self.subTest(text=text):
                self.assertIsNone(self.education(text)['level'])


    def test_job_qualification_context_is_distinct_from_candidate_ownership(self):
        from .feature1 import understand_job_requirements,load_skills_database
        for text in ["Required: A Bachelor's degree in Computer Science is required.", 'Requirements: Applicants must have Bachelor in Computer Science.', 'Required: You must have Bachelor in Computer Science.']:
            with self.subTest(text=text):
                self.assertEqual(understand_job_requirements(text,load_skills_database())['education_level'],2)
        self.assertIsNone(self.education('Work Experience: Mentored Bachelor students in Computer Science')['level'])


class GeneralizedEvidenceTests(unittest.TestCase):
    def profile(self, text):
        from .cv_understanding import understand_cv_from_file
        return understand_cv_from_file(text)

    def test_headingless_project_claims_have_local_sources_in_both_features(self):
        from . import feature2
        for text in ['Used Python and SQL in an academic project.', 'Membangun proyek kuliah menggunakan Python dan SQL.', 'Implemented a dashboard project using Python and SQL.']:
            with self.subTest(text=text):
                for p in [self.profile(text), feature2._evidence_profile(text)]:
                    self.assertTrue(p['experience']['projects'])
                    self.assertFalse(p['experience']['work_entries'])
                    for item in p['skills']:
                        if item['name'] in {'python','sql'}:
                            self.assertEqual(item['evidence_items'][0]['source'],'projects')
                            self.assertEqual(item['evidence_items'][0]['evidence_type'],'project')

    def test_project_context_does_not_spread_across_paragraph_or_skill_list(self):
        p=self.profile('Used Python in a campus project. Interested in learning Docker. Used SQL for data queries.')
        skills={s['name']:s for s in p['skills']}
        self.assertEqual(skills['python']['source'],'projects')
        self.assertEqual(skills['sql']['source'],'unspecified')
        self.assertNotIn('docker',skills)
        self.assertEqual(len(p['experience']['projects']),1)

    def test_nonasserted_projects_and_requirements_are_not_evidence(self):
        for text in ['I want to build a project using Python.', 'I never implemented a Python project.', 'Job requirements\nBuild a Python project.', 'Objective: Implement a Python project.']:
            with self.subTest(text=text):
                p=self.profile(text)
                self.assertFalse(p['skills'])
                self.assertFalse(p['experience']['projects'])

    def test_work_internship_and_unknown_activity_are_not_promoted(self):
        for text,source in [('Work Experience\nUsed Python on a client project.','work_experience'),('Internship\nUsed Python in an academic project.','internship'),('Used Python to process data.','unspecified')]:
            with self.subTest(source=source):
                self.assertEqual(self.profile(text)['skills'][0]['source'],source)

    def test_semantic_representation_keeps_positive_input_byte_for_byte(self):
        from .cv_understanding import semantic_cv_representation
        for text in ['Skills: Python, SQL\nProjects\nBuilt an API.', 'Not only Python but also SQL.', 'Tidak hanya Python tetapi juga SQL.']:
            with self.subTest(text=text):
                self.assertEqual(semantic_cv_representation(text)['text'],text)

    def test_semantic_representation_preserves_positive_prefix_and_later_evidence(self):
        from .cv_understanding import semantic_cv_representation
        text='Used Python and Django, not Docker. Used Docker in a separate project.'
        result=semantic_cv_representation(text)
        self.assertIn('Used Python and Django',result['text'])
        self.assertIn('Used Docker in a separate project.',result['text'])
        self.assertNotIn('not Docker',result['text'])
        self.assertTrue(result['metadata']['filter_applied'])

    def test_semantic_wrapped_negation_aspiration_and_requirements_are_local(self):
        from .cv_understanding import semantic_cv_representation
        for cue in ['No experience with','Currently learning']:
            text=cue+'\nKubernetes, Terraform.\nProjects\nUsed Python in a project.'
            result=semantic_cv_representation(text)['text']
            self.assertNotIn('Kubernetes',result)
            self.assertIn('Python',result)
        result=semantic_cv_representation('Job requirements\nKubernetes\nSkills: Python')['text']
        self.assertNotIn('Kubernetes',result)
        self.assertIn('Python',result)

    def test_no_asserted_text_reports_raw_fallback_without_inventing_input(self):
        from .cv_understanding import semantic_cv_representation
        for text in ['Kubernetes is not a skill I have.', 'I am currently learning SQL.']:
            result=semantic_cv_representation(text)
            self.assertEqual(result['text'],text)
            self.assertEqual(result['metadata']['fallback_reason'],'no_asserted_text')
            self.assertFalse(result['metadata']['asserted_text_available'])


    def test_learning_inside_mixed_claim_is_not_promoted_to_skill(self):
        for text in ["Used Python and I am learning Kubernetes.", "Menggunakan Python dan sedang mempelajari Kubernetes."]:
            with self.subTest(text=text):
                skills={s['name'] for s in self.profile(text)['skills']}
                self.assertIn('python',skills)
                self.assertNotIn('kubernetes',skills)

    def test_without_clause_keeps_actual_implementation_evidence(self):
        from .cv_understanding import semantic_cv_representation
        for text in ['Implemented a Python service without Docker.', 'Menggunakan Python tanpa Docker.', 'Used Python with no Docker.']:
            with self.subTest(text=text):
                result=semantic_cv_representation(text)
                self.assertIn('Python',result['text'])
                self.assertNotIn('Docker',result['text'])
                self.assertTrue(result['metadata']['filter_applied'])


    def test_bullet_inline_heading_resets_semantic_negation_continuation(self):
        from .cv_understanding import semantic_cv_representation
        result=semantic_cv_representation('Skills: No experience with\n\u2022 Skills: Python')
        self.assertEqual(result['text'],'Python')
        self.assertTrue(result['metadata']['filter_applied'])


class SystemRequirementIntegrityTests(unittest.TestCase):
    def analyze(self, cv, job):
        from . import feature1
        from unittest.mock import patch
        with patch.object(feature1,'calculate_semantic_score',return_value=60):
            return feature1.analyze_cv_job(cv,job)

    def test_markdown_headings_separate_skills_experience_and_education(self):
        cv='Education: Completed Bachelor in Computer Science\nSkills: Python, SQL\nWork Experience\nDeveloper Jan 2023 - Dec 2024'
        job='**Required Skills:**\n- Python\n- SQL\n**Preferred Skills:**\n- Docker\n**Experience Requirements:**\nMinimum 1 year professional experience.\n**Education Requirements:**\nCompleted Bachelor in Computer Science required.\n**Responsibilities:**\nMaintain Kubernetes services.'
        r=self.analyze(cv,job)
        self.assertEqual(r['job_understanding']['scoring_skills'],['python','sql'])
        self.assertEqual(r['scores']['education'],100)
        self.assertEqual(r['scores']['experience'],100)
        self.assertEqual(r['job_understanding']['requirement_coverage']['total'],2)

    def test_unknown_required_slot_is_disclosed_not_missing_or_matched(self):
        r=self.analyze('Skills: Python','Required skills: Python, ZorgDB\nPreferred: SQL')
        c=r['job_understanding']['requirement_coverage']
        self.assertEqual((c['total'],c['recognized'],c['matched'],c['unmatched'],c['unresolved']),(2,1,1,0,1))
        self.assertEqual(c['recognition_coverage'],.5)
        self.assertEqual(r['skills']['missing_or_not_detected'],[])
        self.assertTrue(any('belum dapat dinilai' in x for x in r['recommendations']))
        self.assertEqual(r['scores']['skill'],100) # Conditional recognized coverage, not all requirements.
        self.assertEqual(r['scoring_info']['observed_weight'],.65)

    def test_partial_composite_slot_is_unknown_and_no_silent_substring_match(self):
        r=self.analyze('Skills: Python','Required skills: Python / ZorgDB')
        self.assertEqual(r['job_understanding']['requirement_coverage']['unresolved'],1)
        self.assertIsNone(r['scores']['skill'])

    def test_aliases_match_without_inferring_related_technologies(self):
        r=self.analyze('Skills: HTML5, CSS3, DRF, Selenium WebDriver, PostgreSQL','Required skills: HTML, CSS, Django REST Framework, Selenium, SQL, Django')
        self.assertEqual(set(r['skills']['matched']),{'html','css','django rest framework','selenium'})
        self.assertEqual(set(r['skills']['missing_or_not_detected']),{'sql','django'})
        from . import feature2
        self.assertEqual(feature2.get_skill_gap(['html5','css3','drf','selenium webdriver'],['HTML','CSS','Django REST Framework','Selenium']),[])

    def test_sql_not_inferred_from_postgres_and_spark_not_pyspark(self):
        r=self.analyze('Skills: PostgreSQL, PySpark, AWS, API Testing','Required skills: SQL, Apache Spark, GCP, REST API')
        self.assertEqual(r['scores']['skill'],0)

    def test_completion_on_next_nonempty_education_line_is_preserved(self):
        from .cv_understanding import understand_education
        e=understand_education('Pendidikan\nS1 Teknik Informatika\n\nUniversitas Simulasi\n\nLulus 2024.')
        self.assertEqual(e['completion_status'],'completed')
        self.assertEqual(e['qualification_code'],'s1')

    def test_course_and_certification_cannot_complete_academic_degree(self):
        r=self.analyze('Education: Bachelor-level Python course\nCertification: Certified in Data Engineering','Education requirements: Completed Bachelor in Computer Science required.')
        self.assertIsNone(r['scores']['education'])
        self.assertIsNone(r['cv_understanding']['education']['level'])

    def test_in_progress_cannot_meet_completed_degree_but_can_meet_student_eligibility(self):
        cv='Education: Currently pursuing Bachelor in Computer Science\nSkills: Python'
        strict=self.analyze(cv,'Education requirements: Completed Bachelor in Computer Science required.')
        allowed=self.analyze(cv,'Education requirements: Currently pursuing or completed Bachelor in Computer Science. Final-year students are eligible; graduation is not mandatory.')
        self.assertEqual(strict['scores']['education'],0)
        self.assertEqual(allowed['scores']['education'],100)
        self.assertIsNone(allowed['cv_understanding']['education']['level'])
        self.assertEqual(allowed['cv_understanding']['education']['completion_status'],'in_progress')

    def test_unknown_completion_and_absent_requirement_stay_unknown(self):
        a=self.analyze('Education: Bachelor in Computer Science','Education requirements: Completed Bachelor in Computer Science required.')
        b=self.analyze('Education: Completed Bachelor in Computer Science','Required skills: Python')
        self.assertIsNone(a['scores']['education']);self.assertIsNone(b['scores']['education'])

    def test_diploma_iv_and_diploma_iii_keep_explicit_qualification(self):
        a=self.analyze('Education: D4 Teknologi Rekayasa Komputer | Selesai 2023','Pendidikan: Selesai D4 Teknologi Rekayasa Komputer wajib.')
        b=self.analyze('Education: D3 Computer Science | Graduated 2023','Education requirements: Completed Bachelor in Computer Science required.')
        self.assertEqual(a['scores']['education'],100)
        self.assertEqual(a['cv_understanding']['education']['qualification_code'],'d4')
        self.assertLess(b['scores']['education'],100)

    def test_project_heading_prevents_professional_duration_leakage(self):
        r=self.analyze('Work Experience\nDeveloper Jan 2024 - Dec 2024\nProyek Tambahan\nCampus app Jan 2023 - Dec 2023\nUsed Python.','Minimum 2 years professional experience.')
        self.assertEqual(r['experience']['estimated_cv_years'],1)
        self.assertEqual(r['scores']['experience'],50)

    def test_freelance_can_meet_relevant_years_but_not_become_full_time(self):
        cv='Selected Freelance Work\nFrontend Contractor May 2025 - September 2026\nUsed JavaScript and React.'
        relevant=self.analyze(cv,'Minimum 1 year relevant experience. Freelance accepted; full-time employment is not mandatory.')
        strict=self.analyze(cv,'Minimum 1 year full-time professional experience.')
        self.assertEqual(relevant['scores']['experience'],100)
        self.assertIsNone(relevant['experience']['estimated_cv_years'])
        self.assertIsNone(strict['scores']['experience'])

    def test_accepted_types_do_not_invent_unspecified_duration(self):
        cv='Internship\nDeveloper Intern Jan 2025 - Apr 2025\nSkills: Python'
        r=self.analyze(cv,'Experience requirements: Internships are welcome.')
        self.assertEqual(r['experience']['requirement_status'],'conditional')
        self.assertEqual(r['experience']['eligibility_status'],'accepted_evidence')
        self.assertIsNone(r['scores']['experience'])

    def test_explicit_waiver_is_not_employment_claim_or_absent_requirement(self):
        waived=self.analyze('Skills: Python','Experience requirements: Full-time professional experience is not required. Internships accepted.')
        absent=self.analyze('Skills: Python','Required skills: Python')
        self.assertEqual(waived['experience']['requirement_status'],'waived')
        self.assertEqual(waived['scores']['experience'],100)
        self.assertIsNone(waived['experience']['estimated_cv_years'])
        self.assertIsNone(absent['scores']['experience'])

    def test_incomplete_freelance_dates_cannot_prove_years(self):
        r=self.analyze('Freelance Work\nDeveloper May 2025 - 2026\nUsed Python.','Minimum 1 year relevant experience. Freelance accepted.')
        self.assertIsNone(r['scores']['experience'])

    def test_wrapped_negative_expertise_does_not_create_skill_evidence(self):
        from .cv_understanding import understand_cv_from_file
        p=understand_cv_from_file('Skills: Python\nTidak mengklaim keahlian\npenetration testing.')
        self.assertNotIn('penetration testing',{x['name'] for x in p['skills']})

    def test_negative_or_future_completion_does_not_award_degree(self):
        from .cv_understanding import understand_education
        for text in ['Education: Bachelor in Computer Science, belum selesai.', 'Education: S1 Teknik Informatika | Sedang ditempuh, perkiraan selesai 2027.']:
            with self.subTest(text=text):
                p=understand_education(text)
                self.assertIsNone(p['level'])
                self.assertEqual(p['completion_status'],'in_progress')

    def test_activity_heading_ends_prior_internship_without_inventing_employment(self):
        from .cv_understanding import understand_cv_from_file
        text='Internship\nQA Intern Jan 2025 - Apr 2025\nAktivitas dan Hasil\nDalam tugas akhir saya membuat aplikasi menggunakan Python.\nUsed SQL for data processing.'
        p=understand_cv_from_file(text)
        skills={x['name']:x for x in p['skills']}
        self.assertEqual(skills['python']['source'],'projects')
        self.assertEqual(skills['sql']['source'],'unspecified')
        self.assertFalse(p['experience']['work_entries'])


    def test_rejected_type_cannot_inherit_acceptance_from_other_clause(self):
        cv='Freelance Work\nDeveloper Jan 2024 - Dec 2025\nSkills: Python'
        r=self.analyze(cv,'Experience requirements: Minimum 1 year relevant experience; freelance not accepted; internships welcome.')
        self.assertNotIn('freelance',r['experience']['accepted_types'])
        self.assertIsNone(r['scores']['experience'])

    def test_local_negative_requirement_keeps_positive_prefix(self):
        r=self.analyze('Skills: Python','Required skills: Python, not Docker')
        self.assertEqual(r['skills']['job_requirement'],['python'])

    def test_work_engagement_type_is_not_inherited_from_previous_job(self):
        from .cv_understanding import understand_cv_from_file
        p=understand_cv_from_file('Work Experience\nPart-time Developer Jan 2023 - Dec 2023\nDeveloper Jan 2024 - Dec 2024')
        entries=p['experience']['work_entries']
        self.assertEqual(entries[0]['engagement_type'],'part_time')
        self.assertIsNone(entries[1]['engagement_type'])


    def test_equivalent_field_translation_matches_any_explicit_allowed_field(self):
        r=self.analyze('Pendidikan: S1 Sistem Informasi | Lulus 2024.','Education requirements: Completed Bachelor in Computer Science or Information Systems required.')
        self.assertEqual(r['scores']['education'],100)
        self.assertEqual(r['cv_understanding']['education']['field'],'sistem informasi')

    def test_related_field_is_not_silently_canonicalized_as_same_discipline(self):
        r=self.analyze('Pendidikan: S1 Teknik Informatika | Lulus 2024.','Education requirements: Completed Bachelor in Computer Science or related field required.')
        self.assertEqual(r['cv_understanding']['education']['field'],'teknik informatika')
        self.assertEqual(r['scores']['education'],90) # Existing related-technology tier.


    def test_inline_required_and_competence_lists_keep_unsupported_slots(self):
        for job in ['Required: Python and ZorgDB', 'Must know Python and ZorgDB', 'Harus menguasai Python dan ZorgDB']:
            with self.subTest(job=job):
                c=self.analyze('Skills: Python',job)['job_understanding']['requirement_coverage']
                self.assertEqual((c['total'],c['recognized'],c['unresolved']),(2,1,1))

    def test_free_prose_does_not_claim_exhaustive_recognition(self):
        c=self.analyze('Skills: Python','Python is used by this team.')['job_understanding']['requirement_coverage']
        self.assertIsNone(c['recognition_coverage'])
        self.assertEqual(c['enumeration_status'],'non_exhaustive_prose')


    def test_wrapped_inline_required_list_and_additional_requirement(self):
        job='Wajib menguasai Python, SQL,\nDocker, dan Git. Selain itu membutuhkan Kubernetes.'
        r=self.analyze('Skills: Python, SQL, Docker, Git',job)
        self.assertIn('kubernetes',r['skills']['missing_or_not_detected'])
        self.assertEqual(r['job_understanding']['requirement_coverage']['total'],5)

    def test_record_boundaries_keep_acceptance_separate_from_waiver_clause(self):
        cv='Freelance Work\nFrontend Contractor May 2025 - September 2026'
        job='**Experience Requirements:**\nMinimum 1 year of relevant frontend development experience. Professional freelance or contract development experience is accepted; full-time employment is not mandatory.'
        r=self.analyze(cv,job)
        self.assertIn('freelance',r['experience']['accepted_types'])
        self.assertEqual(r['scores']['experience'],100)

    def test_personal_project_dates_do_not_inflate_freelance_duration(self):
        cv='Selected Freelance Work\nFrontend Contractor May 2025 - September 2026\nPersonal Project\nCampus portal February - April 2025'
        r=self.analyze(cv,'Experience requirements: Minimum 1 year relevant experience; freelance accepted.')
        self.assertEqual(r['experience']['eligible_years'],1.42)
        self.assertIsNone(r['experience']['estimated_cv_years'])


    def test_longest_multiword_requirement_does_not_add_component_requirement(self):
        r=self.analyze('Skills: DRF','Required skills: Django REST Framework required')
        self.assertEqual(r['skills']['job_requirement'],['django rest framework'])
        self.assertEqual(r['scores']['skill'],100)


    def test_reviewed_html_css_bundle_requires_both_components_in_both_features(self):
        from . import feature2
        yes=self.analyze('Skills: HTML5, CSS3','Required skills: HTML/CSS')
        no=self.analyze('Skills: HTML5','Required skills: HTML/CSS')
        self.assertEqual(yes['scores']['skill'],100)
        self.assertEqual(yes['job_understanding']['requirement_coverage']['matched'],1)
        self.assertEqual(no['scores']['skill'],0)
        self.assertEqual(feature2.calculate_skill_match_percentage(['HTML5','CSS3'],['HTML/CSS']),100)

    def test_unreviewed_slash_alternatives_remain_unresolved(self):
        r=self.analyze('Skills: AWS, Apache Spark','Required skills: AWS/GCP, Spark/PySpark')
        self.assertEqual(r['job_understanding']['requirement_coverage']['unresolved'],2)
        self.assertIsNone(r['scores']['skill'])


    def test_course_completion_on_later_line_does_not_complete_prior_degree(self):
        r=self.analyze('Education\nBachelor in Computer Science\nPython training course\nCompleted 2024.','Education requirements: Completed Bachelor in Computer Science required.')
        self.assertEqual(r['cv_understanding']['education']['completion_status'],'unknown')
        self.assertIsNone(r['scores']['education'])
