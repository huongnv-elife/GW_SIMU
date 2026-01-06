# ThingsBoard Gateway Simulator

## 📋 Giới thiệu

Đây là simulator cho ThingsBoard Gateway kết nối qua MQTT, hỗ trợ các tính năng:
- **Gateway device** (GWPS_105) với các RPC methods riêng
- **Virtual lock devices** (LOCK_105) có thể nhận RPC từ ThingsBoard
- **Telemetry & Attributes** tự động gửi định kỳ
- **Gateway MQTT API** chuẩn theo ThingsBoard documentation

## 🏗️ Kiến trúc hệ thống

```
Postman → ThingsBoard API → Gateway RPC → Virtual Lock → Response ngược lại
```

## 🔧 Cấu hình

### Broker Settings
```python
BROKERS = {
    "thingsboard": {
        "host": "192.168.44.134",
        "port": 1883,
        "access_token": "5xaFxOYnnmaLuQeSQfwA",
        # ... các topics
    }
}
```

### Virtual Devices
```python
virtual_lock_devices = {

}
```

## 📡 Luồng tin nhắn RPC

### 🔄 Sequence Diagram

```mermaid
sequenceDiagram
    participant P as Postman
    participant T as ThingsBoard
    participant G as Gateway (GWPS_105)
    participant L as Lock Device (LOCK_105)

    P->>T: POST /api/plugins/rpc/twoway/{LOCK_105_DEVICE_ID}
    Note over P,T: {"method": "setLockState", "params": "unlocked"}
    
    T->>G: MQTT v1/gateway/rpc
    Note over T,G: {"device": "LOCK_105", "data": {"id": "123", "method": "setLockState", "params": "unlocked"}}
    
    G->>L: Xử lý RPC nội bộ
    Note over G,L: handle_lock_rpc("LOCK_105", "setLockState", "unlocked")
    
    L->>G: Trả kết quả
    Note over L,G: {"success": true, "status": "Lock unlocked successfully"}
    
    G->>T: MQTT v1/gateway/rpc
    Note over G,T: {"device": "LOCK_105", "id": "123", "data": {"success": true, "status": "Lock unlocked successfully"}}
    
    T->>P: HTTP Response
    Note over T,P: {"success": true, "status": "Lock unlocked successfully"}
```

## 🧪 Hướng dẫn Test với Postman

### Bước 1: Lấy JWT Token
**Request:**
```
POST http://192.168.44.134:8080/api/auth/login
Content-Type: application/json

{
  "username": "tenant@thingsboard.org",
  "password": "tenant"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzUxMiJ9...",
  "refreshToken": "eyJhbGciOiJIUzUxMiJ9..."
}
```

### Bước 2: Lấy Device ID của LOCK_105
**Request:**
```
GET http://192.168.44.134:8080/api/tenant/devices?deviceName=LOCK_105
Header: X-Authorization: Bearer {JWT_TOKEN}
```

**Response:**
```json
{
  "id": {
    "entityType": "DEVICE",
    "id": "d8a3c7c0-1234-5678-90ab-cdef12345678"
  },
  "name": "LOCK_105"
}
```

### Bước 3: Gửi RPC đến Lock Device
**Request:**
```
POST http://192.168.44.134:8080/api/plugins/rpc/twoway/{LOCK_105_DEVICE_ID}
Headers: 
  Content-Type: application/json
  X-Authorization: Bearer {JWT_TOKEN}

Body:
```

#### 📋 Các RPC Methods có thể test:

**1. setLockState - Thay đổi trạng thái khóa**
```json
{
  "method": "setLockState",
  "params": "unlocked"
}
```

**2. getLockState - Lấy trạng thái hiện tại**
```json
{
  "method": "getLockState", 
  "params": {}
}
```

**3. getLockInfo - Lấy thông tin đầy đủ**
```json
{
  "method": "getLockInfo",
  "params": {}
}
```

### Bước 4: Kiểm tra Response

**Response thành công:**
```json
{
  "success": true,
  "status": "Lock unlocked successfully"
}
```

**Response lỗi:**
```json
{
  "success": false,
  "error": "Invalid state"
}
```

## 🔍 Logging và Debug

### Các topics MQTT được subscribe:
- `v1/devices/me/rpc/request/+` - RPC cho gateway device
- `v1/gateway/rpc` - RPC cho các devices qua gateway

### Log mẫu khi nhận RPC:
```
📨 Nhận message từ topic: v1/gateway/rpc
📦 Payload: {
  "device": "LOCK_105",
  "data": {
    "id": "19",
    "method": "setLockState",
    "params": "unlocked"
  }
}

🎯 Xử lý RPC cho LOCK_105
✅ Lock LOCK_105 changed: locked → unlocked
✅ RPC response từ LOCK_105: {'success': True, 'status': 'Lock unlocked successfully'}
```

## ⚙️ Các tính năng khác

### Telemetry tự động
- Battery level giảm dần theo thời gian
- RSSI signal thay đổi ngẫu nhiên
- Gửi telemetry mỗi 30 giây

### Gateway Device RPC
Các methods cho gateway device (GWPS_105):
- `setPowerSaverState` - Bật/tắt power saver
- `getPowerSaverState` - Lấy trạng thái power saver
- `setPowerSaverConfig` - Cấu hình power saver
- `getPowerSaverConfig` - Lấy cấu hình power saver

### Attributes
Các attributes được đồng bộ:
- Device name, location, model
- Firmware version, device type
- Connection status

## 🚀 Chạy simulator

```bash
python gateway_simulator.py
```

Simulator sẽ:
1. Kết nối MQTT đến ThingsBoard
2. Kết nối virtual lock devices
3. Gửi attributes và telemetry ban đầu
4. Sẵn sàng nhận RPC từ ThingsBoard

## 🐛 Xử lý lỗi thường gặp

### Lỗi kết nối MQTT
- Kiểm tra IP và port của ThingsBoard MQTT broker
- Kiểm tra access token của gateway device

### RPC không hoạt động
- Đảm bảo gửi RPC đến đúng LOCK_105 device ID
- Kiểm tra JWT token còn hiệu lực
- Xem log simulator để debug

### Device không xuất hiện trên ThingsBoard
- Kiểm tra gateway có kết nối thành công
- Đảm bảo virtual devices được gửi connect message

## 📞 Hỗ trợ

Khi gặp vấn đề, kiểm tra:
1. Log của simulator để xem chi tiết lỗi
2. ThingsBoard Device Telemetry để xem dữ liệu
3. ThingsBoard Rule Chains để debug luồng RPC

---
**Note:** Simulator này mô phỏng hoạt động của ThingsBoard Gateway thực tế, phù hợp cho testing và development.

# ThingsBoard Gateway Simulator - Sequence Diagrams

## 📋 Danh sách các Sequence Diagrams

### 1. RPC to Lock Device
### 2. Gateway Device Telemetry
### 3. Gateway Device Attributes
### 4. Lock Device Telemetry
### 5. Lock Device Attributes
### 6. Gateway Device RPC
### 7. Periodic Telemetry

## 🔄 1. RPC to Lock Device Sequence

```mermaid
sequenceDiagram
    title: RPC to Lock Device via Gateway

    participant P as Postman/API
    participant T as ThingsBoard Server
    participant G as Gateway (GWPS_105)
    participant L as Lock Device (LOCK_105)

    Note over P: Gửi RPC đến LOCK_105 device

    P->>T: POST /api/plugins/rpc/twoway/{LOCK_105_DEVICE_ID}
    Note right of P: Headers: X-Authorization: Bearer {JWT}<br>Body: {"method": "setLockState", "params": "unlocked"}

    T->>T: Xác thực & chuyển đổi RPC
    Note right of T: Chuyển thành Gateway RPC format

    T->>G: MQTT Publish: v1/gateway/rpc
    Note right of T: {"device": "LOCK_105", "data": {"id": "19", "method": "setLockState", "params": "unlocked"}}

    G->>G: Parse Gateway RPC
    Note right of G: Nhận device="LOCK_105"<br>Gọi handle_lock_rpc()

    G->>L: Internal function call
    Note right of G: handle_lock_rpc("LOCK_105", "setLockState", "unlocked")

    L->>L: Xử lý logic
    Note right of L: Thay đổi state locked→unlocked<br>Cập nhật telemetry

    L->>G: Return response
    Note right of L: {"success": true, "status": "Lock unlocked successfully"}

    G->>T: MQTT Publish: v1/gateway/rpc
    Note right of G: {"device": "LOCK_105", "id": "19", "data": {"success": true, "status": "Lock unlocked successfully"}}

    T->>P: HTTP 200 OK
    Note right of T: {"success": true, "status": "Lock unlocked successfully"}
```

## 📊 2. Gateway Device Telemetry Sequence

```mermaid
sequenceDiagram
    title: Gateway Device Telemetry Upload

    participant G as Gateway (GWPS_105)
    participant T as ThingsBoard Server
    participant D as ThingsBoard Database

    Note over G: Gateway thay đổi trạng thái

    G->>G: set_power_saver_state("on")
    Note right of G: Cập nhật powerState = "on"

    G->>T: MQTT Publish: v1/devices/me/telemetry
    Note right of G: {"powerState": "on"}

    T->>D: Lưu telemetry data
    Note right of T: Lưu vào database<br>Cập nhật latest values

    T->>G: MQTT Ack (nếu có)
    Note right of T: Xác nhận nhận telemetry

    G->>G: Log kết quả
    Note right of G: "✅ Đã gửi Telemetry: powerState = on"
```

## 🏷️ 3. Gateway Device Attributes Sequence

```mermaid
sequenceDiagram
    title: Gateway Device Attributes Upload

    participant G as Gateway (GWPS_105)
    participant T as ThingsBoard Server
    participant D as ThingsBoard Database

    Note over G: Gateway cập nhật cấu hình

    G->>G: set_power_saver_config()
    Note right of G: Cập nhật relayOffTimeout, powerMode

    G->>T: MQTT Publish: v1/devices/me/attributes
    Note right of G: {"relayOffTimeout": 30, "powerMode": "public"}

    T->>D: Lưu attributes
    Note right of T: Lưu client attributes<br>Cập nhật device profile

    T->>G: MQTT Ack (nếu có)

    G->>G: Log kết quả
    Note right of G: "✅ Đã cập nhật cấu hình"
```

## 🔐 4. Lock Device Telemetry Sequence

```mermaid
sequenceDiagram
    title: Lock Device Telemetry via Gateway

    participant L as Lock Device (LOCK_105)
    participant G as Gateway (GWPS_105)
    participant T as ThingsBoard Server
    participant D as ThingsBoard Database

    Note over L: Lock device thay đổi trạng thái

    L->>L: State change hoặc periodic update
    Note right of L: battery--, rssi thay đổi<br>state thay đổi

    L->>G: Internal: gateway_publish_telemetry()
    Note right of L: {"battery": 84.9, "rssi": -67, "state": "unlocked"}

    G->>T: MQTT Publish: v1/gateway/telemetry
    Note right of G: {"LOCK_105": [{"ts": 1630000000000, "values": {"battery": 84.9, "rssi": -67, "state": "unlocked"}}]}

    T->>D: Lưu telemetry cho LOCK_105
    Note right of T: Phân loại theo device<br>Lưu timestamp

    T->>G: MQTT Ack (nếu có)

    G->>L: Log kết quả
    Note right of G: "✅ Telemetry từ LOCK_105"
```

## 📝 5. Lock Device Attributes Sequence

```mermaid
sequenceDiagram
    title: Lock Device Attributes via Gateway

    participant L as Lock Device (LOCK_105)
    participant G as Gateway (GWPS_105)
    participant T as ThingsBoard Server
    participant D as ThingsBoard Database

    Note over L: Lock device kết nối lần đầu

    L->>G: Internal: gateway_publish_attributes()
    Note right of L: {"name": "LOCK_105", "location": "Main Entrance", "model": "SmartLock V2"}

    G->>T: MQTT Publish: v1/gateway/attributes
    Note right of G: {"LOCK_105": {"name": "LOCK_105", "location": "Main Entrance", "model": "SmartLock V2"}}

    T->>D: Lưu attributes cho LOCK_105
    Note right of T: Tạo/update device attributes<br>Cập nhật device info

    T->>G: MQTT Ack (nếu có)

    G->>L: Log kết quả
    Note right of G: "✅ Attributes từ LOCK_105"
```

## ⚡ 6. Gateway Device RPC Sequence

```mermaid
sequenceDiagram
    title: Direct RPC to Gateway Device

    participant P as Postman/API
    participant T as ThingsBoard Server
    participant G as Gateway (GWPS_105)

    Note over P: Gửi RPC trực tiếp đến Gateway

    P->>T: POST /api/plugins/rpc/twoway/{GWPS_105_DEVICE_ID}
    Note right of P: Body: {"method": "setPowerSaverState", "params": "on"}

    T->>G: MQTT Publish: v1/devices/me/rpc/request/
    Note right of T: {"method": "setPowerSaverState", "params": "on"}

    G->>G: Xử lý RPC cho gateway
    Note right of G: Gọi set_power_saver_state("on")<br>Cập nhật internal state

    G->>G: Gửi telemetry & attributes
    Note right of G: Tự động gửi powerState update

    G->>T: MQTT Publish: v1/devices/me/rpc/response/{id}
    Note right of G: {"success": true}

    T->>P: HTTP 200 OK
    Note right of T: {"success": true}
```

## 🔄 7. Periodic Telemetry Sequence

```mermaid
sequenceDiagram
    title: Automatic Periodic Telemetry

    participant Timer as System Timer
    participant G as Gateway (GWPS_105)
    participant L as Lock Devices
    participant T as ThingsBoard Server

    Note over Timer: Mỗi 30 giây

    Timer->>G: simulate_lock_telemetry()
    Note right of Timer: Gọi hàm định kỳ

    G->>L: Lặp qua tất cả lock devices
    Note right of G: for device_id in virtual_lock_devices

    L->>L: Cập nhật giá trị
    Note right of L: battery -= 0.1<br>rssi thay đổi ngẫu nhiên

    L->>G: gateway_publish_telemetry()
    Note right of L: {"battery": 84.8, "rssi": -68, "state": "unlocked"}

    G->>T: MQTT Publish: v1/gateway/telemetry
    Note right of G: Gửi telemetry cho từng device

    T->>G: MQTT Ack (nếu có)

    G->>G: Log kết quả
    Note right of G: "📊 Sent periodic telemetry"
```

## 🔌 8. Device Connection Sequence

```mermaid
sequenceDiagram
    title: Device Connection via Gateway

    participant G as Gateway (GWPS_105)
    participant T as ThingsBoard Server
    participant D as ThingsBoard Database

    Note over G: Gateway khởi động

    G->>T: MQTT Connect
    Note right of G: Kết nối với access_token

    T->>G: MQTT ConnAck
    Note right of T: Xác nhận kết nối thành công

    G->>T: MQTT Subscribe
    Note right of G: Subscribe: v1/gateway/rpc

    loop For each virtual device
        G->>T: MQTT Publish: v1/gateway/connect
        Note right of G: {"device": "LOCK_105"}
        
        T->>D: Đánh dấu device connected
        Note right of T: Cập nhật trạng thái online
        
        G->>T: MQTT Publish: v1/gateway/attributes
        Note right of G: Gửi device attributes
        
        G->>T: MQTT Publish: v1/gateway/telemetry
        Note right of G: Gửi telemetry ban đầu
    end

    G->>G: Log completion
    Note right of G: "🚀 Đã kết nối X lock devices"
```

## 🛠️ 9. Error Handling Sequence

```mermaid
sequenceDiagram
    title: RPC Error Handling

    participant P as Postman/API
    participant T as ThingsBoard Server
    participant G as Gateway (GWPS_105)

    P->>T: POST /api/plugins/rpc/twoway/{LOCK_105_DEVICE_ID}
    Note right of P: {"method": "setLockState", "params": "invalid_state"}

    T->>G: MQTT Publish: v1/gateway/rpc
    Note right of T: {"device": "LOCK_105", "data": {"id": "20", "method": "setLockState", "params": "invalid_state"}}

    G->>G: handle_lock_rpc()
    Note right of G: Kiểm tra params="invalid_state"

    G->>G: Validation failed
    Note right of G: State không hợp lệ<br>Trả về error

    G->>T: MQTT Publish: v1/gateway/rpc
    Note right of G: {"device": "LOCK_105", "id": "20", "data": {"success": false, "error": "Invalid state"}}

    T->>P: HTTP 200 OK
    Note right of T: {"success": false, "error": "Invalid state"}
```

## 📈 10. Multi-Device RPC Sequence

```mermaid
sequenceDiagram
    title: Multiple Lock Devices Scenario

    participant P as Postman/API
    participant T as ThingsBoard Server
    participant G as Gateway (GWPS_105)
    participant L1 as LOCK_105
    participant L2 as LOCK_106
    participant L3 as LOCK_107

    Note over G: Gateway quản lý nhiều lock devices

    par RPC to LOCK_105
        P->>T: RPC to LOCK_105
        T->>G: Gateway RPC
        G->>L1: Process for LOCK_105
        L1->>G: Response
        G->>T: Gateway Response
        T->>P: HTTP Response
    and RPC to LOCK_106
        P->>T: RPC to LOCK_106
        T->>G: Gateway RPC
        G->>L2: Process for LOCK_106
        L2->>G: Response
        G->>T: Gateway Response
        T->>P: HTTP Response
    and Telemetry for all devices
        G->>T: Periodic telemetry
        Note right of G: Gửi cho LOCK_105, LOCK_106, LOCK_107
    end
```

Các sequence diagrams này cho thấy toàn bộ luồng hoạt động có thể test được với simulator, từ RPC đơn giản đến các scenario phức tạp với nhiều devices.