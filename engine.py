import cv2
from PIL import Image
import pytesseract
import numpy as np
import matplotlib.pyplot as plt

im_file = r"D:\VS code insider\project\All-Image\Milk\IMG_8518.jpg"
img = cv2.imread(im_file)

def getSkewAngle(cvImage) -> float:
    # Prep image, copy, convert to gray scale, blur, and threshold
    newImage = cvImage.copy()
    gray = cv2.cvtColor(newImage, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Apply dilate to merge text into meaningful lines/paragraphs.
    # Use larger kernel on X axis to merge characters into single line, cancelling out any spaces.
    # But use smaller kernel on Y axis to separate between different blocks of text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilate = cv2.dilate(thresh, kernel, iterations=2)

    # Find all contours
    contours, hierarchy = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key = cv2.contourArea, reverse = True)
    for c in contours:
        rect = cv2.boundingRect(c)
        x,y,w,h = rect
        cv2.rectangle(newImage,(x,y),(x+w,y+h),(0,255,0),2)

    # Find largest contour and surround in min area box
    largestContour = None
    for c in contours[:10]: # Chỉ xét 10 contour lớn nhất
        rect = cv2.boundingRect(c)
        x, y, w, h = rect
        aspect_ratio = w / float(h)
        
        # Một khối văn bản thường có chiều rộng lớn hơn nhiều so với chiều cao
        if aspect_ratio > 2: # Tỉ lệ rộng/cao phải lớn (ví dụ > 2)
            largestContour = c
            break # Tìm thấy rồi thì dừng lại

    # Nếu không tìm thấy contour phù hợp, báo lỗi hoặc dùng cái lớn nhất
    if largestContour is None:
        print("Không tìm thấy khối văn bản phù hợp, đang dùng contour lớn nhất.")
        largestContour = contours[0]
    
    minAreaRect = cv2.minAreaRect(largestContour)
    
    # Lấy góc
    angle = minAreaRect[-1]
    
    # Chuẩn hóa góc để đảm bảo nó luôn là góc nhỏ nhất cần xoay
    if angle < -45:
        angle = 90 + angle
    
    # Trả về góc cần xoay
    return angle
# Rotate the image around its center
def rotateImage(cvImage, angle: float):
    newImage = cvImage.copy()
    (h, w) = newImage.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    newImage = cv2.warpAffine(newImage, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return newImage

def noise_removal(image):
    import numpy as np
    kernel = np.ones((1, 1), np.uint8)
    image = cv2.dilate(image, kernel, iterations=1)
    kernel = np.ones((1, 1), np.uint8)
    image = cv2.erode(image, kernel, iterations=1)
    image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
    image = cv2.medianBlur(image, 3)
    return (image)
# Deskew image
def deskew(cvImage):
    angle = getSkewAngle(cvImage)
    return rotateImage(cvImage, angle)

def display(im_path):
    dpi = 80
    im_data = plt.imread(im_path)
    height, width = im_data.shape
    
    figsize = width/ float(dpi), height/float(dpi)
    
    fig = plt.figure(figsize = figsize)
    ax = fig.add_axes([0, 0, 1, 1])
    
    ax.axis('off')
    ax.imshow(im_data, cmap='gray')
    plt.show()

def process_image_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Tăng độ nét (Sharpen)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
    sharp = cv2.filter2D(gray, -1, kernel)

# Nâng contrast bằng adaptive threshold
    thresh = cv2.adaptiveThreshold(
        sharp, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY, 35, 15
    )
    resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(r"D:/VS code insider/project/temp/product.jpg", resized)
    return resized




