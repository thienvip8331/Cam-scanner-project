import database_connector
import engine 
import user_interface
import data 
import re
from ocr_corrections import OCR_CORRECTIONS 
import cv2
import pytesseract
from PIL import Image
import os
import base64
import json
import re
from tkinter import filedialog, messagebox
import mysql.connector.errors
from datetime import datetime

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 

class ApplicationController:
    def __init__(self):
        self.db = database_connector.Database()
        self.product_manager = data.ProductManager(self.db)
        self.product_manager.ensure_table_exists()
        self.app_view = user_interface.MainApplication(self)
        self.current_raw_ocr_text = ""
        temp_dir = r"D:/VS code insider/project/temp"
        os.makedirs(temp_dir, exist_ok=True)
        self.load_all_products()

    def run(self):
        self.app_view.mainloop()

    def open_file_dialog(self, event=None):
        file_path = filedialog.askopenfilename(filetypes=[("Tệp ảnh", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if file_path:
            self.process_image_file(file_path)

    def process_image_file(self, file_path):
        # [CẢI TIẾN] Thay đổi con trỏ để báo hiệu ứng dụng đang bận
        self.app_view.config(cursor="watch")
        self.app_view.update_idletasks() # Cập nhật giao diện ngay lập tức

        try:
            # Xóa dữ liệu cũ và chuẩn bị giao diện
            self.app_view.update_extracted_data_fields(self._empty_data_dict())
            self.app_view.display_image_on_canvas(None)
            
            # 1. Đọc ảnh bằng OpenCV
            img_cv = cv2.imread(file_path)
            if img_cv is None:
                raise ValueError(f"Không thể đọc tệp ảnh: {file_path}.")
            
            # Hiển thị ảnh gốc lên giao diện
            self.app_view.display_image_on_canvas(file_path)
            self.app_view.update()

            # 2. [TỐI ƯU] Gọi hàm xử lý ảnh chuyên sâu từ engine.py
            # Hàm này sẽ thực hiện các bước: chỉnh nghiêng, khử nhiễu, và ngưỡng hóa
            print("Bắt đầu xử lý ảnh chuyên sâu...")
            processed_img_np = engine.process_image_for_ocr(img_cv)
            print("Hoàn thành xử lý ảnh.")
            
            # 3. Thực hiện OCR trên ảnh đã được xử lý
            pil_processed_img = Image.fromarray(processed_img_np)
            print("Bắt đầu trích xuất văn bản OCR...")
            # Sử dụng cả tiếng Việt và tiếng Anh để tăng độ chính xác
            text = pytesseract.image_to_string(pil_processed_img, lang='vie+eng')
            self.current_raw_ocr_text = text
            print("--- OCR Text Trích Xuất ---\n", text, "\n--------------------------")

            # 4. Phân tích văn bản OCR để trích xuất thông tin có cấu trúc
            extracted_data = self._parse_ocr_text(text)
            extracted_data["image_name"] = os.path.basename(file_path)
            extracted_data["image_path"] = file_path
            
            # 5. Cập nhật các trường thông tin trên giao diện
            self.app_view.update_extracted_data_fields(extracted_data)
            self.app_view.notebook.select(self.app_view.extracted_data_tab)

        except Exception as e:
            messagebox.showerror("Lỗi Xử Lý Ảnh/OCR", f"Đã có lỗi xảy ra: {e}")
            self.app_view.update_extracted_data_fields(self._empty_data_dict())
        
        finally:
            # [CẢI TIẾN] Đảm bảo con trỏ luôn được trả về trạng thái bình thường
            self.app_view.config(cursor="")

    def save_extracted_data(self):
        data_dict = self.app_view.get_data_from_fields()
        if not data_dict.get("product_name"):
            messagebox.showwarning("Thiếu thông tin", "Tên sản phẩm không được để trống.")
            return
        if not data_dict.get("image_path"):
            messagebox.showwarning("Thiếu thông tin", "Chưa có ảnh nào được tải để lưu.")
            return
        
        if os.path.exists(data_dict["image_path"]):
            try:
                with open(data_dict["image_path"], "rb") as image_file:
                    data_dict["image_base64"] = base64.b64encode(image_file.read()).decode('utf-8')
            except Exception as e:
                messagebox.showwarning("Lỗi ảnh", f"Không thể mã hóa ảnh base64: {e}.")
        else:
            data_dict["image_base64"] = ""

        data_obj = data.Data(
            image_name=data_dict["image_name"], image_path=data_dict["image_path"], image_base64=data_dict["image_base64"],
            product_name=data_dict["product_name"],
            manufacturer_company_name=data_dict["manufacturer"]["company_name"], manufacturer_address=data_dict["manufacturer"]["address"], manufacturer_phone=data_dict["manufacturer"]["phone"],
            importer_company_name=data_dict["importer"]["company_name"], importer_address=data_dict["importer"]["address"], importer_phone=data_dict["importer"]["phone"],
            manufacturing_date=self._format_date_for_db(data_dict["manufacturing_date"]), 
            expiry_date=self._format_date_for_db(data_dict["expiry_date"]), 
            product_type=data_dict["product_type"],
            ingredients=data_dict["ingredients"]
        )
        try:
            data_obj.save(self.db)
            messagebox.showinfo("Thành công", "Dữ liệu đã được lưu vào cơ sở dữ liệu.")
            self.load_all_products()
            self.app_view.update_extracted_data_fields(self._empty_data_dict())
            self.app_view.display_image_on_canvas(None)
        except Exception as e:
            messagebox.showerror("Lỗi lưu dữ liệu", f"Không thể lưu dữ liệu.\nChi tiết: {e}")

    def load_all_products(self):
        try:
            products_data = self.product_manager.get_all_products_summary()
            self.app_view.saved_products_tab.populate_products(products_data)
            product_names = self.product_manager.get_all_product_names()
            self.app_view.update_autocomplete(product_names)
        except mysql.connector.errors.ProgrammingError as e:
            if e.errno == 1146:
                messagebox.showerror("Lỗi cơ sở dữ liệu", "Bảng 'products' không tồn tại. Ứng dụng sẽ tự tạo khi bạn lưu sản phẩm đầu tiên.")
            else:
                raise

    def search_products(self):
        search_term = self.app_view.saved_products_tab.search_entry.get().strip()
        products_data = self.product_manager.search_products_summary(search_term) if search_term else self.product_manager.get_all_products_summary()
        self.app_view.saved_products_tab.populate_products(products_data)

    def view_selected_product_details(self):
        selected_items = self.app_view.saved_products_tab.product_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chọn sản phẩm", "Vui lòng chọn một sản phẩm để xem chi tiết.")
            return
        
        product_id = self.app_view.saved_products_tab.product_tree.item(selected_items[0])['values'][0]
        product_dict = self.product_manager.get_product_details_by_id(product_id)
        
        if product_dict:
            if isinstance(product_dict.get("image_base64"), bytes):
                product_dict["image_base64"] = product_dict["image_base64"].decode('utf-8')
            
            display_data = {
                "image_name": product_dict.get("image_name", ""), "image_path": product_dict.get("image_path", ""),
                "image_base64": product_dict.get("image_base64", ""), "product_name": product_dict.get("product_name", ""),
                "manufacturer": {"company_name": product_dict.get("manufacturer_company_name", ""), "address": product_dict.get("manufacturer_address", ""), "phone": product_dict.get("manufacturer_phone", "")},
                "importer": {"company_name": product_dict.get("importer_company_name", ""), "address": product_dict.get("importer_address", ""), "phone": product_dict.get("importer_phone", "")},
                "manufacturing_date": str(product_dict.get("manufacturing_date", "") or ""), "expiry_date": str(product_dict.get("expiry_date", "") or ""),
                "product_type": product_dict.get("product_type", ""), "ingredients": product_dict.get("ingredients", "")
            }
            self.app_view.update_extracted_data_fields(display_data)
            self.app_view.display_image_on_canvas(display_data["image_path"]) 
            self.app_view.notebook.select(self.app_view.extracted_data_tab)
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy chi tiết sản phẩm.")

    def delete_selected_product(self):
        selected_items = self.app_view.saved_products_tab.product_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chọn sản phẩm", "Vui lòng chọn một sản phẩm để xóa.")
            return
        
        product_id = self.app_view.saved_products_tab.product_tree.item(selected_items[0])['values'][0]
        if messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc chắn muốn xóa sản phẩm ID: {product_id}?"):
            try:
                self.product_manager.delete_product_by_id(product_id)
                messagebox.showinfo("Thành công", "Sản phẩm đã được xóa.")
                self.load_all_products()
            except Exception as e:
                messagebox.showerror("Lỗi xóa", f"Không thể xóa sản phẩm: {e}")

    def export_data_json(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Tệp JSON", "*.json")])
        if file_path:
            try:
                products_list = self.product_manager.get_all_products_for_export()
                for p_dict in products_list:
                    for key, value in p_dict.items():
                        if isinstance(value, bytes):
                            p_dict[key] = value.decode('utf-8')
                        elif hasattr(value, 'isoformat'):
                            p_dict[key] = value.isoformat()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(products_list, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("Thành công", f"Dữ liệu đã được xuất ra file: {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi xuất JSON", f"Không thể xuất dữ liệu: {e}")

    def _format_date_for_db(self, date_str):
        if not date_str or any(keyword in date_str.lower() for keyword in ['xem trên', 'see on', 'on package']):
            return None
        date_str = date_str.strip().replace('.', '/').replace('-', '/')
        formats_to_try = ['%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d']
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def autocorrect_text(self, text: str) -> str:
        for wrong, correct in OCR_CORRECTIONS.items():
            text = re.sub(rf"\b{wrong}\b", correct, text, flags=re.IGNORECASE)
        return text

    def _parse_ocr_text(self, text):
        data = self._empty_data_dict()

        # [1] Chuẩn hóa văn bản: bỏ dòng rỗng + ký tự nhiễu
        lines = [re.sub(r'[\'"]', '', line).strip() for line in text.split('\n') if line.strip()]

        # [2] Chuyển sang chữ thường
        lines = [line.lower() for line in lines]
        normalized_text = '\n'.join(lines)

        # [3] Autocorrect
        normalized_text = self.autocorrect_text(normalized_text)
        lines = [self.autocorrect_text(line) for line in lines]

        # [4] Hàm clean_value
        def clean_value(value):
            value = re.sub(r'[:*]', '', value).strip()
            value = re.sub(r'\s+', ' ', value)
            return value

        # [5] Ingredients
        ingredients_match = re.search(
            r'(?is)(thành phần|ingredients)\s*[:\-\s]*\n?(.*?)(?=\n\s*(hdsd|hướng dẫn sử dụng|hdbq|bảo quản|lưu ý|chú ý|nsx|hsd|sản phẩm của|sản xuất tại|chăm sóc khách hàng|website:|$))',
            normalized_text
        )
        if ingredients_match:
            ingredients_text = ingredients_match.group(2).replace('\n', ' ')
            parts = re.split(r'[;,]', ingredients_text)
            parts = [p.strip() for p in parts if len(p.strip()) > 2]
            data['ingredients'] = ', '.join(parts)

        # [6] Thông tin công ty
        company_keywords = r'sản phẩm của|sản xuất tại|product of|sản xuất bởi|nhập khẩu và phân phối bởi|imported and distributed by|chịu trách nhiệm bởi'
        company_block_match = re.search(
            rf'(?is)({company_keywords})\s*[:\-\s]*\n?(.*?)(?=\n\s*(hdsd|thành phần|ingredients|nsx|hsd|website:|tel|hotline|$))',
            normalized_text
        )

        def parse_company_block(block_text):
            company_info = {"company_name": "", "address": "", "phone": ""}
            block_lines = [line.strip() for line in block_text.split('\n') if line.strip()]

            if not block_lines:
                return company_info

            company_info["company_name"] = block_lines[0]
            address_parts = []
            for line in block_lines[1:]:
                if re.search(r'(?i)tel|hotline|phone|website|email', line):
                    break
                address_parts.append(line)
            company_info["address"] = ', '.join(address_parts)

            phone_match = re.search(r'(?i)(?:tel|hotline|phone|cskh|chăm sóc khách hàng)\s*[:\-\s]*([\d\s\.\(\)]+)', text)
            if phone_match:
                company_info["phone"] = clean_value(phone_match.group(1))

            return company_info

        if company_block_match:
            manufacturer_block = company_block_match.group(2)
            data['manufacturer'] = parse_company_block(manufacturer_block)

        # [7] Ngày sản xuất & hạn sử dụng
        date_patterns = {
            'manufacturing_date': r'(?i)(nsx|ngày sản xuất|prd|production date)\s*[:\.\-\s]*([^\n]+)',
            'expiry_date': r'(?i)(hsd|hạn sử dụng|exp|expiry date)\s*[:\.\-\s]*([^\n]+)'
        }
        for key, pattern in date_patterns.items():
            match = re.search(pattern, normalized_text)
            if match:
                date_value = clean_value(match.group(2))
                if re.search(r'(?i)xem trên|see on', date_value):
                    date_value = "xem trên bao bì"
                data[key] = date_value

        # [8] Tên sản phẩm
        potential_name_lines = []
        stop_keywords = ['thành phần', 'dinh dưỡng', 'năng lượng', 'sản phẩm của', 'công ty', 'ingredients']
        for line in lines[:3]:
            if len(line) > 4 and not any(keyword in line for keyword in stop_keywords):
                potential_name_lines.append(line)
        if potential_name_lines:
            data['product_name'] = max(potential_name_lines, key=len)

        # [9] Loại sản phẩm
        if 'sữa' in data['ingredients'].lower() or 'milk' in data['ingredients'].lower():
            data['product_type'] = "sữa và các sản phẩm từ sữa"
        else:
            data['product_type'] = "thực phẩm"

        return data

    def _empty_data_dict(self):
        return {
            "image_name": "", "image_path": "", "image_base64": "", 
            "product_name": "", 
            "manufacturer": {"company_name": "", "address": "", "phone": ""}, 
            "importer": {"company_name": "", "address": "", "phone": ""}, 
            "manufacturing_date": "", "expiry_date": "", 
            "product_type": "", "ingredients": ""
        }


if __name__ == "__main__":
    app = ApplicationController()
    app.run()
