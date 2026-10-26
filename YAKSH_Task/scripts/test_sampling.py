"""Small algorithm tests; the saved outputs are independently integration-checked."""
import unittest
from build_data import stratified, skew, number

class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':str(i),'group':i%7,'mix':i%3} for i in range(100)]
    def sample(self, rows, n=23, seed=560):
        return stratified(rows,n,lambda r:r['group'],seed,lambda r:r['id'],lambda r:r['mix'])
    def test_invariant_to_input_order(self):
        self.assertEqual(self.sample(self.rows),self.sample(list(reversed(self.rows))))
    def test_marginal_quotas(self):
        s=self.sample(self.rows)
        self.assertEqual(len(s),23)
        for k in range(3):
            self.assertLessEqual(abs(sum(r['mix']==k for r in s)-23*sum(r['mix']==k for r in self.rows)/100),1)
    def test_no_duplication_or_mutation(self):
        s=self.sample(self.rows);self.assertEqual(len({r['id'] for r in s}),len(s));self.assertTrue(all(r in self.rows for r in s))
    def test_seed_changes_selection(self):
        self.assertNotEqual(self.sample(self.rows),self.sample(self.rows,seed=561))
    def test_all_and_one(self):
        self.assertEqual(len(self.sample(self.rows,100)),100);self.assertEqual(len(self.sample(self.rows,1)),1)
    def test_reject_impossible_size(self):
        for n in (0,101):
            with self.assertRaises(ValueError):self.sample(self.rows,n)
    def test_skew_compares_host_fractions(self):
        self.assertEqual(skew(1,.01,64,.64,2),'balanced')
        self.assertEqual(skew(8,.01,64,.64,2),'cpu_heavy')
        self.assertEqual(skew(.5,.1,64,.64,2),'memory_heavy')
    def test_nonfinite_values(self):
        for x in ('','nan','inf','oops'):self.assertIsNone(number(x))
    def test_rare_capacity_is_preserved(self):
        rows=[{'id':str(i),'capacity':'common' if i<100 else 'rare'} for i in range(101)]
        sample=stratified(rows,10,lambda r:r['capacity'],560,lambda r:r['id'],lambda r:r['capacity'],True)
        self.assertEqual(len(sample),10)
        self.assertEqual({r['capacity'] for r in sample},{'common','rare'})

if __name__=='__main__':unittest.main()
