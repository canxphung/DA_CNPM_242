"""
Script để kiểm tra cài đặt cơ bản của dự án.
"""
import os
import importlib
import logging

def check_module(module_name):
    """Kiểm tra xem một module có tồn tại hay không."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def check_project_structure():
    """Kiểm tra cấu trúc thư mục dự án."""
    essential_dirs = [
        "src",
        "src/api",
        "src/core",
        "src/adapters",
        "src/infrastructure",
        "config",
        "tests"
    ]
    
    missing_dirs = []
    for d in essential_dirs:
        if not os.path.isdir(d):
            missing_dirs.append(d)
    
    return len(missing_dirs) == 0, missing_dirs

def check_dependencies():
    """Kiểm tra các phụ thuộc chính đã được cài đặt hay chưa."""
    essential_packages = [
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "redis",
        "firebase_admin",
        "Adafruit_IO",
        "pydantic"
    ]
    
    missing_packages = []
    for package in essential_packages:
        if not check_module(package.replace("-", "_")):
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def main():
    """Chức năng chính."""
    print("=== Kiểm tra cài đặt Core Operations Service ===\n")
    
    # Kiểm tra cấu trúc thư mục
    structure_ok, missing_dirs = check_project_structure()
    if structure_ok:
        print("✅ Cấu trúc thư mục: OK")
    else:
        print("❌ Cấu trúc thư mục: Thiếu các thư mục sau:")
        for d in missing_dirs:
            print(f"  - {d}")
    
    # Kiểm tra phụ thuộc
    deps_ok, missing_packages = check_dependencies()
    if deps_ok:
        print("✅ Phụ thuộc: Tất cả đã được cài đặt")
    else:
        print("❌ Phụ thuộc: Thiếu các package sau:")
        for p in missing_packages:
            print(f"  - {p}")
    
    # Kiểm tra tệp .env
    if os.path.isfile('.env'):
        print("✅ Tệp .env: Tìm thấy")
    else:
        print("❌ Tệp .env: Không tìm thấy")
    
    print("\n=== Tóm tắt ===")
    if structure_ok and deps_ok and os.path.isfile('.env'):
        print("🎉 Tất cả kiểm tra đều PASS! Dự án đã sẵn sàng để phát triển.")
    else:
        print("⚠️ Một số kiểm tra KHÔNG PASS. Hãy giải quyết các vấn đề trên trước khi tiếp tục.")

if __name__ == "__main__":
    main()