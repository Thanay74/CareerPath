import csv
import unittest
from pathlib import Path

from backend.skill_catalog import SKILLS, canonical_skill, career_skill_guidance, education_skill_catalog


def names(group):
    return {item['key'] for item in group}


class EducationSkillCatalogTests(unittest.TestCase):
    def test_every_standardized_display_label_resolves_to_its_canonical_key(self):
        for key, (label, _category, _contexts) in SKILLS.items():
            with self.subTest(label=label):
                self.assertEqual(canonical_skill(label), key)

    def test_stage_stream_degree_and_specialization_choose_suggestions(self):
        cases = [
            ({'education_level': '10th', 'stream': 'Commerce'}, 'domain_skills', {'accounting', 'tally', 'gst'}),
            ({'education_level': '10th', 'stream': 'Science'}, 'domain_skills', set()),
            ({'education_level': '10th', 'stream': 'Arts/Humanities'}, 'domain_skills', set()),
            ({'education_level': '10th', 'stream': 'Diploma/Vocational'}, 'domain_skills', set()),
            ({'education_level': '12th', 'stream': 'Commerce'}, 'domain_skills', {'accounting', 'tally', 'gst'}),
            ({'education_level': '12th', 'stream': 'Arts/Humanities'}, 'domain_skills', set()),
            ({'education_level': '12th', 'stream': 'Vocational/Diploma'}, 'domain_skills', set()),
            ({'education_level': '12th', 'stream': 'Science PCM'}, 'domain_skills', {'matlab', 'python', 'programming'}),
            ({'education_level': "Bachelor's", 'stream': 'Commerce', 'degree': 'B.Com', 'specialization': 'Finance'}, 'domain_skills', {'accounting', 'financial_analysis', 'finance'}),
            ({'education_level': "Bachelor's", 'stream': 'Business', 'degree': 'BBA', 'specialization': 'Business Analytics'}, 'domain_skills', {'business_analytics', 'power_bi', 'crm'}),
            ({'education_level': "Bachelor's", 'stream': 'Science', 'degree': 'BCA', 'specialization': 'Software Development'}, 'domain_skills', {'programming', 'sql', 'software_testing'}),
            ({'education_level': "Bachelor's", 'stream': 'Engineering', 'degree': 'B.Tech/BE', 'specialization': 'Mechanical Engineering'}, 'domain_skills', {'matlab', 'hardware', 'electronics'}),
            ({'education_level': "Bachelor's", 'stream': 'Arts/Humanities', 'degree': 'BA', 'specialization': 'Journalism'}, 'domain_skills', {'video_editing', 'digital_publishing', 'seo'}),
            ({'education_level': "Bachelor's", 'stream': 'Science', 'degree': 'B.Sc', 'specialization': 'Physics'}, 'domain_skills', {'matlab', 'hardware', 'data_analysis'}),
            ({'education_level': "Bachelor's", 'stream': 'Other', 'degree': 'B.Voc', 'specialization': 'Medical Laboratory Technology'}, 'domain_skills', {'laboratory_instrumentation'}),
            ({'education_level': "Bachelor's", 'stream': 'Other', 'degree': 'Other', 'specialization': 'Other'}, 'domain_skills', set()),
            ({'education_level': "Master's", 'stream': 'Computing', 'degree': 'MCA', 'specialization': 'Cybersecurity'}, 'domain_skills', {'cybersecurity', 'cloud_computing', 'software_testing'}),
            ({'education_level': "Master's", 'stream': 'Commerce', 'degree': 'M.Com', 'specialization': 'Accounting'}, 'domain_skills', {'accounting', 'tally', 'gst'}),
            ({'education_level': "Master's", 'stream': 'Arts/Humanities', 'degree': 'MA', 'specialization': 'Psychology'}, 'domain_skills', {'research_software', 'survey_tools', 'statistical_analysis'}),
        ]
        for profile, group, expected in cases:
            with self.subTest(profile=profile):
                catalog = education_skill_catalog(profile)
                self.assertTrue(expected.issubset(names(catalog[group])))
                self.assertIn('not curriculum requirements', catalog['notice'])
                self.assertEqual(len(names(catalog[group])), len(catalog[group]))

    def test_optional_and_employability_groups_are_available_and_separate(self):
        catalog = education_skill_catalog({'education_level': '12th', 'stream': 'Arts/Humanities'})
        self.assertIn('computer_literacy', names(catalog['general_digital_skills']))
        self.assertIn('python', names(catalog['advanced_self_acquired_skills']))
        self.assertIn('communication', names(catalog['employability_skills']))
        self.assertNotIn('communication', names(catalog['advanced_self_acquired_skills']))

    def test_each_existing_career_skill_has_explicit_project_guidance_classification(self):
        path = Path(__file__).resolve().parents[1] / 'data' / 'career_knowledge_base.csv'
        with path.open(encoding='utf-8', newline='') as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 25)
        for career in rows:
            technical = dict(part.split(':', 1) for part in career['technical_skills'].split(';') if ':' in part)
            employability = dict(part.split(':', 1) for part in career['employability_skills'].split(';') if ':' in part)
            guidance = career_skill_guidance(career['career_id'], technical, employability)
            self.assertEqual(set(guidance), set(technical) | set(employability), career['career_id'])
            self.assertTrue(all(item['classification'] in {'core', 'optional'} and item['trainable'] for item in guidance.values()))


if __name__ == '__main__':
    unittest.main()
