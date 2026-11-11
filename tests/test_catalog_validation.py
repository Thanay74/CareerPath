import unittest

from backend.catalog_validation import validate_education_catalog, validate_project_catalogs


class CatalogValidationTests(unittest.TestCase):
    def test_current_project_catalogs_validate_without_rewriting_sources(self):
        from backend.catalog_validation import CAREER_CSV, CAREER_METADATA
        before=(CAREER_CSV.read_bytes(),CAREER_METADATA.read_bytes())
        self.assertEqual(validate_project_catalogs(),[])
        self.assertEqual((CAREER_CSV.read_bytes(),CAREER_METADATA.read_bytes()),before)

    def test_education_validator_catches_duplicate_identifiers_and_bad_references(self):
        catalog={
            '10th':{'streams':['Science','Science'],'degrees':[],'specializations':{},'subjects':{'default':['math','math']}},
            '12th':{'streams':['Commerce'],'degrees':[],'specializations':{},'subjects':{'Unknown':['economics']}},
            "Bachelor's":{'streams':[],'degrees':['BCA'],'specializations':{'Unknown':['Focus']},'subjects':{'BCA|Missing':['code']}},
            "Master's":{'streams':[],'degrees':[],'specializations':{},'subjects':{'Other':['x']}},
        }
        errors=validate_education_catalog(catalog)
        self.assertTrue(any('duplicate stream' in item for item in errors))
        self.assertTrue(any('duplicate subject' in item for item in errors))
        self.assertTrue(any('unknown stream' in item for item in errors))
        self.assertTrue(any('unknown degree' in item for item in errors))
        self.assertTrue(any('unknown degree/specialization' in item for item in errors))

    def test_career_validator_catches_duplicate_ids_and_invalid_scores_without_touching_files(self):
        from backend.catalog_validation import CAREER_CSV, CAREER_FIELDS, validate_career_records
        original=CAREER_CSV.read_bytes()
        record={field:'' for field in CAREER_FIELDS}
        record.update(career_id='C999',career_name='Example',minimum_education_level="Bachelor's",aptitude_requirements='logic:0',technical_skills='python:50',employability_skills='',interest_requirements='')
        errors=validate_career_records([record,{**record,'technical_skills':'python:101'}])
        self.assertTrue(any('duplicate career_id' in item for item in errors))
        self.assertTrue(any('between 0 and 100' in item for item in errors))
        self.assertEqual(CAREER_CSV.read_bytes(),original)


if __name__=='__main__': unittest.main()
