"""Script chạy toàn bộ kiểm thử unit test cho module src.core."""

import importlib.util
import sys

sys.stdout.reconfigure(encoding="utf-8")


def run_all():
  print("=" * 60)
  print("CHẠY UNIT TEST KIỂM THỬ THUẬT TOÁN CỐT LÕI (src.core)")
  print("=" * 60)

  spec = importlib.util.spec_from_file_location(
      "test_core", "tests/test_core.py"
  )
  t = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(t)

  tests = [
      (
          "1. Kiểm tra bảo toàn moment kernel Gaussian 1D (order 0, 1, 2)",
          t.test_kernel_moments,
      ),
      (
          "2. Kiểm tra tích chập tách rời 2D đối chuẩn với SciPy (< 1e-14)",
          t.test_convolution_vs_scipy,
      ),
      (
          "3. Kiểm chứng giải tích trên ảnh đa thức (Ramp, Parabol, Saddle)",
          t.test_analytical_polynomials,
      ),
      (
          "4. Kiểm tra Structure Tensor & Coherence trên gradient chuẩn",
          t.test_structure_tensor,
      ),
      (
          "5. Smoke test 3 hàm dò mức cao (Canny, Frangi, Blob LoG)",
          t.test_detectors_smoke,
      ),
  ]

  passed = 0
  for desc, test_fn in tests:
    try:
      test_fn()
      print(f"[OK] {desc}")
      passed += 1
    except Exception as e:
      print(f"[FAIL] {desc}")
      print(f"       Chi tiết lỗi: {e}")

  print("=" * 60)
  print(f"KẾT QUẢ: {passed}/{len(tests)} bài test đạt chuẩn!")
  print("=" * 60)
  return passed == len(tests)


if __name__ == "__main__":
  success = run_all()
  sys.exit(0 if success else 1)
