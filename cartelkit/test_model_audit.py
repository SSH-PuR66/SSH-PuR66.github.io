"""Checks for the independent audit's identities and explicit boundaries."""
from fractions import Fraction as F
import json
import math
from pathlib import Path
import unittest
import model_audit as audit

DATA=json.loads((Path(__file__).parent/'model-audit.json').read_text(encoding='utf-8'))

class ModelAuditChecks(unittest.TestCase):
    def test_aggregate_count_and_expected_means(self):
        rows=DATA['sentences']['distribution']
        self.assertEqual(sum(n for _,n in rows),40297)
        weighted=audit.sentence_stats(rows)
        self.assertAlmostEqual(weighted['assigned_years'],8.713438481497516,places=12)
        self.assertAlmostEqual(audit.sentence_stats(rows,inverse=False)['assigned_years'],20.085401311905255,places=12)
        self.assertEqual(DATA['sentences']['unique_lengths'],len(rows))

    def test_independent_harmonic_mean_identity(self):
        values=DATA['sentences']['distribution']
        expected=sum(n for _,n in values)/math.fsum(n/s for s,n in values)
        self.assertAlmostEqual(audit.sentence_stats(values)['assigned_years'],expected,places=12)

    def test_age_changes_cap_not_assignment(self):
        values=DATA['sentences']['distribution']
        young=audit.sentence_stats(values,15)
        old=audit.sentence_stats(values,60)
        self.assertEqual(young['assigned_years'],old['assigned_years'])
        self.assertGreater(young['capped_years'],old['capped_years'])
        self.assertLess(young['probability_beyond_age_69'],old['probability_beyond_age_69'])

    def test_age_limit_and_multiplier(self):
        rows=DATA['sentences']['distribution']
        self.assertEqual(audit.sentence_stats(rows,69)['capped_years'],0)
        self.assertAlmostEqual(audit.sentence_stats(rows,multiplier=2)['assigned_years'],2*audit.sentence_stats(rows)['assigned_years'],places=12)

    def test_known_distribution_caps_and_weights(self):
        values=[[1.,1],[20.,1]]
        result=audit.sentence_stats(values,age=60)
        self.assertAlmostEqual(result['assigned_years'],40/21)
        self.assertAlmostEqual(result['capped_years'],29/21)
        self.assertAlmostEqual(result['probability_beyond_age_69'],1/21)

    def test_source_byte_mutation_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity'):
            audit.verify_bytes('ENPOL sentences.csv',b'fabricated dataset')

    def test_invalid_sensitivity_inputs(self):
        for age,multiplier in ((14,1),(70,1),(40,0),(40,4),(float('nan'),1),(40,float('inf'))):
            with self.subTest(age=age,multiplier=multiplier),self.assertRaises(ValueError):
                audit.sentence_stats([[1,1]],age,multiplier)

    def test_full_equation_identity_with_asymmetric_network(self):
        result=audit.check_symmetry()
        self.assertEqual(result['exact_rational_cases'],20)
        self.assertEqual(result['trajectory_cases'],4)
        self.assertLess(result['max_relative_trajectory_error'],1e-12)

    def test_unscaled_eta_breaks_equivariance(self):
        c=[F(2),F(3)]
        p=[F(1,10),F(1,5),F(1,100),F(1,50)]
        network=[[F(0),F(2)],[F(1),F(0)]]
        scaled,q=audit.transformed(c,p,F(2))
        q[1]=p[1]
        self.assertNotEqual(audit.rhs(scaled,q,network),[2*x for x in audit.rhs(c,p,network)])

    def test_fixed_absolute_target_does_not_have_identical_residual(self):
        # A perfect fit at one assumed target is not a perfect fit after output rescaling alone.
        target=F(120); original_output=F(120); k=F(2)
        self.assertEqual((original_output-target)**2,0)
        self.assertGreater((k*original_output-target)**2,0)
        residual=F(117)-target
        self.assertEqual((k*F(117)-k*target)**2,k*k*residual*residual)

    def test_nonpositive_state_is_explicitly_outside_audit(self):
        with self.assertRaises(ValueError): audit.rhs([0],[1,1,1,1],[[0]])

    def test_public_aggregate_has_no_person_or_location_fields(self):
        for row in DATA['sentences']['distribution']:
            self.assertEqual(len(row),2)
            self.assertGreater(row[0],0)
            self.assertIsInstance(row[1],int)
        self.assertNotIn('ID_PER',json.dumps(DATA))
        self.assertFalse(DATA['scope']['full_R_model_executed'])
        self.assertFalse(DATA['scope']['new_cartel_population_estimate'])

    def test_approximate_policy_arithmetic_is_same_year(self):
        base=DATA['baseline']
        self.assertAlmostEqual((base['double_incapacitation_index']/base['unchanged_index']-1)*100,-22.85714285714286)

if __name__=='__main__': unittest.main()
