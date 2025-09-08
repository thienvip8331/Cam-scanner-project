import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class AutocompleteEntry(ttk.Entry):
    def __init__(self, *args, **kwargs):
        self.listbox = None
        self.autocomplete_list = kwargs.pop('autocomplete_list', [])
        super().__init__(*args, **kwargs)
        self.var = self["textvariable"]
        if self.var == '': self.var = self["textvariable"] = tk.StringVar()
        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Up>", self.move_up)
        self.bind("<Down>", self.move_down)
        self.bind("<FocusOut>", self.hide_listbox)
    def changed(self, name, index, mode):
        if self.var.get() == '':
            if self.listbox: self.listbox.destroy(); self.listbox = None
        else:
            words = self.comparison()
            if words:
                if not self.listbox:
                    self.listbox = tk.Listbox(self.winfo_toplevel(), background='#333333', foreground='white', selectbackground='#0078D7')
                    self.listbox.bind("<Double-Button-1>", self.selection)
                    self.listbox.bind("<Right>", self.selection)
                    x = self.winfo_rootx(); y = self.winfo_rooty() + self.winfo_height()
                    self.listbox.place(x=x, y=y, width=self.winfo_width())
                self.listbox.delete(0, tk.END)
                for w in words: self.listbox.insert(tk.END, w)
            else:
                if self.listbox: self.listbox.destroy(); self.listbox = None
    def selection(self, event=None):
        if self.listbox:
            self.var.set(self.listbox.get(tk.ACTIVE))
            self.listbox.destroy(); self.listbox = None
            self.icursor(tk.END); return "break"
    def move_up(self, event):
        if self.listbox:
            if self.listbox.curselection() == (0,): return
            index = self.listbox.curselection()[0]
            self.listbox.selection_clear(first=index)
            index = str(int(index) - 1)
            self.listbox.selection_set(first=index); self.listbox.activate(index)
        return "break"
    def move_down(self, event):
        if self.listbox:
            if self.listbox.curselection() == (self.listbox.size() - 1,): return
            index = self.listbox.curselection()[0]
            self.listbox.selection_clear(first=index)
            index = str(int(index) + 1)
            self.listbox.selection_set(first=index); self.listbox.activate(index)
        return "break"
    def comparison(self): return [w for w in self.autocomplete_list if self.var.get().lower() in w.lower()]
    def hide_listbox(self, event=None):
        if self.listbox: self.listbox.destroy(); self.listbox = None
    def update_autocomplete_list(self, new_list): self.autocomplete_list = new_list

class MainApplication(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("Ứng dụng Quản lý Sản phẩm | Đọc OCR & Lưu DB")
        self.geometry("1280x800")
        self.configure(bg="black")
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', background='black', foreground='white', font=('Arial', 10))
        self.style.configure('TFrame', background='black')
        self.style.configure('TLabel', background='black', foreground='white')
        self.style.configure('TButton', background='#333333', foreground='white', font=('Arial', 10, 'bold'), relief='raised')
        self.style.map('TButton', background=[('active', '#555555'), ('pressed', '#111111')], foreground=[('active', 'white')])
        self.style.configure('Treeview', background='#333333', foreground='white', fieldbackground='#333333', borderwidth=0)
        self.style.configure('Treeview.Heading', background='#555555', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Treeview', background=[('selected', '#0078D7')])
        self.style.configure('TEntry', fieldbackground='#555555', foreground='white', insertbackground='white', borderwidth=1, relief='solid')
        self.style.configure('TPanedwindow', background='black')
        self.style.configure('TNotebook', background='black', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#333333', foreground='white', borderwidth=0, padding=[5, 2])
        self.style.map('TNotebook.Tab', background=[('selected', 'grey')], foreground=[('selected', 'white')], expand=[('selected', [1,1,1,0])])
        self.style.configure('Grey.TFrame', background='grey')
        self.style.configure('Grey.TLabel', background='grey', foreground='white')

        self.file_menu_button = tk.Menubutton(self, text="File", font=("Arial", 10, 'bold'), bg="#333333", fg="white", relief=tk.RAISED, borderwidth=2, activebackground="#555555", activeforeground="white")
        self.file_menu_button.place(x=10, y=10)
        self.file_menu = tk.Menu(self.file_menu_button, tearoff=0, bg="#333333", fg="white", activebackground="#555555", activeforeground="white")
        self.file_menu_button["menu"] = self.file_menu
        self.file_menu.add_command(label="Mở file từ thư mục", command=self.controller.open_file_dialog)
        self.file_menu.add_command(label="Xuất dữ liệu dưới dạng file.json", command=self.controller.export_data_json)

        self.main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(40, 10))

        self.left_frame = ttk.Frame(self.main_paned_window, style='TFrame')
        self.main_paned_window.add(self.left_frame, weight=3)
        self.image_canvas = tk.Canvas(self.left_frame, bg="#222222", relief=tk.SUNKEN, borderwidth=2, highlightbackground="#555555", highlightthickness=1)
        self.image_canvas.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.image_placeholder_text_id = self.image_canvas.create_text(0, 0, text="Nhấn vào đây để chọn ảnh", font=("Arial", 14, "italic"), fill="white", justify=tk.CENTER)
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)
        self.image_canvas.bind("<Button-1>", self.controller.open_file_dialog)
        self.current_image_tk = None; self.current_image_path = None

        self.right_frame = ttk.Frame(self.main_paned_window, style='Grey.TFrame')
        self.main_paned_window.add(self.right_frame, weight=2)
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        self.extracted_data_tab = ttk.Frame(self.notebook, style='Grey.TFrame')
        self.notebook.add(self.extracted_data_tab, text="Thông tin trích xuất")

        ttk.Label(self.extracted_data_tab, text="Thông tin chi tiết sản phẩm:", font=("Arial", 12, 'bold'), style='Grey.TLabel').pack(padx=10, pady=(10, 5), anchor='w')
        self.data_fields = {}
        field_labels = [("Tên ảnh:", "image_name"), ("Đường dẫn ảnh:", "image_path"), ("Tên sản phẩm:", "product_name"),("NSX Cty:", "manufacturer_company_name"), ("NSX Địa chỉ:", "manufacturer_address"), ("NSX SĐT:", "manufacturer_phone"), ("Ngày SX:", "manufacturing_date"), ("Ngày HH:", "expiry_date"), ("Loại SP:", "product_type")]

        self.scrollable_frame_container = ttk.Frame(self.extracted_data_tab, style='Grey.TFrame')
        self.scrollable_frame_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.canvas_scroll = tk.Canvas(self.scrollable_frame_container, background='grey', highlightthickness=0)
        self.canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_y = ttk.Scrollbar(self.scrollable_frame_container, orient=tk.VERTICAL, command=self.canvas_scroll.yview)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar_y.set)
        self.data_entry_frame = ttk.Frame(self.canvas_scroll, style='Grey.TFrame')
        self.canvas_scroll.create_window((0, 0), window=self.data_entry_frame, anchor="nw")
        self.data_entry_frame.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        
        for i, (label_text, field_key) in enumerate(field_labels):
            ttk.Label(self.data_entry_frame, text=label_text, style='Grey.TLabel').grid(row=i, column=0, sticky='w', padx=5, pady=2)
            entry = AutocompleteEntry(self.data_entry_frame, width=40, style='TEntry') if field_key == "product_name" else ttk.Entry(self.data_entry_frame, width=40, style='TEntry')
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=2)
            self.data_fields[field_key] = entry

        ingredients_row = len(field_labels)
        ttk.Label(self.data_entry_frame, text="Thành phần:", style='Grey.TLabel').grid(row=ingredients_row, column=0, sticky='nw', padx=5, pady=2)
        self.ingredients_text = tk.Text(self.data_entry_frame, height=8, width=40, background='#555555', foreground='white', insertbackground='white', relief='solid', borderwidth=1, wrap=tk.WORD)
        self.ingredients_text.grid(row=ingredients_row, column=1, sticky='nsew', padx=5, pady=2)
        self.data_fields["ingredients"] = self.ingredients_text
        
        self.data_entry_frame.grid_columnconfigure(1, weight=1)
        self.data_entry_frame.grid_rowconfigure(ingredients_row, weight=1)

        self.save_button = ttk.Button(self.extracted_data_tab, text="Lưu vào cơ sở dữ liệu", command=self.controller.save_extracted_data)
        self.save_button.pack(pady=10)

        self.saved_products_tab = SavedProductsTab(self.notebook, self.controller)
        self.notebook.add(self.saved_products_tab, text="Sản phẩm đã lưu")

    def on_canvas_resize(self, event=None):
        if event:
            # Được gọi bởi sự kiện <Configure> của Tkinter
            width = event.width
            height = event.height
        else:
            # Được gọi thủ công, tự lấy kích thước hiện tại
            width = self.image_canvas.winfo_width()
            height = self.image_canvas.winfo_height()

        # Căn giữa lại placeholder text nếu nó tồn tại
        if hasattr(self, 'image_placeholder_text_id') and self.image_canvas.find_withtag(self.image_placeholder_text_id):
             self.image_canvas.coords(self.image_placeholder_text_id, width / 2, height / 2)

        # Vẽ lại ảnh nếu có, và nếu đây là một sự kiện thay đổi kích thước thực sự (để tránh vòng lặp vô hạn)
        if event and self.current_image_tk:
            self.display_image_on_canvas(self.current_image_path)
    
    def display_image_on_canvas(self, image_path):
        self.current_image_path = image_path
        self.image_canvas.delete("all")
        if not image_path:
            self.image_placeholder_text_id = self.image_canvas.create_text(0, 0, text="Nhấn vào đây để chọn ảnh", font=("Arial", 14, "italic"), fill="white", justify=tk.CENTER)
            self.on_canvas_resize() # [SỬA LỖI] Gọi hàm mà không cần tạo event giả
            self.current_image_tk = None
            return
        try:
            pil_image = Image.open(image_path)
        except Exception as e:
            messagebox.showerror("Lỗi ảnh", f"Không thể mở ảnh: {e}")
            self.current_image_tk = None
            return
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            self.after(50, lambda: self.display_image_on_canvas(image_path))
            return
        img_width, img_height = pil_image.size
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        resized_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        self.current_image_tk = ImageTk.PhotoImage(resized_image)
        x_center = (canvas_width - new_width) // 2
        y_center = (canvas_height - new_height) // 2
        self.image_canvas.create_image(x_center, y_center, anchor=tk.NW, image=self.current_image_tk)
    
    def update_autocomplete(self, product_names):
        if "product_name" in self.data_fields: self.data_fields["product_name"].update_autocomplete_list(product_names)
    
    def update_extracted_data_fields(self, data_dict):
        for field_key, widget in self.data_fields.items():
            value = ""
            if field_key.startswith("manufacturer_"): value = data_dict.get("manufacturer", {}).get(field_key.replace("manufacturer_", ""), "")
            elif field_key.startswith("importer_"): value = data_dict.get("importer", {}).get(field_key.replace("importer_", ""), "")
            else: value = data_dict.get(field_key, "")
            
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END); widget.insert("1.0", str(value))
            else:
                widget.delete(0, tk.END); widget.insert(0, str(value))
    
    def get_data_from_fields(self):
        return {
            "image_name": self.data_fields["image_name"].get(), "image_path": self.data_fields["image_path"].get(),
            "image_base64": "",
            "product_name": self.data_fields["product_name"].get(),
            "manufacturer": {"company_name": self.data_fields["manufacturer_company_name"].get(), "address": self.data_fields["manufacturer_address"].get(), "phone": self.data_fields["manufacturer_phone"].get()},
            "manufacturing_date": self.data_fields["manufacturing_date"].get(),
            "expiry_date": self.data_fields["expiry_date"].get(),
            "product_type": self.data_fields["product_type"].get(),
            "ingredients": self.data_fields["ingredients"].get("1.0", tk.END).strip()
        }

class SavedProductsTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='Grey.TFrame')
        self.controller = controller

        search_frame = ttk.Frame(self, style='Grey.TFrame')
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(search_frame, text="Tìm kiếm:", style='Grey.TLabel').pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, style='TEntry')
        self.search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.search_button = ttk.Button(search_frame, text="Tìm", command=self.controller.search_products)
        self.search_button.pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(self, style='Grey.TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.product_tree = ttk.Treeview(tree_frame, columns=("ID", "Tên SP", "Ngày SX", "Ngày HH"), show="headings", selectmode="browse")
        self.product_tree.heading("ID", text="ID"); self.product_tree.heading("Tên SP", text="Tên sản phẩm")
        self.product_tree.heading("Ngày SX", text="Ngày sản xuất"); self.product_tree.heading("Ngày HH", text="Ngày hết hạn")
        self.product_tree.column("ID", width=50, stretch=tk.NO); self.product_tree.column("Tên SP", width=200, stretch=tk.YES)
        self.product_tree.column("Ngày SX", width=100, stretch=tk.NO); self.product_tree.column("Ngày HH", width=100, stretch=tk.NO)
        self.product_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.product_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.product_tree.configure(yscrollcommand=tree_scrollbar.set)

        button_frame = ttk.Frame(self, style='Grey.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        self.refresh_button = ttk.Button(button_frame, text="Làm mới", command=self.controller.load_all_products)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        self.delete_button = ttk.Button(button_frame, text="Xóa", command=self.controller.delete_selected_product)
        self.delete_button.pack(side=tk.RIGHT, padx=5)
        self.view_details_button = ttk.Button(button_frame, text="Xem chi tiết", command=self.controller.view_selected_product_details)
        self.view_details_button.pack(side=tk.RIGHT, padx=5)
    
    def populate_products(self, products_data):
        for item in self.product_tree.get_children(): self.product_tree.delete(item)
        for prod in products_data: self.product_tree.insert("", "end", iid=prod['id'], values=(prod['id'], prod['product_name'], prod['manufacturing_date'], prod['expiry_date']))
