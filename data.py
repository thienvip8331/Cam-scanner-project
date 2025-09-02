import mysql.connector

# Lớp Data đại diện cho một đối tượng sản phẩm duy nhất
class Data:
    def __init__(self, image_name="", image_path="", image_base64="", product_name="", manufacturer_company_name="", manufacturer_address="", manufacturer_phone="", importer_company_name="", importer_address="", importer_phone="", manufacturing_date=None, expiry_date=None, product_type="", ingredients=""):
        self.image_name = image_name
        self.image_path = image_path
        self.image_base64 = image_base64
        self.product_name = product_name
        self.manufacturer = {"company_name": manufacturer_company_name, "address": manufacturer_address, "phone": manufacturer_phone}
        self.importer = {"company_name": importer_company_name, "address": importer_address, "phone": importer_phone}
        self.manufacturing_date = manufacturing_date
        self.expiry_date = expiry_date
        self.product_type = product_type
        self.ingredients = ingredients

    def to_dict(self):
        """Chuyển đổi đối tượng Data thành một dictionary."""
        return {
            "image_name": self.image_name, "image_path": self.image_path, "image_base64": self.image_base64,
            "product_name": self.product_name,
            "manufacturer": self.manufacturer,
            "importer": self.importer,
            "manufacturing_date": self.manufacturing_date, "expiry_date": self.expiry_date,
            "product_type": self.product_type, "ingredients": self.ingredients
        }
    
    def save(self, db):
        """Lưu hoặc cập nhật một bản ghi sản phẩm duy nhất vào cơ sở dữ liệu."""
        
        # [TỐI ƯU] Dữ liệu ngày tháng đã được xử lý thành YYYY-MM-DD hoặc None từ controller
        mfg_date = self.manufacturing_date
        exp_date = self.expiry_date

        check_query = "SELECT id FROM products WHERE product_name = %s"
        existing_product = db.fetch_one(check_query, (self.product_name,))

        if existing_product:
            query = """
            UPDATE products SET
                image_name = %s, image_path = %s, image_base64 = %s,
                manufacturer_company_name = %s, manufacturer_address = %s, manufacturer_phone = %s,
                importer_company_name = %s, importer_address = %s, importer_phone = %s,
                manufacturing_date = %s, expiry_date = %s, product_type = %s, ingredients = %s
            WHERE id = %s;
            """
            params = (
                self.image_name, self.image_path, self.image_base64,
                self.manufacturer["company_name"], self.manufacturer["address"], self.manufacturer["phone"],
                self.importer["company_name"], self.importer["address"], self.importer["phone"],
                mfg_date, exp_date, self.product_type, self.ingredients,
                existing_product[0]
            )
        else:
            query = """
            INSERT INTO products (
                image_name, image_path, image_base64, product_name,
                manufacturer_company_name, manufacturer_address, manufacturer_phone,
                importer_company_name, importer_address, importer_phone,
                manufacturing_date, expiry_date, product_type, ingredients
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            params = (
                self.image_name, self.image_path, self.image_base64, self.product_name,
                self.manufacturer["company_name"], self.manufacturer["address"], self.manufacturer["phone"],
                self.importer["company_name"], self.importer["address"], self.importer["phone"],
                mfg_date, exp_date, self.product_type, self.ingredients
            )
            
        db.execute_query(query, params)


# Lớp ProductManager quản lý tất cả các tương tác với bảng 'products'
class ProductManager:
    def __init__(self, db):
        self.db = db

    def ensure_table_exists(self):
        """
        [TỐI ƯU] Tạo/Cập nhật bảng 'products'. 
        - Thay đổi kiểu dữ liệu của manufacturing_date và expiry_date thành DATE.
        - Thêm cột ingredients nếu chưa có.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            image_name VARCHAR(255),
            image_path TEXT,
            image_base64 LONGTEXT,
            product_name VARCHAR(255) UNIQUE NOT NULL,
            manufacturer_company_name VARCHAR(255),
            manufacturer_address TEXT,
            manufacturer_phone VARCHAR(50),
            importer_company_name VARCHAR(255),
            importer_address TEXT,
            importer_phone VARCHAR(50),
            manufacturing_date DATE NULL,
            expiry_date DATE NULL,
            product_type VARCHAR(100),
            ingredients TEXT
        );
        """
        self.db.execute_query(create_table_query)
        
        # Cố gắng thêm cột ingredients, bỏ qua lỗi nếu đã tồn tại
        try:
            self.db.execute_query("ALTER TABLE products ADD COLUMN ingredients TEXT")
        except mysql.connector.Error as err:
            if err.errno != 1060: # 1060 là lỗi "Duplicate column name"
                print(f"Lưu ý khi thêm cột 'ingredients': {err}")

    def get_all_product_names(self):
        """Lấy danh sách tất cả tên sản phẩm để gợi ý autocomplete."""
        query = "SELECT product_name FROM products"
        results = self.db.fetch_all(query)
        return [row[0] for row in results] if results else []

    def get_all_products_summary(self):
        query = "SELECT id, product_name, manufacturing_date, expiry_date FROM products"
        products_raw = self.db.fetch_all(query)
        return [{"id": p_id, "product_name": p_name, "manufacturing_date": str(mfg_date or ""), "expiry_date": str(exp_date or "")} for p_id, p_name, mfg_date, exp_date in products_raw]
        
    def get_all_products_for_export(self):
        query = "SELECT * FROM products"
        all_products = self.db.fetch_all(query)
        if not all_products: return []
        column_names = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(column_names, row)) for row in all_products]

    def search_products_summary(self, search_term):
        query = "SELECT id, product_name, manufacturing_date, expiry_date FROM products WHERE product_name LIKE %s"
        params = (f"%{search_term}%",)
        products_raw = self.db.fetch_all(query, params)
        return [{"id": p_id, "product_name": p_name, "manufacturing_date": str(mfg_date or ""), "expiry_date": str(exp_date or "")} for p_id, p_name, mfg_date, exp_date in products_raw]

    def get_product_details_by_id(self, product_id):
        query = "SELECT * FROM products WHERE id = %s"
        product_details_tuple = self.db.fetch_one(query, (product_id,))
        if product_details_tuple:
            column_names = [desc[0] for desc in self.db.cursor.description]
            return dict(zip(column_names, product_details_tuple))
        return None

    def delete_product_by_id(self, product_id):
        query = "DELETE FROM products WHERE id = %s"
        self.db.execute_query(query, (product_id,))
