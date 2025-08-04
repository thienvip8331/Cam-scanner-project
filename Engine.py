import cv2
import pytesseract
import numpy as np
from PIL import Image
import re # Import thư viện Regular Expressions
import os

class ImageProcessor:
    def __init__(self):
        try:
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise RuntimeError("Tesseract is not installed or it's not in your PATH. See README file for more information.") from e

    def image_to_text(self, image, lang='vie'):
        if image is None: return ""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        # Sử dụng thêm config để cải thiện chất lượng OCR
        config = f'--oem 3 --psm 6 -l {lang}'
        text = pytesseract.image_to_string(pil_image, config=config)
        return text

    def process_image_and_extract_data(self, image_path):
        try:
            image = cv2.imread(image_path)
            if image is None: return None
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
        processed_image = cv2.adaptiveThreshold(
            blurred_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        processed_bgr_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2BGR)
        extracted_text = self.image_to_text(processed_bgr_image, lang='vie')
        
        if not extracted_text.strip():
            return {"image_path": image_path, "extracted_text": ""}
        
        return {"image_path": image_path, "extracted_text": extracted_text}

class DataProcessor:
    def create_json_structure(self, image_path):
        """
        Tạo một cấu trúc JSON rỗng.
        """
        image_name = os.path.basename(image_path)
        return {
            "image_name": image_name,
            "image_path": image_path,
            "image_base64": "",
            "product_name": "",
            "manufacturer": { "company_name": "", "address": "", "phone": "" },
            "importer": { "company_name": "", "address": "", "phone": "" },
            "manufacturing_date": "",
            "expiry_date": "",
            "type": ""
        }

    def parse_text_to_json(self, raw_text, json_data):
        """
        Hàm chính để phân tích văn bản thô và điền vào cấu trúc JSON.
        """
        # --- 1. Trích xuất Tên sản phẩm ---
        # Giả định tên sản phẩm là dòng chữ lớn ở đầu
        lines = [line for line in raw_text.split('\n') if line.strip()]
        if lines:
            # OCR thường đọc sai "Cốm" thành "C60m", "C60",...
            # Chúng ta sẽ thử tìm dòng nào giống "Bánh Custas..." nhất
            for line in lines:
                if "bánh" in line.lower() or "custas" in line.lower():
                    json_data["product_name"] = line.strip()
                    break
            if not json_data["product_name"]:
                 json_data["product_name"] = lines[0] # Lấy dòng đầu tiên nếu không tìm thấy

        # --- 2. Trích xuất Hạn sử dụng ---
        # Mẫu tìm kiếm: "HẠN SỬ DỤNG" theo sau là dấu hai chấm (có thể có hoặc không) và nội dung
        match = re.search(r'HẠN SỬ DỤNG\s*[: ]*(.*)', raw_text, re.IGNORECASE)
        if match:
            json_data["expiry_date"] = match.group(1).strip()

        # --- 3. Trích xuất Nhà sản xuất ---
        # Mẫu tìm kiếm: "SẢN XUẤT TẠI" và lấy nội dung trên cùng một dòng
        match = re.search(r'SẢN XUẤT TẠI\s*C[OÔ]NG TY\s*(.*)', raw_text, re.IGNORECASE)
        if match:
            # OCR có thể đọc sai "CÔNG TY", nên dùng C[OÔ]NG TY
            json_data["manufacturer"]["company_name"] = "CÔNG TY " + match.group(1).strip()

        # --- 4. Trích xuất Địa chỉ nhà sản xuất ---
        # Mẫu tìm kiếm: (M) hoặc LÔ E-13...
        match = re.search(r'\((M|m)\)\s*(.*)', raw_text, re.IGNORECASE)
        if match:
            json_data["manufacturer"]["address"] = match.group(2).strip()

        # --- 5. Trích xuất Xuất xứ ---
        # Gán "type" dựa trên xuất xứ
        match = re.search(r'XUẤT XỨ\s*[: ]*(.*)', raw_text, re.IGNORECASE)
        if match:
            json_data["type"] = match.group(1).strip()
        
        return json_data