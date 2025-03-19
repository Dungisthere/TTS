# Sử dụng image chính thức của Ubuntu 22.04
FROM ubuntu:22.04 AS builder


# Thiết lập biến môi trường để tránh các thông báo trong quá trình cài đặt
ENV DEBIAN_FRONTEND=noninteractive


# Cập nhật danh sách các gói và cài đặt các gói cần thiết
RUN apt-get update && \
    apt-get install -y python3 python3-pip git nano htop && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Thiết lập thư mục làm việc trong container
WORKDIR /_app_

# Sao chép toàn bộ mã nguồn vào container
COPY . /_app_


# Cài đặt các gói yêu cầu
RUN pip3 install --no-cache-dir --upgrade -r /_app_/requirements.txt


# Xóa thư mục .venv nếu có
RUN rm -rf /_app_/.venv || true


# Lệnh để chạy ứng dụng
CMD ["python3", "run_api.py"]