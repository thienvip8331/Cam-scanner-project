-- Tạo cơ sở dữ liệu nếu chưa tồn tại.
CREATE DATABASE IF NOT EXISTS base;

-- Sử dụng cơ sở dữ liệu 'base'.
USE base;

-- Lệnh này sẽ xóa toàn bộ bảng và dữ liệu. 
-- Hãy cẩn thận khi sử dụng sau khi đã có dữ liệu quan trọng.
DROP TABLE IF EXISTS products;

-- Tạo bảng products nếu nó chưa tồn tại, với các kiểu dữ liệu đã được tối ưu.
CREATE TABLE IF NOT EXISTS products (
    -- Khóa chính tự tăng, định danh duy nhất cho mỗi sản phẩm.
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Thông tin về ảnh
    image_name VARCHAR(255),
    image_path TEXT,
    image_base64 LONGTEXT,
    
    -- Thông tin cơ bản của sản phẩm
    -- UNIQUE NOT NULL để đảm bảo tính toàn vẹn và là cơ sở cho việc cập nhật.
    product_name VARCHAR(255) UNIQUE NOT NULL,
    ingredients TEXT,
    product_type VARCHAR(100),

    -- Ngày sản xuất và hết hạn, sử dụng kiểu DATE để truy vấn và sắp xếp chính xác.
    -- NULL cho phép bỏ trống nếu không trích xuất được thông tin ngày tháng.
    manufacturing_date DATE NULL,
    expiry_date DATE NULL,
    
    -- Thông tin nhà sản xuất
    manufacturer_company_name VARCHAR(255),
    manufacturer_address TEXT,
    manufacturer_phone VARCHAR(50),
    
    -- Thông tin nhà nhập khẩu
    importer_company_name VARCHAR(255),
    importer_address TEXT,
    importer_phone VARCHAR(50)
);