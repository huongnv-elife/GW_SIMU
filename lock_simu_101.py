import paho.mqtt.client as mqtt
import json
import time
import random
import base64
import re
import socket
from datetime import datetime
import threading

# ==================== CẤU HÌNH ====================
DEVICE_NAME = "eedge/Canopi Gateway - Power Saver_00:FF:FF:FF:FF:FD"

# ==================== THINGSBOARD CONFIG ====================
THINGSBOARD_CONFIG = {
    "host": "192.168.1.62", 
    "port": 1883,
    "access_token": "wKQRMtBvLLo0bTDy9VIA",
    "rpc_request_topic": "v1/devices/me/rpc/request/+",  # ĐỂ NHẬN RPC TỪ SERVER
    "telemetry_topic": "v1/devices/me/telemetry",
    "attributes_topic": "v1/devices/me/attributes",
    "response_template": "v1/devices/me/rpc/response/{}",  # ĐỂ GỬI RESPONSE VỀ SERVER
}

# ==================== TRẠNG THÁI & CẤU HÌNH ====================
power_saver_lock_state = "off"
power_saver_config = {
    "relayOffTimeout": 30,
    "powerMode": "public"
}

# 🔹 LƯU TRỮ THÔNG TIN CÁC LOCK ĐÃ LINK
linked_locks = {}  # Format: {lockId: {lmsLockId, lockMac, bleSessionToken, tbLockName, linkedAt}}

client = None
start_time = time.time()

# ==================== DEBUG & LOGGING ====================
def log_debug(message, level="INFO"):
    """Ghi log với timestamp và level"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    
    # Ghi vào file log
    with open("gateway_client_debug.log", "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

# ==================== NETWORK CHECK ====================
def check_network_connection():
    """Kiểm tra kết nối mạng đến ThingsBoard"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        result = sock.connect_ex((THINGSBOARD_CONFIG["host"], THINGSBOARD_CONFIG["port"]))
        if result == 0:
            log_debug(f"✅ Network: Có thể kết nối tới {THINGSBOARD_CONFIG['host']}:{THINGSBOARD_CONFIG['port']}")
            return True
        else:
            log_debug(f"❌ Network: KHÔNG thể kết nối tới {THINGSBOARD_CONFIG['host']}:{THINGSBOARD_CONFIG['port']}", "ERROR")
            return False
    except Exception as e:
        log_debug(f"❌ Network lỗi: {e}", "ERROR")
        return False
    finally:
        sock.close()

# ==================== HÀM MQTT GỬI DỮ LIỆU ====================
def publish_telemetry(payload):
    """Gửi telemetry lên ThingsBoard"""
    topic = THINGSBOARD_CONFIG["telemetry_topic"]
    result = client.publish(topic, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        log_debug(f"✅ Telemetry → {topic} | Payload: {json.dumps(payload)}")
    else:
        log_debug(f"❌ Lỗi gửi telemetry (rc={result.rc})", "ERROR")

def publish_attributes(payload):
    """Gửi attributes lên ThingsBoard"""
    topic = THINGSBOARD_CONFIG["attributes_topic"]
    result = client.publish(topic, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        log_debug(f"✅ Attributes → {topic} | Payload: {json.dumps(payload)}")
    else:
        log_debug(f"❌ Lỗi gửi attributes (rc={result.rc})", "ERROR")

def send_rpc_response(request_id, response):
    """Gửi RPC response về ThingsBoard"""
    topic = THINGSBOARD_CONFIG["response_template"].format(request_id)
    result = client.publish(topic, json.dumps(response), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        log_debug(f"✅ RPC Response → {topic} | Payload: {json.dumps(response)}")
    else:
        log_debug(f"❌ Lỗi gửi RPC response (rc={result.rc})", "ERROR")

# ==================== HÀM GỬI LINK LOCK TELEMETRY ====================
def send_link_lock_telemetry(tb_lock_id, lock_info):
    """
    Gửi telemetry link_lock sau khi link lock thành công
    Delay 10 giây sau khi trả về RPC response
    
    Format:
    {
        "link_lock": {
            "deviceId": "xxxx",  // Thingsboard gateway device ID
            "event": "GATEWAY_CONNECTED_LOCK",
            "ts": 1609459200000,  // Timestamp
            "data": {
                "lockId": "xxxx",  // Thingsboard lock device ID
                "lockMac": "AA:BB:CC:DD:EE:FF",
                "rssi": -89,  // signal strength
                "error_code": 0,  // 0: success
                "is_success": true  // infer from error_code
            }
        }
    }
    """
    def send_after_delay():
        """Gửi telemetry sau delay 10 giây"""
        log_debug(f"⏳ Đang đợi 10 giây để gửi link_lock telemetry cho lock {tb_lock_id}...")
        time.sleep(10)
        
        # Tạo RSSI ngẫu nhiên (giả lập signal strength)
        rssi = random.randint(-95, -60)  # -95 đến -60 dBm
        
        # Tạo telemetry link_lock
        link_lock_data = {
            "deviceId": DEVICE_NAME,  # Gateway device ID
            "event": "GATEWAY_CONNECTED_LOCK",
            "ts": int(time.time() * 1000),  # Current timestamp in milliseconds
            "data": {
                "lockId": tb_lock_id,
                "lockMac": lock_info["lockMac"],
                "rssi": rssi,
                "error_code": 0,  # Success
                "is_success": True
            }
        }
        
        # Tạo payload telemetry
        telemetry_payload = {
            "link_lock": link_lock_data
        }
        
        # Gửi telemetry
        publish_telemetry(telemetry_payload)
        
        log_debug(f"📡 Đã gửi link_lock telemetry:")
        log_debug(f"   • Lock ID: {tb_lock_id}")
        log_debug(f"   • Lock MAC: {lock_info['lockMac']}")
        log_debug(f"   • RSSI: {rssi} dBm")
        log_debug(f"   • Event: GATEWAY_CONNECTED_LOCK")
        log_debug(f"   • Timestamp: {link_lock_data['ts']}")
        
        # Cập nhật lastSeen trong lock info
        if tb_lock_id in linked_locks:
            linked_locks[tb_lock_id]["lastSeen"] = int(time.time() * 1000)
            linked_locks[tb_lock_id]["lastRSSI"] = rssi
            linked_locks[tb_lock_id]["connectionStatus"] = "connected"
            
            log_debug(f"✅ Đã cập nhật connection status cho lock {tb_lock_id}")
    
    # Chạy trong thread riêng để không block main thread
    thread = threading.Thread(target=send_after_delay, daemon=True)
    thread.start()
    
    log_debug(f"🔄 Đã khởi động thread gửi link_lock telemetry sau 10 giây")

# ==================== SIMULATE GATEWAY TELEMETRY ====================
def simulate_gateway_telemetry():
    """
    Gửi telemetry cho gateway device (DEVICE_NAME)
    Bao gồm powerState với giá trị "on" hoặc "off" ngẫu nhiên
    """
    # Tạo giá trị powerState ngẫu nhiên (on/off)
    power_state = random.choice(["on", "off"])
    
    # Các giá trị telemetry cho gateway
    telemetry_data = {
        "powerState": power_state,
        "active": True,
        "gatewayUptime": int(time.time() - start_time),
        "memoryUsage": round(random.uniform(30.0, 80.0), 2),
        "cpuLoad": round(random.uniform(5.0, 50.0), 2),
        "networkQuality": random.choice(["excellent", "good", "fair", "poor"]),
        "linkedLocksCount": len(linked_locks),
        "lastHeartbeat": int(time.time() * 1000),
        "ts": int(time.time() * 1000)
    }
    
    # Gửi telemetry
    publish_telemetry(telemetry_data)
    
    log_debug(f"📊 Telemetry sent: powerState={power_state}, linkedLocks={len(linked_locks)}")
    
    return telemetry_data

def send_active_status():
    """Gửi trạng thái active định kỳ để giữ State là Active"""
    # Gửi shared attributes
    attributes_payload = {"active": True}
    publish_attributes(attributes_payload)
    log_debug(f"🔥 Gửi active status: True")

# ==================== XỬ LÝ RPC GATEWAY ====================
def set_power_saver_lock_state(lock_state):
    global power_saver_lock_state

    if lock_state not in ["on", "off"]:
        log_debug(f"❌ Trạng thái không hợp lệ: {lock_state}", "ERROR")
        return {"success": False}

    log_debug(f"⚙️ Đang chuyển Power Saver → {lock_state.upper()}")
    power_saver_lock_state = lock_state
    log_debug(f"✅ Power Saver hiện đang {lock_state.upper()}")

    telemetry = {"powerlock_state": lock_state}
    publish_telemetry(telemetry)

    attributes = {"powerlock_state": lock_state}
    publish_attributes(attributes)

    log_debug(f"📡 Đã gửi Telemetry + Attribute: powerlock_state = {lock_state}")
    return {"success": True}

def get_power_saver_lock_state():
    global power_saver_lock_state
    if power_saver_lock_state not in ["on", "off"]:
        log_debug(f"⚠️ lock_state không hợp lệ: {power_saver_lock_state}", "WARNING")
        return {"success": False}
    log_debug(f"🔍 Trả về trạng thái Power Saver: {power_saver_lock_state}")
    return {"success": True, "result": power_saver_lock_state}

def set_power_saver_config(params):
    global power_saver_config

    if not isinstance(params, dict):
        return {"success": False}

    if "relayOffTimeout" in params:
        try:
            power_saver_config["relayOffTimeout"] = int(params["relayOffTimeout"])
        except Exception:
            log_debug(f"⚠️ relayOffTimeout không hợp lệ", "WARNING")
            return {"success": False}

    if "powerMode" in params:
        if params["powerMode"] in ["public", "private"]:
            power_saver_config["powerMode"] = params["powerMode"]
        else:
            log_debug(f"⚠️ powerMode không hợp lệ", "WARNING")
            return {"success": False}

    log_debug(f"✅ Đã cập nhật cấu hình: {power_saver_config}")
    publish_attributes(power_saver_config)
    return {"success": True}

def get_power_saver_config():
    global power_saver_config
    log_debug(f"🔍 Trả về cấu hình Power Saver: {power_saver_config}")
    return {"success": True, "result": power_saver_config}

# ==================== XỬ LÝ RPC LINK LOCK ====================
def handle_link_lock(params):
    """
    Xử lý RPC linkLock
    Format params:
    {
        "lockId": "xxxx",        // Thingsboard lock ID
        "lmsLockId": "yyyy",       // LMS lock ID  
        "lockMac": "AA:BB:CC:DD:EE:FF",
        "bleSessionToken": "base64-string",
        "tbLockName": "CNP-lock-001122"
    }
    
    Response: {"code": 0}
    """
    log_debug(f"🔗 Nhận RPC linkLock với params: {json.dumps(params, indent=2)}")
    
    # Kiểm tra các trường bắt buộc
    required_fields = ["lockId", "lmsLockId", "lockMac", "bleSessionToken", "tbLockName"]
    missing_fields = [field for field in required_fields if field not in params]
    
    if missing_fields:
        log_debug(f"❌ Thiếu trường bắt buộc: {missing_fields}", "ERROR")
        return {"code": 1, "error": f"Missing required fields: {missing_fields}"}
    
    # Lấy thông tin từ params
    tb_lock_id = params["lockId"]
    lms_lock_id = params["lmsLockId"]
    lock_mac = params["lockMac"]
    ble_session_token = params["bleSessionToken"]
    tb_lock_name = params["tbLockName"]
    
    # Kiểm tra token base64
    try:
        decoded_token = base64.b64decode(ble_session_token)
        token_length = len(decoded_token)
        log_debug(f"🔑 BLE Session Token decoded: {token_length} bytes")
    except Exception as e:
        log_debug(f"❌ BLE Session Token không hợp lệ (base64): {e}", "ERROR")
        return {"code": 2, "error": "Invalid BLE session token format"}
    
    # Kiểm tra MAC address format
    if not validate_mac_address(lock_mac):
        log_debug(f"❌ MAC address không hợp lệ: {lock_mac}", "ERROR")
        return {"code": 3, "error": "Invalid MAC address format"}
    
    # Kiểm tra xem lock đã được link chưa
    if tb_lock_id in linked_locks:
        log_debug(f"⚠️ Lock {tb_lock_id} đã được link trước đó, sẽ cập nhật thông tin mới", "WARNING")
    
    # Lưu thông tin lock vào linked_locks
    lock_info = {
        "lmsLockId": lms_lock_id,
        "lockMac": lock_mac.upper(),
        "bleSessionToken": ble_session_token,
        "tbLockName": tb_lock_name,
        "linkedAt": int(time.time() * 1000),
        "status": "linking",  # Trạng thái đang kết nối
        "lastSeen": int(time.time() * 1000),
        "connectionStatus": "connecting"
    }
    
    linked_locks[tb_lock_id] = lock_info
    
    log_debug(f"✅ Đã nhận link lock request thành công:")
    log_debug(f"   • TB Lock ID: {tb_lock_id}")
    log_debug(f"   • TB Lock Name: {tb_lock_name}")
    log_debug(f"   • LMS Lock ID: {lms_lock_id}")
    log_debug(f"   • MAC Address: {lock_mac.upper()}")
    log_debug(f"   • Token Length: {len(ble_session_token)} chars")
    log_debug(f"   • Total Linked Locks: {len(linked_locks)}")
    
    # Gửi telemetry cập nhật số lượng lock đã link
    telemetry_update = {
        "linkedLocksCount": len(linked_locks),
        "lastLinkedLock": tb_lock_name,
        "lastLinkedAt": int(time.time() * 1000),
        "ts": int(time.time() * 1000)
    }
    
    publish_telemetry(telemetry_update)
    
    # Gửi attributes cập nhật danh sách lock
    update_locks_attributes()
    
    log_debug(f"📝 Lock device {tb_lock_name} đang được xử lý...")
    
    # 🔥 THÊM: Khởi động thread để gửi link_lock telemetry sau 10 giây
    send_link_lock_telemetry(tb_lock_id, lock_info)
    
    # Trả về response theo format yêu cầu
    return {"code": 0}

# ==================== XỬ LÝ RPC UNLINK LOCK ====================
def handle_unlink_lock(params):
    """
    Xử lý RPC unlinkLock
    Format params:
    {
        "tbLockId": "xxxx",        // Thingsboard lock ID
        "lmsLockId": "yyyy"        // LMS lock ID
    }
    
    Response: {"code": 0} nếu thành công
    """
    log_debug(f"🔓 Nhận RPC unlinkLock với params: {json.dumps(params, indent=2)}")
    
    # Kiểm tra các trường bắt buộc
    required_fields = ["tbLockId", "lmsLockId"]
    missing_fields = [field for field in required_fields if field not in params]
    
    if missing_fields:
        log_debug(f"❌ Thiếu trường bắt buộc: {missing_fields}", "ERROR")
        return {"code": 1, "error": f"Missing required fields: {missing_fields}"}
    
    # Lấy thông tin từ params
    tb_lock_id = params["tbLockId"]
    lms_lock_id = params["lmsLockId"]
    
    # Kiểm tra xem lock có tồn tại không
    if tb_lock_id not in linked_locks:
        log_debug(f"❌ Lock ID {tb_lock_id} không tồn tại trong danh sách linked locks", "ERROR")
        return {"code": 4, "error": f"Lock ID {tb_lock_id} not found"}
    
    # Kiểm tra LMS Lock ID có khớp không
    lock_info = linked_locks[tb_lock_id]
    if lock_info["lmsLockId"] != lms_lock_id:
        log_debug(f"⚠️ LMS Lock ID không khớp: expected {lock_info['lmsLockId']}, got {lms_lock_id}", "WARNING")
        # Vẫn tiếp tục unlink nếu chỉ cung cấp tbLockId
    
    # Lưu thông tin lock trước khi xóa (cho log)
    lock_name = lock_info["tbLockName"]
    lock_mac = lock_info["lockMac"]
    
    # Xóa lock khỏi danh sách
    del linked_locks[tb_lock_id]
    
    log_debug(f"✅ Đã unlink lock thành công:")
    log_debug(f"   • TB Lock ID: {tb_lock_id}")
    log_debug(f"   • TB Lock Name: {lock_name}")
    log_debug(f"   • LMS Lock ID: {lms_lock_id}")
    log_debug(f"   • MAC Address: {lock_mac}")
    log_debug(f"   • Total Linked Locks còn lại: {len(linked_locks)}")
    
    # Gửi telemetry cập nhật số lượng lock
    telemetry_update = {
        "linkedLocksCount": len(linked_locks),
        "lastUnlinkedLock": lock_name,
        "lastUnlinkedAt": int(time.time() * 1000),
        "ts": int(time.time() * 1000)
    }
    
    publish_telemetry(telemetry_update)
    
    # Gửi attributes cập nhật danh sách lock
    update_locks_attributes()
    
    # Thêm sự kiện unlink vào telemetry
    unlink_event = {
        "eventType": "lock_unlinked",
        "lockId": tb_lock_id,
        "lockName": lock_name,
        "lmsLockId": lms_lock_id,
        "unlinkedAt": int(time.time() * 1000),
        "ts": int(time.time() * 1000)
    }
    
    publish_telemetry(unlink_event)
    
    log_debug(f"📝 Lock device {lock_name} đã được unlink")
    
    # Trả về response theo format yêu cầu
    return {"code": 0}

# ==================== XỬ LÝ RPC GET LINK LOCKS ====================
def handle_get_link_locks(params):
    """
    Xử lý RPC getLinkLocks
    Format params: {} (không có params, hoặc có thể có filter params trong tương lai)
    
    Response: 
    {
        "count": 1,
        "locks": [
            { 
                "tbLockId": "xxxx", 
                "lmsLockId": "yyyy",
                "lockMac": "AA:BB:CC:DD:EE:FF", 
                "tbLockName": "CNL-lock-001122" 
            },
        ]
    }
    """
    log_debug(f"📋 Nhận RPC getLinkLocks")
    
    # Tạo danh sách locks theo đúng format yêu cầu
    locks_list = []
    
    for lock_id, lock_info in linked_locks.items():
        lock_data = {
            "tbLockId": lock_id,  # Lưu ý: đổi từ "lockId" thành "tbLockId" theo format
            "lmsLockId": lock_info["lmsLockId"],
            "lockMac": lock_info["lockMac"],
            "tbLockName": lock_info["tbLockName"]
        }
        
        # Có thể thêm thông tin bổ sung nếu cần
        if "linkedAt" in lock_info:
            lock_data["linkedAt"] = lock_info["linkedAt"]
        if "status" in lock_info:
            lock_data["status"] = lock_info["status"]
        if "lastSeen" in lock_info:
            lock_data["lastSeen"] = lock_info["lastSeen"]
        if "connectionStatus" in lock_info:
            lock_data["connectionStatus"] = lock_info["connectionStatus"]
        if "lastRSSI" in lock_info:
            lock_data["lastRSSI"] = lock_info["lastRSSI"]
        
        locks_list.append(lock_data)
    
    # Tạo response theo đúng format
    response = {
        "count": len(locks_list),
        "locks": locks_list
    }
    
    log_debug(f"✅ Trả về danh sách {len(locks_list)} lock(s)")
    
    # Log chi tiết từng lock
    if locks_list:
        log_debug(f"📋 Chi tiết locks:")
        for i, lock in enumerate(locks_list, 1):
            status = lock.get('connectionStatus', 'unknown')
            rssi = lock.get('lastRSSI', 'N/A')
            log_debug(f"   {i}. {lock['tbLockName']} ({lock['tbLockId']}) - {lock['lockMac']} - Status: {status}, RSSI: {rssi}")
    else:
        log_debug(f"📭 Không có lock nào được link")
    
    return response

def update_locks_attributes():
    """Cập nhật attributes danh sách lock"""
    lock_list = {lock_id: {"name": info["tbLockName"], "mac": info["lockMac"]} 
                for lock_id, info in linked_locks.items()}
    publish_attributes({"linkedLocks": lock_list})

def validate_mac_address(mac):
    """Validate MAC address format"""
    mac_pattern = r'^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$'
    return re.match(mac_pattern, mac) is not None

def get_linked_locks():
    """Lấy danh sách các lock đã link (cho tương thích với method cũ)"""
    return {
        "code": 0,
        "count": len(linked_locks),
        "locks": linked_locks
    }

# ==================== DEBUG FUNCTIONS ====================
def check_connection_status():
    """Kiểm tra trạng thái kết nối MQTT"""
    if client and client.is_connected():
        log_debug(f"✅ MQTT Connected: True")
        log_debug(f"📡 Broker: {THINGSBOARD_CONFIG['host']}:{THINGSBOARD_CONFIG['port']}")
        log_debug(f"🔑 Device: {DEVICE_NAME}")
        log_debug(f"🔔 Subscribed to RPC: {THINGSBOARD_CONFIG['rpc_request_topic']}")
        return True
    else:
        log_debug(f"❌ MQTT Connected: False", "ERROR")
        return False

def simulate_incoming_rpc():
    """Giả lập RPC từ ThingsBoard để test (local test only)"""
    log_debug(f"\n🎯 [LOCAL TEST] Đang giả lập RPC từ ThingsBoard...")
    
    # Test RPC 1: linkLock
    test_rpc_linklock = {
        "method": "linkLock",
        "params": {
            "lockId": "test-lock-001",
            "lmsLockId": "lms-test-001",
            "lockMac": "AA:BB:CC:DD:EE:FF",
            "bleSessionToken": "dGVzdC1zZXNzaW9uLXRva2Vu",
            "tbLockName": "CNL-lock-001122"
        }
    }
    
    # Test RPC 2: unlinkLock
    test_rpc_unlinklock = {
        "method": "unlinkLock",
        "params": {
            "tbLockId": "test-lock-001",
            "lmsLockId": "lms-test-001"
        }
    }
    
    # Test RPC 3: getLinkLocks
    test_rpc_getlinklocks = {
        "method": "getLinkLocks",
        "params": {}
    }
    
    # Tạo topic giả lập
    test_topic = f"v1/devices/me/rpc/request/{int(time.time())}"
    
    # Gọi on_message trực tiếp để test
    class MockMsg:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = json.dumps(payload).encode()
            self.qos = 1
            self.retain = False
    
    # Test linkLock
    mock_msg = MockMsg(test_topic, test_rpc_linklock)
    on_message(client, None, mock_msg)
    
    # Đợi 12 giây để thấy link_lock telemetry được gửi (10s + buffer)
    log_debug(f"⏳ Đợi 12 giây để xem link_lock telemetry được gửi...")
    time.sleep(12)
    
    # Test getLinkLocks
    mock_msg2 = MockMsg(f"v1/devices/me/rpc/request/{int(time.time())}", test_rpc_getlinklocks)
    on_message(client, None, mock_msg2)
    
    # Đợi 2 giây rồi test unlinkLock
    time.sleep(2)
    
    mock_msg3 = MockMsg(f"v1/devices/me/rpc/request/{int(time.time())}", test_rpc_unlinklock)
    on_message(client, None, mock_msg3)
    
    # Đợi 1 giây rồi test getLinkLocks lại (sau khi unlink)
    time.sleep(1)
    
    mock_msg4 = MockMsg(f"v1/devices/me/rpc/request/{int(time.time())}", test_rpc_getlinklocks)
    on_message(client, None, mock_msg4)
    
    log_debug(f"✅ [LOCAL TEST] Đã giả lập cả linkLock, getLinkLocks và unlinkLock test thành công")

# ==================== CALLBACKS MQTT ====================
def on_connect(client, userdata, flags, rc):
    """Callback khi kết nối MQTT thành công"""
    if rc == 0:
        log_debug(f"✅ Kết nối MQTT thành công tới ThingsBoard")
        log_debug(f"📡 Broker: {THINGSBOARD_CONFIG['host']}:{THINGSBOARD_CONFIG['port']}")
        log_debug(f"🔑 Access Token: {THINGSBOARD_CONFIG['access_token']}")
        log_debug(f"🏷️ Device Name: {DEVICE_NAME}")
        
        # QUAN TRỌNG: Subscribe để nhận RPC từ server
        result, mid = client.subscribe(THINGSBOARD_CONFIG["rpc_request_topic"], qos=1)
        log_debug(f"🔔 Đã subscribe RPC topic (mid={mid}): {THINGSBOARD_CONFIG['rpc_request_topic']}")
        
        # Subscribe thêm để debug
        client.subscribe("v1/devices/me/#", qos=1)
        log_debug(f"🔔 Đã subscribe all topics: v1/devices/me/#")
        
        # Gửi telemetry ban đầu để báo hiệu kết nối
        time.sleep(1)
        initial_telemetry = {
            "connectionStatus": "connected",
            "firstConnect": True,
            "deviceName": DEVICE_NAME,
            "timestamp": int(time.time() * 1000),
            "active": True
        }
        publish_telemetry(initial_telemetry)
        
        # Gửi attributes ban đầu
        initial_attributes = {
            "active": True,
            "deviceType": "power_saver_gateway",
            "firmwareVersion": "1.0.0",
            "location": "Vietnam",
            "powerlock_state": power_saver_lock_state,
            "linkedLocksCount": 0,
            "maxLocksSupported": 50
        }
        publish_attributes(initial_attributes)
        
        log_debug(f"📤 Đã gửi initial telemetry và attributes")
        
    else:
        error_msg = mqtt.error_string(rc)
        log_debug(f"❌ Kết nối thất bại (rc={rc}): {error_msg}", "ERROR")

def on_disconnect(client, userdata, rc):
    """Callback khi mất kết nối MQTT"""
    if rc == 0:
        log_debug(f"🔌 Ngắt kết nối MQTT bình thường")
    else:
        log_debug(f"🔌 Mất kết nối MQTT bất thường (rc={rc})", "WARNING")
        log_debug(f"🔄 Tự động kết nối lại sau 5 giây...")
        time.sleep(5)
        try:
            client.reconnect()
        except Exception as e:
            log_debug(f"❌ Lỗi khi reconnect: {e}", "ERROR")

def on_message(client, userdata, msg):
    """Callback khi nhận message từ MQTT broker"""
    try:
        log_debug(f"\n{'='*80}")
        log_debug(f"📨 NHẬN MESSAGE TỪ TOPIC: {msg.topic}")
        
        # Parse payload
        payload_str = msg.payload.decode('utf-8', errors='ignore')
        payload = json.loads(payload_str)
        
        log_debug(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
        
        # XỬ LÝ RPC REQUEST TỪ SERVER
        if "rpc/request" in msg.topic:
            # Lấy request_id từ topic: v1/devices/me/rpc/request/123
            request_id = msg.topic.split("/")[-1]
            log_debug(f"🎯 RPC Request ID: {request_id}")
            
            method = payload.get("method")
            params = payload.get("params", {})
            
            log_debug(f"🎯 RPC Method: {method}")
            log_debug(f"🎯 RPC Params: {params}")
            
            response = None
            
            # Xử lý các method RPC
            if method == "setPowerSaverlock_state":
                response = set_power_saver_lock_state(params)
            elif method == "getPowerSaverlock_state":
                response = get_power_saver_lock_state()
            elif method == "setPowerSaverConfig":
                response = set_power_saver_config(params)
            elif method == "getPowerSaverConfig":
                response = get_power_saver_config()
            elif method == "linkLock":
                response = handle_link_lock(params)
            elif method == "unlinkLock":
                response = handle_unlink_lock(params)
            elif method == "getLinkLocks":  # 🔥 THÊM XỬ LÝ GET LINK LOCKS
                response = handle_get_link_locks(params)
            elif method == "getLinkedLocks":  # Giữ lại cho tương thích
                response = get_linked_locks()
            else:
                log_debug(f"❌ Method không được hỗ trợ: {method}", "WARNING")
                response = {"code": 99, "error": f"Method '{method}' not supported"}
            
            # GỬI RESPONSE VỀ SERVER
            if response:
                send_rpc_response(request_id, response)
                log_debug(f"📤 Đã gửi RPC response cho request_id={request_id}")
        
        log_debug(f"{'='*80}")
        
    except json.JSONDecodeError as e:
        log_debug(f"❌ Lỗi decode JSON: {e}", "ERROR")
        log_debug(f"❌ Raw payload: {msg.payload.decode('utf-8', errors='ignore')[:200]}", "ERROR")
    except Exception as e:
        log_debug(f"❌ Lỗi xử lý message: {e}", "ERROR")
        import traceback
        traceback.print_exc()

# ==================== KẾT NỐI MQTT ====================
def connect_to_thingsboard():
    """Kết nối đến ThingsBoard MQTT broker"""
    global client
    
    client = mqtt.Client(client_id=f"gateway_{int(time.time())}")
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    # Đăng nhập với access token
    client.username_pw_set(THINGSBOARD_CONFIG["access_token"])
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    log_debug(f"🚀 Đang kết nối tới ThingsBoard...")
    log_debug(f"📍 Host: {THINGSBOARD_CONFIG['host']}:{THINGSBOARD_CONFIG['port']}")
    log_debug(f"🔑 Access Token: {THINGSBOARD_CONFIG['access_token'][:10]}...")
    
    try:
        # Kết nối với keepalive 60 giây
        client.connect(
            THINGSBOARD_CONFIG["host"], 
            THINGSBOARD_CONFIG["port"], 
            keepalive=60
        )
        
        # Bắt đầu loop để xử lý MQTT messages
        client.loop_start()
        
        log_debug(f"🔄 Đã bắt đầu MQTT loop")
        return True
        
    except Exception as e:
        log_debug(f"❌ Lỗi kết nối MQTT: {e}", "ERROR")
        return False

# ==================== MAIN ====================
if __name__ == "__main__":
    # Kiểm tra network trước
    log_debug("🔍 Kiểm tra kết nối mạng...")
    if not check_network_connection():
        log_debug("⚠️ Có thể có vấn đề với kết nối mạng", "WARNING")
    
    # Kết nối ThingsBoard
    if not connect_to_thingsboard():
        log_debug("❌ Không thể kết nối ThingsBoard. Dừng chương trình.", "ERROR")
        exit(1)
    
    # Chờ kết nối ổn định
    time.sleep(3)
    
    # Kiểm tra trạng thái kết nối
    check_connection_status()
    
    # Biến thời gian
    last_telemetry_time = 0
    last_active_status_time = 0
    last_status_check = 0
    
    try:
        log_debug(f"🟢 Gateway Client Simulator đang chạy")
        log_debug(f"📡 Device: {DEVICE_NAME}")
        log_debug(f"🔗 Linked Locks: {len(linked_locks)}")
        
        # 🔥 OPTIONAL: Local test sau 10 giây
        log_debug(f"⏰ Sẽ chạy local test sau 10 giây...")
        time.sleep(10)
        simulate_incoming_rpc()
        
        # Vòng lặp chính
        while True:
            current_time = time.time()
            
            # Kiểm tra connection mỗi 30 giây
            if current_time - last_status_check > 30:
                check_connection_status()
                last_status_check = current_time
            
            # Gửi telemetry mỗi 15 giây
            if current_time - last_telemetry_time > 15:
                log_debug(f"\n⚡ Gửi periodic telemetry...")
                simulate_gateway_telemetry()
                last_telemetry_time = current_time
            
            # Gửi active status mỗi 60 giây
            if current_time - last_active_status_time > 60:
                log_debug(f"\n🔥 Gửi active status...")
                send_active_status()
                last_active_status_time = current_time
            
            # Sleep 1 giây
            time.sleep(1)
            
    except KeyboardInterrupt:
        log_debug(f"\n🛑 Dừng Gateway Client Simulator...")
        
        # Log danh sách lock đã link
        if linked_locks:
            log_debug(f"🔗 Danh sách lock đã link:")
            for lock_id, lock_info in linked_locks.items():
                status = lock_info.get('connectionStatus', 'unknown')
                rssi = lock_info.get('lastRSSI', 'N/A')
                log_debug(f"  • {lock_info['tbLockName']} ({lock_id}) - {lock_info['lockMac']} - Status: {status}, RSSI: {rssi}")
        
        # Gửi disconnect status
        try:
            disconnect_telemetry = {
                "connectionStatus": "disconnected",
                "lastSeen": int(time.time() * 1000),
                "active": False
            }
            publish_telemetry(disconnect_telemetry)
            
            disconnect_attributes = {"active": False}
            publish_attributes(disconnect_attributes)
            
            time.sleep(1)
        except:
            pass
        
        # Dừng MQTT client
        if client:
            client.loop_stop()
            client.disconnect()
        
        log_debug(f"👋 Đã dừng chương trình")