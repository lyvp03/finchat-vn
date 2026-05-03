"""Static domain knowledge for gold market analysis.

This knowledge is injected into the LLM prompt so it can reason about
gold price movements using established financial theory, not just
pattern-match from news headlines.
"""

GOLD_MARKET_KNOWLEDGE = """
=== KIẾN THỨC NỀN TẢNG VỀ THỊ TRƯỜNG VÀNG ===
Sử dụng kiến thức dưới đây để suy luận khi phân tích. Đây là lý thuyết tài chính đã được thiết lập.

1. CƠ CHẾ ĐỊNH GIÁ VÀNG TRONG NƯỚC
- Giá vàng Việt Nam = Giá vàng thế giới (XAUUSD) × Tỷ giá USD/VND × 0.8299 (hệ số quy đổi oz → lượng) + Premium nội địa.
- Premium nội địa phản ánh: cung-cầu trong nước, chính sách NHNN (hạn ngạch nhập khẩu), thuế, brand premium (SJC được NHNN công nhận).
- Premium cao bất thường (>10-15%) → thường do thiếu hụt nguồn cung vàng miếng, hoặc NHNN chưa cấp quota nhập khẩu mới.
- Khi NHNN bán vàng can thiệp → premium thu hẹp nhanh.

2. CÁC YẾU TỐ TÁC ĐỘNG ĐẾN GIÁ VÀNG THẾ GIỚI (XAUUSD)
a) Lãi suất thực (Real Yield) — yếu tố quan trọng nhất:
   - Vàng không sinh lãi → khi lãi suất thực (= lãi suất danh nghĩa - lạm phát kỳ vọng) tăng → chi phí cơ hội giữ vàng tăng → vàng kém hấp dẫn.
   - Lãi suất thực giảm hoặc âm → giữ vàng không mất nhiều cơ hội → vàng hấp dẫn hơn.
   - Theo dõi: US 10Y TIPS yield, Fed funds rate, CPI expectations.

b) Chính sách Fed:
   - Fed hawkish (tăng lãi suất / giảm QE / phát biểu cứng rắn) → USD mạnh + lãi suất thực tăng → vàng chịu áp lực.
   - Fed dovish (giảm lãi suất / tăng QE / phát biểu ôn hòa) → USD yếu + lãi suất thực giảm → vàng được hỗ trợ.
   - Dot plot, FOMC minutes, phát biểu của Chair → tín hiệu quan trọng.

c) Đồng USD (DXY):
   - Vàng được định giá bằng USD → USD mạnh → vàng đắt hơn cho người mua ngoài Mỹ → cầu giảm → giá giảm.
   - USD yếu → vàng rẻ hơn tương đối → cầu tăng → giá tăng.
   - Lưu ý: DXY đo sức mạnh USD so với rổ tiền tệ lớn (EUR, JPY, GBP...), khác với USD/VND.

d) Lạm phát:
   - Vàng là tài sản chống lạm phát truyền thống (inflation hedge).
   - Lạm phát cao → demand giữ vàng tăng (hedge). NHƯNG nếu lạm phát cao khiến Fed phải tăng lãi suất mạnh → hiệu ứng ngược qua lãi suất thực.
   - Cần phân biệt: lạm phát tăng + Fed chưa phản ứng → tốt cho vàng. Lạm phát tăng + Fed hawkish → xấu cho vàng.

e) Rủi ro địa chính trị & khủng hoảng:
   - Chiến tranh, xung đột, khủng hoảng tài chính → tâm lý "flight to safety" → vàng được mua như tài sản trú ẩn.
   - Hiệu ứng thường mạnh trong ngắn hạn, có thể giảm dần khi thị trường "quen" với rủi ro.

f) Cầu vật lý:
   - Ngân hàng trung ương mua vàng (đặc biệt Trung Quốc, Ấn Độ, Nga) → hỗ trợ giá dài hạn.
   - Mùa cưới/lễ hội ở Ấn Độ, Tết Nguyên Đán → tăng cầu mùa vụ.
   - Cầu công nghiệp (điện tử, y tế) chiếm ~7% tổng cầu, ít ảnh hưởng giá.

3. MỐI QUAN HỆ GIỮA CÁC CHỈ SỐ KỸ THUẬT
- RSI (Relative Strength Index):
  + RSI > 70: vùng quá mua (overbought) → khả năng điều chỉnh giảm.
  + RSI < 30: vùng quá bán (oversold) → khả năng hồi phục.
  + RSI 40-60: vùng trung tính, chưa có tín hiệu rõ.
  + RSI phân kỳ (divergence): giá tạo đỉnh mới nhưng RSI không → cảnh báo đảo chiều.

- EMA (Exponential Moving Average):
  + Giá trên EMA20: xu hướng ngắn hạn tăng. Giá dưới EMA20: xu hướng ngắn hạn giảm.
  + EMA20 cắt lên EMA50: tín hiệu tăng (golden cross). EMA20 cắt xuống EMA50: tín hiệu giảm (death cross).
  + Khoảng cách giữa giá và EMA càng lớn → khả năng mean-reversion (quay về trung bình) càng cao.

- MACD:
  + MACD > Signal line: momentum tăng. MACD < Signal line: momentum giảm.
  + MACD histogram dương và tăng: lực tăng đang mạnh lên.
  + MACD histogram âm và giảm: lực giảm đang mạnh lên.

4. ĐẶC THÙ THỊ TRƯỜNG VÀNG VIỆT NAM
- Thị trường vàng VN không liên thông hoàn toàn với thế giới (không có sàn giao dịch vàng quốc tế).
- NHNN quản lý chặt: SJC là thương hiệu vàng quốc gia, được NHNN cấp phép sản xuất.
- Khi NHNN đấu thầu bán vàng → cung tăng → premium giảm. Khi NHNN ngừng bán → cung thiếu → premium tăng.
- Giá SJC thường cao hơn giá quy đổi thế giới 5-20 triệu đồng/lượng.
- Các loại vàng khác (DOJI, PNJ, nhẫn tròn) thường bám sát giá thế giới hơn SJC.
- Spread (chênh lệch mua-bán) cao → thanh khoản thấp hoặc thị trường biến động mạnh.

5. QUY TẮC SUY LUẬN
- Luôn xác định yếu tố CHỦ ĐẠO (dominant factor) trước, rồi mới nói các yếu tố phụ.
- Khi nhiều yếu tố trái chiều → nêu rõ "tín hiệu trái chiều" và giải thích channel nào đang chi phối.
- Không kết luận "vàng tăng vì lạm phát" nếu không có dữ liệu lạm phát trong context.
- Không bịa thông tin Fed, CPI, hoặc sự kiện kinh tế nếu không có trong context.
- Phân biệt: tác động NGẮN HẠN (1-7 ngày) vs TRUNG HẠN (1-3 tháng). Nếu chỉ có data ngắn hạn, không nhận định trung/dài hạn.
"""
