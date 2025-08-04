# --- START OF FILE user_interface.py (REVISED WITH THREADING) ---

import Engine
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import base64
import threading # Dùng để chạy các tác vụ nặng trong luồng riêng
import queue # Dùng để giao tiếp an toàn giữa các luồng

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to Data Extractor")
        self.root.geometry("800x600")

        self.image_processor = Engine.ImageProcessor()
        self.data_processor = Engine.DataProcessor()

        self.current_image_path = None
        self.extracted_data_json = None
        self.result_queue = queue.Queue() # Tạo hàng đợi để nhận kết quả từ luồng công nhân

        self._create_widgets()

    def _create_widgets(self):
        # ... (phần code này không thay đổi)
        self.image_frame = tk.Frame(self.root, bd=2, relief="groove")
        self.image_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.image_label = tk.Label(self.image_frame, text="No Image Loaded")
        self.image_label.pack(expand=True)
        self.control_frame = tk.Frame(self.root, bd=2, relief="groove")
        self.control_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.load_button = tk.Button(self.control_frame, text="Load Image", command=self._load_image)
        self.load_button.pack(pady=5)
        self.process_button = tk.Button(self.control_frame, text="Process Image", command=self._start_processing)
        self.process_button.pack(pady=5)
        self.save_button = tk.Button(self.control_frame, text="Save Data (JSON)", command=self._save_data)
        self.save_button.pack(pady=5)
        self.data_label = tk.Label(self.control_frame, text="Extracted Data:")
        self.data_label.pack(pady=5)
        self.data_text = tk.Text(self.control_frame, wrap="word", height=20, width=50)
        self.data_text.pack(pady=5, fill="both", expand=True)

    def _load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if file_path:
            self.current_image_path = file_path
            self._display_image(file_path)
            self.data_text.delete(1.0, tk.END)
            self.data_text.insert(tk.END, "Image loaded. Click 'Process Image' to extract data.")
            self.extracted_data_json = None
            self.process_button.config(state="normal")
            self.save_button.config(state="disabled")

    def _display_image(self, file_path):
        try:
            img = Image.open(file_path)
            img.thumbnail((380, 580), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_image, text="")
            self.image_label.image = self.tk_image
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
            self.image_label.config(image="", text="Error loading image")

    def _start_processing(self):
        if not self.current_image_path:
            messagebox.showwarning("No Image", "Please load an image first.")
            return

        self.process_button.config(state="disabled")
        self.load_button.config(state="disabled")
        self.data_text.delete(1.0, tk.END)
        self.data_text.insert(tk.END, "Processing image... This may take a moment.")
        
        # Tạo và khởi chạy luồng công nhân
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            args=(self.current_image_path,)
        )
        self.processing_thread.start()
        self.root.after(100, self._check_queue)

    def _processing_worker(self, image_path):
        """
        Hàm này chạy trong luồng công nhân. Nó thực hiện tất cả các công việc nặng.
        """
        try:
            # 1. Trích xuất văn bản thô từ ảnh
            processed_data = self.image_processor.process_image_and_extract_data(image_path)
            
            if processed_data and processed_data.get("extracted_text"):
                raw_text = processed_data["extracted_text"]
                
                # 2. Tạo một cấu trúc JSON rỗng
                json_structure = self.data_processor.create_json_structure(image_path)
                
                # 3. GỌI BỘ PHÂN TÍCH MỚI để điền dữ liệu
                final_json = self.data_processor.parse_text_to_json(raw_text, json_structure)
                
                # 4. Mã hóa ảnh sang Base64
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    final_json["image_base64"] = encoded_string
                
                self.result_queue.put(final_json) # Đặt kết quả cuối cùng vào hàng đợi
            else:
                self.result_queue.put({"error": "No text extracted or processing failed."})
        except Exception as e:
            # Gửi lỗi về hàng đợi
            self.result_queue.put({"error": str(e)})
            
    def _check_queue(self):
        try:
            result = self.result_queue.get_nowait()
            self._update_ui_with_result(result)
        except queue.Empty:
            self.root.after(100, self._check_queue)

    def _update_ui_with_result(self, result):
        """
        Cập nhật giao diện với kết quả nhận được. Chạy trên luồng chính.
        """
        self.data_text.delete(1.0, tk.END)

        if "error" in result:
            messagebox.showerror("Processing Error", f"An error occurred: {result['error']}")
            self.data_text.insert(tk.END, f"Error: {result['error']}")
            self.extracted_data_json = None
        else:
            self.extracted_data_json = result
            
            display_data = self.extracted_data_json.copy()
            display_data["image_base64"] = "--- (Base64 data is too long to display) ---"
            
            self.data_text.insert(tk.END, json.dumps(display_data, indent=4, ensure_ascii=False))
            self.save_button.config(state="normal")
            messagebox.showinfo("Success", "Image processed successfully!")

        self.process_button.config(state="normal")
        self.load_button.config(state="normal")

    def _save_data(self):
        if not self.extracted_data_json:
            messagebox.showwarning("No Data", "No data has been extracted yet to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.extracted_data_json, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Save Successful", f"Data saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save data: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()