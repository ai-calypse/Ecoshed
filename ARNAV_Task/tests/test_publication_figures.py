"""Publication figures use actual evidence; no workload/scheduler execution."""
import json
from pathlib import Path
import tempfile
import unittest

from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT, POLICIES
from ARNAV_Task.publication.figures import metric_grid, streaming_figures, research_figures
from ARNAV_Task.publication.style import configure, save_figure, plt
from ARNAV_Task.publication.diagrams import architecture_figures, mermaid


class PublicationFigureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=ResearchArtifacts();cls.cfg=json.loads((ROOT/'ARNAV_Task/config/publication.json').read_text());configure(cls.cfg)
        cls.p4=json.loads((ROOT/'ARNAV_Task/reports/phase4_verification.json').read_text())
        cls.p5=json.loads((ROOT/'ARNAV_Task/reports/phase5_verification.json').read_text())

    def tearDown(self):plt.close('all')

    def test_active_policy_selection(self):
        spec=metric_grid(self.a,'test','Energy',['energy_kwh'],['kWh'])
        self.assertEqual(len(spec.data),36);self.assertEqual({r['policy'] for r in spec.data},set(POLICIES))

    def test_figure_values_match_adapter(self):
        spec=metric_grid(self.a,'test','Energy',['energy_kwh'],['kWh'])
        for r in spec.data:self.assertEqual(r['energy_kwh'],self.a.index[(r['workload_groups'],r['power_curve'],r['policy'])]['energy_kwh'])
        heights=[p.get_height() for p in spec.figure.axes[0].patches]
        expected=[self.a.index[(s,'hpe_dl360_gen9',p)]['energy_kwh'] for p in POLICIES for s in (250,1000,4000)]
        self.assertEqual(heights,expected)

    def test_missing_metric_is_not_zero(self):
        spec=metric_grid(self.a,'test','Unavailable',['unsupported_metric'],['Unavailable'])
        import math
        self.assertTrue(all(math.isnan(p.get_height()) for p in spec.figure.axes[0].patches))

    def test_three_readable_formats(self):
        spec=metric_grid(self.a,'test','Energy',['energy_kwh'],['kWh'])
        with tempfile.TemporaryDirectory() as tmp:
            paths=save_figure(spec.figure,Path(tmp),'test',self.cfg)
            self.assertEqual({p.suffix for p in paths},{'.png','.pdf','.svg'})
            from PIL import Image
            with Image.open(Path(tmp)/'test.png') as image:self.assertGreaterEqual(image.info['dpi'][0],299)

    def test_byte_identical_figure_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            before={}
            for i in range(2):
                spec=metric_grid(self.a,'test','Energy',['energy_kwh'],['kWh'])
                paths=save_figure(spec.figure,Path(tmp),'test',self.cfg)
                now={p.suffix:p.read_bytes() for p in paths}
                if i:self.assertEqual(before,now)
                before=now

    def test_missing_streaming_history_skips_only_optional_plot(self):
        specs=list(streaming_figures(self.p4,self.p5,None))
        self.assertEqual([s.identifier for s in specs],['S01_fast_replay','S02_integrity_recovery','S03_browser_timed_replay'])

    def test_streaming_uses_receipt_values(self):
        spec=next(streaming_figures(self.p4,self.p5))
        self.assertEqual(spec.data[0]['elapsed_wall_s'],self.p4['integration']['workloads'][0]['metrics']['elapsed_wall_s'])
        self.assertIn('not',spec.caption);self.assertEqual(spec.evidence,'Kafka transport verification')

    def test_architecture_editable_and_connected(self):
        specs=list(architecture_figures());self.assertEqual(len(specs),4)
        for spec in specs:
            source=mermaid(spec.data);self.assertTrue(source.startswith('flowchart LR'))
            self.assertIn('-->',source);self.assertGreater(len(spec.figure.axes[0].patches),5)

    def test_primary_figure_preserves_negative_results(self):
        generator=research_figures(self.a,self.cfg)
        next(generator);next(generator);spec=next(generator)
        self.assertEqual(len(spec.data),9)
        self.assertEqual(sum(r['energy_reduction_pct']>0 for r in spec.data),4)
        self.assertTrue(all(r['energy_reduction_pct']<0 for r in spec.data if r['workload_groups']==4000))

    def test_plot_inventory_all_supported_categories(self):
        specs=list(research_figures(self.a,self.cfg))
        self.assertEqual(len(specs),15)
        self.assertEqual(len({s.identifier for s in specs}),15)
        resources=next(s for s in specs if s.identifier=='R13_resource_outcomes')
        self.assertFalse(any(r['workload_groups']==250 and r['task_type']=='cpu_heavy' for r in resources.data))
        self.assertIn('No observations',resources.caption)
