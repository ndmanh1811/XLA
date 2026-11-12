# Bằng chứng giao diện Fiji/FeatureJ

Đã chụp **15 PNG** ngày 12/11/2026 trên đúng bản Fiji dùng để hiệu chuẩn.
Ảnh giao diện là bằng chứng bổ sung; số đo định lượng vẫn lấy từ
`measurement_results.csv`, `kernel_profiles.csv` và các TIFF trong `outputs/`.

| PNG | Input/lệnh và tùy chọn | TIFF hoặc dữ liệu đối chiếu |
| --- | --- | --- |
| `01_fiji_imagej_version.png` | Cửa sổ Fiji/ImageJ đang chạy | `environment.csv`: ImageJ `2.16.0/1.54p`, Java `1.8.0_452` 64-bit |
| `02_featurej_imagescience_version.png` | Phiên bản đọc trực tiếp từ lớp plugin đã cài | FeatureJ `2.0.0`, ImageScience `3.0.0` |
| `03a_derivatives_ramp_lx_s2_dialog.png` | `ramp.tif`; Derivatives `x=1,y=0,z=0`, sigma `2.0` | `calib_ramp_lx_s2.0.tif` |
| `03_derivatives_ramp_lx_s2_roi.png` | ROI `(96,96,64,64)` trên output Lx | Dòng `ramp.tif,lx,2.0` trong `measurement_results.csv` |
| `04a_derivatives_parabola_lxx_s2_dialog.png` | `parabola.tif`; Derivatives `x=2,y=0,z=0`, sigma `2.0` | `calib_parabola_lxx_s2.0.tif` |
| `04_derivatives_parabola_lxx_s2_roi.png` | ROI `(96,96,64,64)` trên output Lxx | Dòng `parabola.tif,lxx,2.0` trong `measurement_results.csv` |
| `05_laplacian_parabola_s2_dialog.png` | `parabola.tif`; Compute bật, zero-crossings tắt, sigma `2.0` | `calib_parabola_lap_s2.0.tif` |
| `06_hessian_saddle_s2_dialog.png` | `saddle.tif`; Largest/Smallest bật, Middle/Absolute tắt, sigma `2.0` | `calib_saddle_hess-l1_s2.0.tif`, `calib_saddle_hess-l2_s2.0.tif` |
| `07_edges_ramp_s2_dialog.png` | `ramp.tif`; Compute bật, NMS tắt, hai ngưỡng trống, sigma `2.0` | `calib_ramp_grad_s2.0.tif` |
| `08_structure_ramp_sd1_si3_dialog.png` | `ramp.tif`; Largest/Smallest bật, `(sigma_d,sigma_i)=(1,3)` | `calib_ramp_st-l1_sd1.0_si3.0.tif`, `calib_ramp_st-l2_sd1.0_si3.0.tif` |
| `09_structure_ramp_sd2_si6_dialog.png` | `ramp.tif`; Largest/Smallest bật, `(sigma_d,sigma_i)=(2,6)` | `calib_ramp_st-l1_sd2.0_si6.0.tif`, `calib_ramp_st-l2_sd2.0_si6.0.tif` |
| `10_profile_dirac_gauss_s2.png` | Profile ngang qua tâm Dirac, Gaussian sigma `2.0` | `calib_dirac_gauss_s2.0.tif`; các dòng `dirac.tif,gauss,2.0` trong `kernel_profiles.csv` |
| `11_profile_dirac_lx_s2.png` | Profile ngang qua tâm Dirac, Lx sigma `2.0` | `calib_dirac_lx_s2.0.tif`; các dòng `dirac.tif,lx,2.0` |
| `12_profile_dirac_lxx_s2.png` | Profile ngang qua tâm Dirac, Lxx sigma `2.0` | `calib_dirac_lxx_s2.0.tif`; các dòng `dirac.tif,lxx,2.0` |
| `13_profile_bright_border_gauss_s2.png` | Profile ngang qua giữa ảnh sát hai biên, Gaussian sigma `2.0` | `calib_bright_border_gauss_s2.0.tif`; các dòng `bright_border.tif,gauss,2.0` |

Kết luận kiểu biên còn đối chiếu đầy đủ các profile Gaussian/Lx/Lxx ở sigma
`1,2,4` trong `kernel_profiles.csv`; PNG cuối chỉ là ảnh giao diện đại diện.

