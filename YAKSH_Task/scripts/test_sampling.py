"""Small algorithm tests; the saved outputs are independently integration-checked."""
import unittest
from build_data import stratified, skew, number
from sampling_quality import refine, measure, assert_limits, distance, profile
import collections

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

    def workload_fixture(self):
        return [{'task_group_id':f'{b}-{i}', 'time_bin':b,'resource_skew':'balanced','multiplicity_band':'2-100',
                 'instance_num':i+1,'cpu_request_cores':.5+(i%2)*.25,'memory_request_normalized':.01*(1+i%3),'duration_s':2*(i+1)}
                for b in range(4) for i in range(20)]

    def test_group_counts_do_not_hide_weighted_burst_failure(self):
        rows=self.workload_fixture();sample=[rows[0],rows[20],rows[59],rows[79]]
        self.assertEqual(distance(profile(rows,'time_bin'),profile(sample,'time_bin')),0)
        with self.assertRaises(ValueError):assert_limits(measure(rows,sample),{'instance_time_bin_total_variation':.10})

    def test_refinement_preserves_source_rows_and_quotas(self):
        rows=self.workload_fixture();initial=[rows[0],rows[20],rows[59],rows[79]]
        result,_=refine(rows,initial,560)
        self.assertEqual(len({r['task_group_id'] for r in result}),len(initial))
        self.assertTrue(all(r in rows for r in result))
        cells=lambda data:collections.Counter((r['time_bin'],r['resource_skew']) for r in data)
        self.assertEqual(cells(result),cells(initial))
        self.assertLess(measure(rows,result)['instance_time_bin_total_variation'],measure(rows,initial)['instance_time_bin_total_variation'])

    def test_refinement_is_invariant_to_input_order(self):
        rows=self.workload_fixture();initial=[rows[0],rows[20],rows[59],rows[79]]
        self.assertEqual(refine(rows,initial,560),refine(list(reversed(rows)),list(reversed(initial)),560))

if __name__=='__main__':unittest.main()
