# Group 2 — Phân tích biến động giá vàng Việt Nam (2010–2025)

Dự án nghiên cứu tác động bất đối xứng của các biến kinh tế vĩ mô lên **biến động giá vàng** tại Việt Nam trong giai đoạn 2010–2025, sử dụng mô hình **ARX(1)-EGARCHX(1,1)** ước lượng theo từng giai đoạn (sub-sample).

---

## Câu hỏi nghiên cứu

> *Các cú sốc kinh tế vĩ mô (giá dầu, tỷ giá, VN-Index, CPI, M2, lãi suất) tác động bất đối xứng lên biến động giá vàng như thế nào, và liệu tác động này có thay đổi theo regime kinh tế hay không?*

---

## Dữ liệu

| File | Mô tả | Số quan sát | Số cột |
|------|-------|-------------|--------|
| `g2data_final.csv` | Bộ dữ liệu gốc | ~3,845 | — |
| `g2data_asymmetric_final.csv` | Dữ liệu cho mô hình Asymmetric (biến `_pos`/`_neg`) | 3,845 | 25 |
| `g2data_quantile_final.csv` | Dữ liệu cho mô hình Quantile (biến `_5`/`_95`) | 3,845 | 25 |

**Phạm vi**: 01/10/2010 – 30/06/2025 (tần suất ngày)

**Biến phụ thuộc**: `dlog_GoldPrice` — log-return hàng ngày của giá vàng (%)

**Biến độc lập** (6 biến kinh tế vĩ mô):

| Biến gốc | Ý nghĩa |
|----------|---------|
| `dlog_OilPrice` | Log-return giá dầu Brent |
| `dlog_ExchangeRate` | Log-return tỷ giá USD/VND |
| `dlog_VNIndex` | Log-return chỉ số VN-Index |
| `d_CPI` | Thay đổi chỉ số giá tiêu dùng |
| `d_IR` | Thay đổi lãi suất |
| `dlog_M2` | Log-return cung tiền M2 |

**Biến phân rã** — Trong phương trình variance, mỗi biến được tách thành 2 chiều:
- Mô hình Asymmetric: `_pos` (shocks dương) và `_neg` (shocks âm)
- Mô hình Quantile: `_5` (percentile thứ 5) và `_95` (percentile thứ 95)

---

## Phân chia giai đoạn (Sub-sample)

Chuỗi được chia thành 3 windows dựa trên 2 breakpoints (2014-12-31 và 2020-01-01):

| Window | Giai đoạn | Số quan sát | Bối cảnh kinh tế |
|--------|-----------|-------------|-----------------|
| **W1** | Oct 2010 – Dec 2014 | ~1,108 | Hậu GFC, gold crash ($1,800→$1,200), oil collapse |
| **W2** | Jan 2015 – Dec 2019 | ~1,303 | Low-volatility regime, US-China trade war |
| **W3** | Jan 2020 – Jun 2025 | ~1,431 | COVID-19, Ukraine War, gold all-time highs (>$3,000) |

### Tại sao phải chia giai đoạn?

Hillebrand (2005, *Journal of Econometrics*) chứng minh rằng nếu chuỗi có structural break trong variance nhưng ước lượng bằng 1 GARCH model duy nhất, persistence parameter β bị **upward biased** (β → 1), tạo ra "spurious near-integrated GARCH." Lamoureux & Lastrapes (1990, *JBES*) xác nhận finding tương tự trên dữ liệu stock returns.

---

## Mô hình

### Cấu trúc tổng quát: ARX(1)-EGARCHX(1,1)

**Mean equation (ARX):**
$$\text{dlog\_GoldPrice}_t = \mu + \beta_1 \cdot \text{dlog\_GoldPrice}_{t-1} + \sum_{i} \beta_i \cdot X_{i,t-1} + \varepsilon_t$$

**Variance equation (EGARCHX):**
$$\log(\sigma^2_t) = \omega + \alpha |z_{t-1}| + \gamma z_{t-1} + \beta \log(\sigma^2_{t-1}) + \sum_{i} \delta_i \cdot \text{Exog}_i$$

Trong đó $z_{t-1} = \varepsilon_{t-1}/\sigma_{t-1}$ là standardized residual.

| Parameter | Ý nghĩa |
|-----------|---------|
| ω (omega) | Hằng số trong variance equation |
| α (alpha) | ARCH effect — độ nhạy với shock gần đây |
| γ (gamma) | Leverage/asymmetric effect — phân biệt shock dương/âm |
| β (beta) | GARCH persistence — độ dai dẳng của volatility |
| δᵢ | Tác động của external regressors lên volatility |

**Ước lượng**: Quasi-Maximum Likelihood (QML) qua package `rugarch` trong R, chạy thông qua `rpy2`.

**Diagnostic tests** (sau mỗi window):
- Ljung-Box Q(10) — kiểm tra autocorrelation trong residuals
- ARCH-LM Q²(10) — kiểm tra remaining heteroskedasticity
- Engle-Ng Sign Bias Test — kiểm tra remaining asymmetric effect

---

## Cấu trúc file

```
Group-2-Timeseries/
├── Breakpoint_Justification.ipynb      ← Bước 1: Justify breakpoints (chạy trước)
├── model_asymmetric_group2.ipynb       ← Bước 2a: Mô hình Asymmetric (_pos/_neg)
├── model_quantile_group2.ipynb         ← Bước 2b: Mô hình Quantile (_5/_95)
├── Structural_Break_Tests_v2.ipynb     ← Tham khảo: phân tích tổng quát (không cần chạy)
├── g2data_final.csv                    ← Dữ liệu gốc
├── g2data_asymmetric_final.csv         ← Input cho model_asymmetric
└── g2data_quantile_final.csv           ← Input cho model_quantile
```

### Mô tả từng notebook

**`Breakpoint_Justification.ipynb`** — Notebook cốt lõi về kiểm định cấu trúc

Validates 2 breakpoints đã chọn (2014-12-31, 2020-01-01) bằng 5 tests độc lập:

| Test | Kiểm tra |
|------|---------|
| Chow Test (Chow, 1960) | Mean equation parameters có thay đổi tại breakpoint? |
| Levene Test (Brown & Forsythe, 1974) | Variance có khác nhau trước/sau breakpoint? |
| Mann-Whitney U (Mann & Whitney, 1947) | Toàn bộ distribution có khác nhau? |
| ARCH-LM per window (Engle, 1982) | ARCH effect tồn tại ở cả 2 bên breakpoint? |
| Proximity to data-driven (Andrews, 1993 + PELT) | Breakpoint có gần với kết quả data-driven? |

Kết quả ≥ 3/5 tests confirm → breakpoint **justified**.

---

**`model_asymmetric_group2.ipynb`** — Mô hình Asymmetric

- Input: `g2data_asymmetric_final.csv` (biến `_pos`/`_neg`)
- External regressors trong variance: `dlog_OilPrice_pos`, `dlog_OilPrice_neg`, ..., `d_IR_pos`, `d_IR_neg`
- Chạy tuần tự `run_model_window1()`, `run_model_window2()`, `run_model_window3()`

**`model_quantile_group2.ipynb`** — Mô hình Quantile

- Input: `g2data_quantile_final.csv` (biến `_5`/`_95`)
- External regressors trong variance: `dlog_OilPrice_5`, `dlog_OilPrice_95`, ..., `d_IR_5`, `d_IR_95`
- Cấu trúc tương tự model_asymmetric, chỉ khác cách phân rã biến

**`Structural_Break_Tests_v2.ipynb`** — Phân tích tổng quát (tham khảo)

Notebook này là bước tiền nghiên cứu (trả lời câu hỏi "break có tồn tại không?" mà không biết trước vị trí). Nội dung thống kê của nó (Andrews Sup-F, PELT, Levene, ARCH-LM) đã được tích hợp đầy đủ vào `Breakpoint_Justification.ipynb`. Không cần chạy file này nếu đã quyết định breakpoints.

---

## Kết quả mô hình

### Model Asymmetric — Tóm tắt 3 Windows

| Window | Obs | AIC | BIC | Log-Likelihood |
|--------|-----|-----|-----|----------------|
| W1 (2010–2014) | 1,108 | 2.0457 | 2.1542 | −1,109.29 |
| W2 (2015–2019) | 1,303 | 0.7872 | 0.8785 | −489.88 |
| W3 (2020–2025) | 1,431 | 1.6203 | 1.7086 | −1,135.29 |

### Model Quantile — Tóm tắt 3 Windows

| Window | Obs | AIC | BIC | Log-Likelihood |
|--------|-----|-----|-----|----------------|
| W1 (2010–2014) | 1,108 | 2.0562 | 2.1647 | −1,115.13 |
| W2 (2015–2019) | 1,303 | 0.7948 | 0.8861 | −494.82 |
| W3 (2020–2025) | 1,431 | 1.6137 | 1.7020 | −1,130.58 |

Tất cả 6 windows (3 per model) đều **pass** cả 3 diagnostic tests (Ljung-Box, ARCH-LM, Engle-Ng Sign Bias, p > 0.05).

---

## Cài đặt và chạy

### Yêu cầu

```bash
pip install rpy2 pandas numpy matplotlib scipy statsmodels ruptures
```

Trong R:
```r
install.packages("rugarch")
```

### Thứ tự chạy

1. Mở `Breakpoint_Justification.ipynb` → chạy để xác nhận breakpoints hợp lệ
2. Mở `model_asymmetric_group2.ipynb` → chạy 3 windows để có kết quả mô hình Asymmetric
3. Mở `model_quantile_group2.ipynb` → chạy 3 windows để có kết quả mô hình Quantile

> **Lưu ý**: Đảm bảo working directory là thư mục chứa notebook khi chạy, để các file CSV được tìm thấy đúng đường dẫn tương đối.

---

## Tài liệu tham khảo chính

- Andrews, D.W.K. (1993). Tests for Parameter Instability and Structural Change. *Econometrica*, 61(4), 821–856.
- Engle, R.F. (1982). Autoregressive Conditional Heteroscedasticity. *Econometrica*, 50(4), 987–1007.
- Hansen, B.E. (2001). The New Econometrics of Structural Change. *Journal of Economic Perspectives*, 15(4), 117–128.
- Hillebrand, E. (2005). Neglecting parameter changes in GARCH models. *Journal of Econometrics*, 129(1-2), 121–138.
- Killick, R., Fearnhead, P. & Eckley, I.A. (2012). Optimal Detection of Changepoints. *JASA*, 107(500), 1590–1598.
- Lamoureux, C.G. & Lastrapes, W.D. (1990). Persistence in Variance, Structural Change, and the GARCH Model. *JBES*, 8(2), 225–234.
- Nelson, D.B. (1991). Conditional Heteroskedasticity in Asset Returns: A New Approach. *Econometrica*, 59(2), 347–370.
