# GW_SIMU Project

Dự án mô phỏng Gateway và Lock system sử dụng MQTT protocol.

## 📁 Cấu trúc thư mục

```
GW_SIMU/
├── gw_simu_101.py      # Gateway simulation
├── lock_simu_101.py    # Lock device simulation  
├── requirements.txt    # Python dependencies
└── venv/              # Virtual environment (không đẩy lên git)
```

## 🚀 Cài đặt và Chạy

### 1. Clone repository
```bash
git clone https://github.com/huongnv-elife/GW_SIMU.git
cd GW_SIMU
```

### 2. Thiết lập Virtual Environment
```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt venv
source venv/bin/activate

# Trên Windows (PowerShell):
# venv\Scripts\activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Chạy ứng dụng

#### Chạy Gateway Simulator:
```bash
python gw_simu_101.py
```

#### Chạy Lock Simulator:
```bash
python lock_simu_101.py
```

## 🔧 Cấu hình

### MQTT Broker Settings
Các file simulator sử dụng MQTT broker mặc định:
- **Host**: `localhost` hoặc `test.mosquitto.org`
- **Port**: `1883`
- **Topics**: 
  - Gateway: `gateway/status`
  - Lock: `lock/status`

### Virtual Environment Auto-activation (Optional)
Để tự động kích hoạt venv mỗi khi vào thư mục, thêm vào `~/.bashrc`:
```bash
# Auto activate venv for GW_SIMU
cd() {
    builtin cd "$@"
    if [[ -d "venv" ]] && [[ -z "$VIRTUAL_ENV" ]]; then
        source venv/bin/activate
    fi
}
```

Hoặc tạo alias:
```bash
echo 'alias gw_simu="cd ~/Documents/GW_SIMU && source venv/bin/activate"' >> ~/.bashrc
source ~/.bashrc
```

## 📋 Requirements

Các thư viện Python cần thiết (tự động cài đặt từ requirements.txt):

- **paho-mqtt**: MQTT client implementation
- Các thư viện standard khác...

Xem file `requirements.txt` để biết đầy đủ dependencies.

## 🛠 Troubleshooting

### Lỗi "ModuleNotFoundError: No module named 'paho'"
```bash
# Đảm bảo venv đã được kích hoạt
source venv/bin/activate

# Cài đặt lại dependencies
pip install -r requirements.txt
```

### Lỗi kết nối MQTT
- Kiểm tra kết nối internet
- Đảm bảo MQTT broker đang chạy
- Kiểm tra firewall settings

### Lỗi Git authentication
```bash
# Sử dụng SSH để tránh đăng nhập nhiều lần
git remote set-url origin git@github.com:huongnv-elife/GW_SIMU.git
```

## 🔄 Development Workflow

1. **Luôn kích hoạt venv trước khi làm việc:**
   ```bash
   source venv/bin/activate
   ```

2. **Cài đặt thư viện mới:**
   ```bash
   pip install <package_name>
   pip freeze > requirements.txt  # Cập nhật dependencies
   ```

3. **Chạy thử ứng dụng:**
   ```bash
   python gw_simu_101.py
   python lock_simu_101.py
   ```

## 📝 Ghi chú

- Dự án sử dụng Python 3.6+
- Virtual environment giúp cô lập dependencies
- File `venv/` không nên được đẩy lên git (đã có trong .gitignore)

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

---

**Lưu ý**: Đảm bảo virtual environment luôn được kích hoạt trước khi chạy các script Python.
