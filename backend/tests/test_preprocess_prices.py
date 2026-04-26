import json
import sys
import io
import pandas as pd
from pathlib import Path

# Add backend directory to path so we can import preprocessing
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from preprocessing.compute_indicators import prepare_updates

# Fix encoding cho Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("=== TEST PREPROCESSING 6 LOẠI VÀNG ===")
    
    input_file = Path(__file__).resolve().parents[2] / "data" / "raw_prices_test.json"
    
    if not input_file.exists():
        print(f"[-] Không tìm thấy file {input_file}. Vui lòng chạy test_crawl_prices.py trước.")
        return
        
    print(f"[*] Đang đọc dữ liệu từ {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    df = pd.DataFrame(data)
    # Convert 'ts' string back to datetime for processing
    df['ts'] = pd.to_datetime(df['ts'])
    
    print(f"[*] Dữ liệu gốc: {len(df)} dòng.")
    print("[*] Đang chạy hàm tiền xử lý prepare_updates() (tính EMA, MACD, RSI)...")
    
    try:
        # Hàm prepare_updates trả về dataframe đã có thêm các cột chỉ số
        processed_df = prepare_updates(df)
        
        print("\n--- KẾT QUẢ MẪU SAU KHI TÍNH TOÁN ---")
        # In ra vài dòng của XAUUSD hoặc SJC để xem
        sample = processed_df.tail(3)
        display_cols = ['ts', 'type_code', 'mid_price', 'ema20', 'rsi14', 'macd']
        print(sample[display_cols].to_string(index=False))
        
        # Format lại datetime để lưu JSON
        processed_df['ts'] = processed_df['ts'].astype(str)
        
        out_file = input_file.parent / "processed_prices_test.json"
        with open(out_file, "w", encoding="utf-8") as f:
            # Thay thế NaN bằng None (null trong JSON)
            processed_data = processed_df.where(pd.notnull(processed_df), None).to_dict(orient="records")
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n[+] Đã lưu dữ liệu ({len(processed_df)} dòng) có chứa Indicators ra file: {out_file}")
        
    except Exception as e:
        print(f"[-] Lỗi trong quá trình tính toán: {e}")

if __name__ == "__main__":
    main()
