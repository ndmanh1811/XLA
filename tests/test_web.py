"""Regression tests for the web's data/metric contract, independent of UI styling."""
import copy
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import tifffile
from src.eval.metric_utils import strict_config, write_csv
from src.web import app as web
from src.web.comparison import build_reference, compare_maps, shared_limits, align_fiji
from src.web.parameters import web_settings, validate_request
from src.web import comparison


class WebComparisonTests(unittest.TestCase):
    def setUp(self):
        self.cfg = strict_config()

    def save(self, folder, name, array):
        tifffile.imwrite(Path(folder)/name, np.asarray(array,dtype=np.float32), compression=None)

    def reference(self, folder, algo, dtype=None, sigma=2, **kwargs):
        return build_reference('bsds_03',algo,dtype,sigma,1,3,(4,4),self.cfg,
                               directory=folder,**kwargs)

    def test_canny_uses_lx_ly_and_never_native_edges(self):
        with tempfile.TemporaryDirectory() as d:
            self.save(d,'fiji_bsds_03_lx_s2.0.tif',np.full((4,4),3))
            self.save(d,'fiji_bsds_03_ly_s2.0.tif',np.full((4,4),4))
            self.save(d,'fiji_bsds_03_edge_s2.0.tif',np.full((4,4),99))
            array,meta,_=self.reference(d,'canny')
            np.testing.assert_array_equal(array,np.full((4,4),10))
            self.assertTrue(meta['has_fiji'])
            self.assertFalse(any('_edge_' in f for f in meta['files']))

    def test_angle_is_atan2_of_matching_components(self):
        with tempfile.TemporaryDirectory() as d:
            self.save(d,'fiji_bsds_03_lx_s2.0.tif',np.zeros((4,4)))
            self.save(d,'fiji_bsds_03_ly_s2.0.tif',np.ones((4,4)))
            self.save(d,'fiji_bsds_03_grad_s2.0.tif',np.full((4,4),99))
            array,_,valid=self.reference(d,'gradient',dtype='angle')
            np.testing.assert_allclose(array,np.pi/2)
            self.assertTrue(valid.all())

    def test_incomplete_blob_stack_does_not_become_single_laplacian(self):
        with tempfile.TemporaryDirectory() as d:
            self.save(d,'fiji_bsds_03_lap_s2.0.tif',np.ones((4,4)))
            result,meta,_=self.reference(d,'blob',scales=[1.,2.,4.])
            self.assertIsNone(result)
            self.assertFalse(meta['has_fiji'])

    def test_incomplete_hessian_pair_does_not_become_frangi(self):
        with tempfile.TemporaryDirectory() as d:
            self.save(d,'fiji_bsds_03_hess-l2_s2.0.tif',np.ones((4,4)))
            result,meta,_=self.reference(d,'frangi',scales=[2.])
            self.assertIsNone(result)
            self.assertFalse(meta['has_fiji'])

    def test_scale_lookup_does_not_round_to_unrequested_tiff(self):
        with tempfile.TemporaryDirectory() as d:
            self.save(d,'fiji_bsds_03_gauss_s1.0.tif',np.ones((4,4)))
            result,meta,_=self.reference(d,'gaussian',sigma=1.04)
            self.assertIsNone(result)
            self.assertFalse(meta['has_fiji'])

    def test_live_reference_rejects_changed_config_provenance(self):
        with patch.object(comparison,'_reference_registry',return_value=('not the current hash',{})):
            result,meta,_=build_reference('bsds_03','canny',None,2,1,3,(4,4),self.cfg)
        self.assertIsNone(result)
        self.assertIn('Config',meta['message'])

    def test_live_reference_rejects_unverified_tiff_checksum(self):
        with patch.object(comparison,'_reference_registry',return_value=(comparison.sha256(comparison.ROOT/'config.yaml'),{})):
            result,meta,_=build_reference('bsds_03','canny',None,2,1,3,(4,4),self.cfg)
        self.assertIsNone(result)
        self.assertIn('checksum',meta['message'])

    def test_normalization_flag_applies_exactly_once_in_both_modes(self):
        a=np.ones((3,3))
        self.cfg['featurej_normalized']['laplacian']=False
        np.testing.assert_equal(align_fiji(a,2,2,'laplacian',self.cfg,True),a*4)
        self.cfg['featurej_normalized']['laplacian']=True
        np.testing.assert_equal(align_fiji(a,2,2,'laplacian',self.cfg,True),a)
        np.testing.assert_equal(align_fiji(a,2,2,'laplacian',self.cfg,False),a/4)

    def test_constant_pearson_is_undefined_even_for_equal_arrays(self):
        for b in (np.ones((4,4)),np.full((4,4),2)):
            _,metrics=compare_maps(np.ones((4,4)),b)
            self.assertIsNone(metrics['pearson'])

    def test_periodic_angle_error_does_not_cross_two_pi(self):
        _,metrics=compare_maps(np.array([[np.pi-.01]]),np.array([[-np.pi+.01]]),angular=True)
        self.assertAlmostEqual(metrics['mae'],.02)
        self.assertIsNone(metrics['pearson'])

    def test_zero_gradient_angle_has_no_valid_numeric_score(self):
        _,metrics=compare_maps(np.zeros((3,3)),np.zeros((3,3)),angular=True,valid=np.zeros((3,3),bool))
        self.assertIsNone(metrics['mae'])
        self.assertIsNone(metrics['mean_angular_error_deg'])
        self.assertEqual(metrics['valid_pixels'],0)

    def test_shared_range_preserves_amplitude_difference_and_sign(self):
        a=np.arange(16.).reshape(4,4);b=a*2
        lo,hi=shared_limits(a,b)
        self.assertNotEqual(web.array_to_base64_png(a,vmin=lo,vmax=hi),web.array_to_base64_png(b,vmin=lo,vmax=hi))
        self.assertEqual(shared_limits(-a,b,signed=True),(-30.,30.))


class WebRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.settings=web_settings()

    def setUp(self):
        self.client=web.app.test_client()

    def test_invalid_inputs_are_json_400(self):
        inputs=[None,[],{'algorithm':'unknown'}, {'algorithm':[]}, {'sigma':'abc'}, {'sigma':0},
                {'sigma':float('nan')}, {'p_low':95,'p_high':10},
                {'sigma':True},{'use_fov':'false'},{'beta':0}]
        for data in inputs:
            with self.subTest(data=data):
                r=self.client.post('/api/process',json=data)
                self.assertEqual(r.status_code,400)
                self.assertIn('error',r.get_json())

    def test_dark_blob_default_comes_from_annotation(self):
        for name in ('blob_02','blob_04'):
            p=validate_request(dict(image_id=name,algorithm='blob'),self.settings)
            self.assertEqual(p['polarity'],'dark')

    def test_corrupted_upload_returns_json_400(self):
        r=self.client.post('/api/upload',data={'file':(io.BytesIO(b'not png'),'bad.png')})
        self.assertEqual(r.status_code,400)
        self.assertIn('error',r.get_json())

    def test_upload_ids_are_unique_and_result_echoes_selection(self):
        with tempfile.TemporaryDirectory() as d, patch.object(web,'UPLOAD_DIR',Path(d)):
            ids=[]
            for _ in range(2):
                b=io.BytesIO();Image.fromarray(np.zeros((16,16),dtype=np.uint8)).save(b,format='PNG');b.seek(0)
                r=self.client.post('/api/upload',data={'file':(b,'same.png')})
                self.assertEqual(r.status_code,200);ids.append(r.get_json()['id'])
            self.assertNotEqual(*ids)
            response=self.client.post('/api/process',json=dict(image_id=ids[0],algorithm='gaussian',sigma=1))
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.get_json()['request_context'],dict(image_id=ids[0],algorithm='gaussian'))

    def test_benchmark_fails_closed_when_manifest_is_invalid(self):
        with patch.object(web,'verify_metric_delivery',side_effect=ValueError('changed input')):
            r=self.client.get('/api/benchmarks')
            self.assertEqual(r.status_code,503)
            self.assertIn('changed input',r.get_json()['error'])

    def test_benchmark_headlines_and_classification_are_from_csv(self):
        with tempfile.TemporaryDirectory() as d, patch.object(web,'RESULTS',Path(d)), patch.object(web,'ROOT',Path(d)), patch.object(web,'verify_metric_delivery'):
            write_csv(Path(d)/'tier1_report.csv',[
                dict(status='PASS',relative_error=1e-6,pearson_r=1),
                dict(status='FAIL',relative_error=.001,pearson_r=1),
                dict(status='FAIL',relative_error=.1,pearson_r=1)])
            rows=[dict(source='python',task=task,sigma=sigma,macro_f1=score,micro_f1=score)
                  for task,sigma,score in [('edge_bsds',2,.1234),('ridge_drive','multiscale',.2345),('blob_log','multiscale',.3456)]]
            write_csv(Path(d)/'tier2_summary.csv',rows)
            write_csv(Path(d)/'tier2_comparison.csv',[dict(task='fixture')])
            (Path(d)/'run_manifest.json').write_text('{}')
            r=self.client.get('/api/benchmarks')
            self.assertEqual(r.status_code,200)
            data=r.get_json()
            self.assertEqual(float(data['headlines']['edge']['macro_f1']),.1234)
            self.assertEqual(data['tier1_counts'],dict(total=3,strict=1,strict_failed=2,relaxed=1,outside_relaxed=1))

    def test_frangi_component_time_is_measured_not_a_fixed_split(self):
        with tempfile.TemporaryDirectory() as d, patch.object(web,'UPLOAD_DIR',Path(d)):
            Image.fromarray(np.zeros((16,16),dtype=np.uint8)).save(Path(d)/'custom_timing.png')
            z=np.zeros((16,16))
            def slow_detector(*args,**kwargs):
                time.sleep(.02)
                return z.copy()
            with patch.object(web,'compute_derivatives_2nd',return_value=(z,z,z)), patch.object(web,'detect_ridge',side_effect=slow_detector):
                r=self.client.post('/api/process',json=dict(image_id='custom_timing',algorithm='frangi'))
            self.assertEqual(r.status_code,200)
            timing=r.get_json()['timing']
            self.assertGreater(timing['detector_ms'],timing['derivative_ms'])


if __name__=='__main__':
    unittest.main()
