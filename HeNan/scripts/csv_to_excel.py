import pandas as pd
import os

def convert_csv_to_excel(csv_path, excel_path):
    print(f"Reading CSV from {csv_path}...")
    try:
        # Try reading with utf-8 encoding first
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Fallback to gbk if utf-8 fails
            print("UTF-8 decode failed, trying GBK...")
            df = pd.read_csv(csv_path, encoding='gbk')
            
        print(f"Writing Excel to {excel_path}...")
        df.to_excel(excel_path, index=False)
        print(f"Conversion successful! File saved to: {excel_path}")
    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    # Get the project root directory (assuming script is in scripts/ folder)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    csv_file = os.path.join(project_root, "tables", "scan_result_with_standard_name.csv")
    excel_file = os.path.join(project_root, "tables", "scan_result_with_standard_name.xlsx")
    
    if os.path.exists(csv_file):
        convert_csv_to_excel(csv_file, excel_file)
    else:
        print(f"File not found: {csv_file}")
