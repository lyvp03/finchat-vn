import json
import pandas as pd
from pathlib import Path
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def preprocess_json_data(file_path):
    print(f"[*] Đọc dữ liệu từ {file_path}")
    if not file_path.exists():
        print("[-] Không tìm thấy file JSON. Vui lòng chạy test_crawl_sjc.py trước.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("[-] File JSON rỗng.")
        return

    # Chuyển đổi JSON thành Pandas DataFrame
    df = pd.DataFrame(data)
    
    # 1. Tính toán giá trị trung bình (mid_price) và chênh lệch (spread)
    print("\n[*] Tiền xử lý: Tính Mid Price và Spread...")
    df['mid_price'] = (df['giá_mua'] + df['giá_bán']) / 2
    df['spread'] = df['giá_bán'] - df['giá_mua']

    # Đảm bảo dữ liệu được sắp xếp theo thời gian tăng dần để tính toán Indicator
    df['thời_gian_thu_thập'] = pd.to_datetime(df['thời_gian_thu_thập'])
    df = df.sort_values('thời_gian_thu_thập').reset_index(drop=True)

    # 2. Tính toán các chỉ số cơ bản (EMA, MACD mô phỏng)
    print("[*] Tiền xử lý: Tính các chỉ số kỹ thuật (Indicators)...")
    # Sử dụng Pandas EWM để tính toán đường trung bình động hàm mũ
    df['ema_3'] = df['mid_price'].ewm(span=3, adjust=False).mean()
    
    print("\n--- KẾT QUẢ SAU TIỀN XỬ LÝ (PREPROCESSED) ---")
    # In ra một số cột quan trọng để kiểm tra
    display_cols = ['thời_gian_thu_thập', 'giá_mua', 'giá_bán', 'mid_price', 'spread', 'ema_3']
    print(df[display_cols].to_string(index=False))
    
    # Lưu kết quả đã tiền xử lý ra file JSON khác
    out_file = file_path.parent / "sjc_preprocessed_test.json"
    
    # Format lại datetime thành chuỗi để lưu JSON
    df['thời_gian_thu_thập'] = df['thời_gian_thu_thập'].astype(str)
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    
    print(f"\n[+] Đã lưu dữ liệu tiền xử lý ra file: {out_file}")

if __name__ == "__main__":
    print("=== BƯỚC 2: TEST PREPROCESSING DATA SJC ===")
    json_path = Path(__file__).resolve().parents[2] / "data" / "sjc_sample_test.json"
    preprocess_json_data(json_path)
