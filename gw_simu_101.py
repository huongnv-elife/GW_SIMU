import paho.mqtt.client as mqtt
import json
import time
import uuid

# ==================== CẤU HÌNH ====================
DEVICE_NAME = "GWPS_105"

BROKERS = {
    "thingsboard": {
        "host": "192.168.44.134",
        "port": 1883,
        "access_token": "5xaFxOYnnmaLuQeSQfwA",
        "rpc_request_topic": "v1/devices/me/rpc/request/+",
        "telemetry_topic": "v1/devices/me/telemetry",
        "attributes_topic": "v1/devices/me/attributes",
        "response_template": "v1/devices/me/rpc/response/{}",
        # Gateway API topics
        "gateway_connect_topic": "v1/gateway/connect",
        "gateway_disconnect_topic": "v1/gateway/disconnect",
        "gateway_telemetry_topic": "v1/gateway/telemetry",
        "gateway_attributes_topic": "v1/gateway/attributes",
        "gateway_rpc_topic": "v1/gateway/rpc"
    },
    "nanomq": {
        "host": "192.168.1.254",
        "port": 1883,
        "username": "guest",
        "password": "guest",
        "rpc_request_topic": f"{DEVICE_NAME}/rpc/request/+",
        "telemetry_topic": f"{DEVICE_NAME}/telemetry",
        "attributes_topic": f"{DEVICE_NAME}/attributes",
        "response_template": f"{DEVICE_NAME}/rpc/response/{{}}"
    }
}

# 🔹 Chọn broker muốn test ("thingsboard" hoặc "nanomq")
ACTIVE_BROKER = "thingsboard"

# ==================== TRẠNG THÁI & CẤU HÌNH ====================
power_saver_state = "off"
power_saver_config = {
    "relayOffTimeout": 30,
    "powerMode": "public"
}

# 🔹 THÊM DEVICE LOCK ẢO
virtual_lock_devices = {
    "LOCK_105": {
        "name": "LOCK_105",
        "state": "locked",
        "battery": 85,
        "rssi": -65,
        "location": "Main Entrance"
    }
}

client = None

# ==================== HÀM MQTT GỬI DỮ LIỆU ====================
def publish_message(msg_type, payload):
    config = BROKERS[ACTIVE_BROKER]
    if msg_type == "telemetry":
        topic = config["telemetry_topic"]
    elif msg_type == "attributes":
        topic = config["attributes_topic"]
    elif msg_type.startswith("response:"):
        req_id = msg_type.split(":")[1]
        topic = config["response_template"].format(req_id)
    else:
        print(f"[{DEVICE_NAME}] ⚠️ Message type không hợp lệ: {msg_type}")
        return

    result = client.publish(topic, json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[{DEVICE_NAME}] ✅ Publish → {topic} | Payload: {payload}")
    else:
        print(f"[{DEVICE_NAME}] ❌ Lỗi publish: {result.rc}")

# ==================== GATEWAY API FUNCTIONS ====================
def gateway_connect_device(device_name):
    """Thông báo device kết nối qua Gateway"""
    if ACTIVE_BROKER != "thingsboard":
        return
        
    config = BROKERS[ACTIVE_BROKER]
    payload = {"device": device_name}
    result = client.publish(config["gateway_connect_topic"], json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[GATEWAY] ✅ Device connected: {device_name}")
    else:
        print(f"[GATEWAY] ❌ Lỗi connect device: {result.rc}")

def gateway_disconnect_device(device_name):
    """Thông báo device ngắt kết nối qua Gateway"""
    if ACTIVE_BROKER != "thingsboard":
        return
        
    config = BROKERS[ACTIVE_BROKER]
    payload = {"device": device_name}
    result = client.publish(config["gateway_disconnect_topic"], json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[GATEWAY] ✅ Device disconnected: {device_name}")
    else:
        print(f"[GATEWAY] ❌ Lỗi disconnect device: {result.rc}")

def gateway_publish_telemetry(device_name, telemetry_data):
    """Gửi telemetry của device qua Gateway - ĐÚNG FORMAT"""
    if ACTIVE_BROKER != "thingsboard":
        return
        
    config = BROKERS[ACTIVE_BROKER]
    
    payload = {
        device_name: [
            {
                "ts": telemetry_data.get("ts", int(time.time() * 1000)),
                "values": {k: v for k, v in telemetry_data.items() if k != "ts"}
            }
        ]
    }
    
    result = client.publish(config["gateway_telemetry_topic"], json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[GATEWAY] ✅ Telemetry từ {device_name}: {telemetry_data}")
    else:
        print(f"[GATEWAY] ❌ Lỗi gửi telemetry: {result.rc}")

def gateway_publish_attributes(device_name, attributes_data):
    """Gửi attributes của device qua Gateway"""
    if ACTIVE_BROKER != "thingsboard":
        return
        
    config = BROKERS[ACTIVE_BROKER]
    
    payload = {
        device_name: attributes_data
    }
    
    result = client.publish(config["gateway_attributes_topic"], json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[GATEWAY] ✅ Attributes từ {device_name}: {attributes_data}")
    else:
        print(f"[GATEWAY] ❌ Lỗi gửi attributes: {result.rc}")

def gateway_send_rpc_response(device_name, req_id, response_data):
    """Gửi RPC response từ device qua Gateway - ĐÚNG FORMAT"""
    if ACTIVE_BROKER != "thingsboard":
        return
        
    config = BROKERS[ACTIVE_BROKER]
    payload = {
        "device": device_name,
        "id": req_id,
        "data": response_data
    }
    result = client.publish(config["gateway_rpc_topic"], json.dumps(payload))
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[GATEWAY] ✅ RPC response từ {device_name}: {response_data}")
    else:
        print(f"[GATEWAY] ❌ Lỗi gửi RPC response: {result.rc}")

# ==================== VIRTUAL LOCK FUNCTIONS ====================
def lock_device_connect_all():
    """Kết nối tất cả lock devices"""
    for device_id in virtual_lock_devices:
        print(f"[GATEWAY] 🚀 Đang kết nối device: {device_id}")
        gateway_connect_device(device_id)
        time.sleep(1)
        
        # Gửi attributes ban đầu
        attributes = {
            "name": virtual_lock_devices[device_id]["name"],
            "location": virtual_lock_devices[device_id]["location"],
            "model": "SmartLock V2",
            "firmware": "1.0.0",
            "type": "smart_lock",
            "connected": True
        }
        gateway_publish_attributes(device_id, attributes)
        time.sleep(1)
        
        # Gửi telemetry ban đầu
        telemetry_data = {
            "battery": virtual_lock_devices[device_id]["battery"],
            "rssi": virtual_lock_devices[device_id]["rssi"],
            "state": virtual_lock_devices[device_id]["state"],
            "ts": int(time.time() * 1000)
        }
        gateway_publish_telemetry(device_id, telemetry_data)
        time.sleep(1)

def handle_lock_rpc(device_id, method, params, req_id):
    """Xử lý RPC cho lock device"""
    if device_id not in virtual_lock_devices:
        print(f"[RPC] ❌ Device không tồn tại: {device_id}")
        return {"success": False, "error": "Device not found"}
    
    lock = virtual_lock_devices[device_id]
    
    print(f"[RPC] 🔄 Xử lý RPC: device={device_id}, method={method}, params={params}")
    
    if method == "setLockState":
        state = params
        print(f"[RPC] 🎯 setLockState: {state}")
        
        if state in ["locked", "unlocked"]:
            old_state = lock["state"]
            lock["state"] = state
            
            # Gửi telemetry cập nhật state
            telemetry_data = {
                "state": state,
                "lastAction": "rpc_control",
                "battery": lock["battery"],
                "previousState": old_state,
                "ts": int(time.time() * 1000)
            }
            gateway_publish_telemetry(device_id, telemetry_data)
            
            print(f"[RPC] ✅ Lock {device_id} changed: {old_state} → {state}")
            return {"success": True, "status": f"Lock {state} successfully"}
        else:
            print(f"[RPC] ❌ State không hợp lệ: {state}")
            return {"success": False, "error": "Invalid state"}
    
    elif method == "getLockState":
        print(f"[RPC] 📊 getLockState: {lock['state']}")
        return {
            "success": True, 
            "state": lock["state"], 
            "battery": lock["battery"],
            "rssi": lock["rssi"]
        }
    
    elif method == "getLockInfo":
        print(f"[RPC] 📋 getLockInfo")
        return {
            "success": True, 
            "name": lock["name"],
            "state": lock["state"],
            "battery": lock["battery"],
            "rssi": lock["rssi"],
            "location": lock["location"]
        }
    
    else:
        print(f"[RPC] ❌ Method không được hỗ trợ: {method}")
        return {"success": False, "error": "Method not supported"}

def simulate_lock_telemetry():
    """Mô phỏng thay đổi telemetry của lock devices"""
    for device_id, lock in virtual_lock_devices.items():
        if lock["battery"] > 10:
            lock["battery"] -= 0.1
        
        lock["rssi"] = -60 - (time.time() % 20)
        
        telemetry_data = {
            "battery": round(lock["battery"], 1),
            "rssi": int(lock["rssi"]),
            "state": lock["state"],
            "signalStrength": "good" if lock["rssi"] > -70 else "fair",
            "ts": int(time.time() * 1000)
        }
        gateway_publish_telemetry(device_id, telemetry_data)
        print(f"[LOCK {device_id}] 📊 Sent periodic telemetry")

# ==================== XỬ LÝ RPC GATEWAY ====================
def set_power_saver_state(state):
    global power_saver_state

    if state not in ["on", "off"]:
        print(f"[{DEVICE_NAME}] ❌ Trạng thái không hợp lệ: {state}")
        return {"success": False}

    print(f"[{DEVICE_NAME}] ⚙️ Đang chuyển Power Saver → {state.upper()}")
    power_saver_state = state
    print(f"[{DEVICE_NAME}] ✅ Power Saver hiện đang {state.upper()}")

    telemetry = {"powerState": state}
    publish_message("telemetry", telemetry)

    attributes = {"powerState": state}
    publish_message("attributes", attributes)

    print(f"[{DEVICE_NAME}] 📡 Đã gửi Telemetry + Attribute: powerState = {state}")
    return {"success": True}

def get_power_saver_state():
    global power_saver_state
    if power_saver_state not in ["on", "off"]:
        print(f"[{DEVICE_NAME}] ⚠️ State không hợp lệ: {power_saver_state}")
        return {"success": False}
    print(f"[{DEVICE_NAME}] 🔍 Trả về trạng thái Power Saver: {power_saver_state}")
    return {"success": True, "result": power_saver_state}

def set_power_saver_config(params):
    global power_saver_config

    if not isinstance(params, dict):
        return {"success": False}

    if "relayOffTimeout" in params:
        try:
            power_saver_config["relayOffTimeout"] = int(params["relayOffTimeout"])
        except Exception:
            print(f"[{DEVICE_NAME}] ⚠️ relayOffTimeout không hợp lệ")
            return {"success": False}

    if "powerMode" in params:
        if params["powerMode"] in ["public", "private"]:
            power_saver_config["powerMode"] = params["powerMode"]
        else:
            print(f"[{DEVICE_NAME}] ⚠️ powerMode không hợp lệ")
            return {"success": False}

    print(f"[{DEVICE_NAME}] ✅ Đã cập nhật cấu hình: {power_saver_config}")
    publish_message("attributes", power_saver_config)
    return {"success": True}

def get_power_saver_config():
    global power_saver_config
    print(f"[{DEVICE_NAME}] 🔍 Trả về cấu hình Power Saver: {power_saver_config}")
    return {"success": True, "result": power_saver_config}

# ==================== DEBUG & TEST FUNCTIONS ====================
def print_rpc_test_instructions():
    """In hướng dẫn test RPC từ Postman"""
    print("\n" + "="*80)
    print("🔧 HƯỚNG DẪN TEST RPC TỪ POSTMAN - ĐÚNG CHUẨN GATEWAY API")
    print("="*80)
    
    print("\n📝 LƯU Ý QUAN TRỌNG:")
    print("   - Gửi RPC TRỰC TIẾP đến Lock Device (LOCK_105)")
    print("   - ThingsBoard sẽ tự động chuyển RPC đến Gateway theo format Gateway RPC")
    
    print("\n1. 🔐 Lấy JWT Token từ ThingsBoard:")
    print("   POST http://192.168.44.134:8080/api/auth/login")
    print("   Body: {\"username\": \"tenant@thingsboard.org\", \"password\": \"tenant\"}")
    
    print("\n2. 🔍 Lấy DEVICE_ID của Lock Device (LOCK_105):")
    print("   GET http://192.168.44.134:8080/api/tenant/devices?deviceName=LOCK_105")
    print("   Header: X-Authorization: Bearer {JWT_TOKEN}")
    
    print("\n3. 🚀 Gửi RPC đến Lock Device (LOCK_105):")
    print("   POST http://192.168.44.134:8080/api/plugins/rpc/twoway/{LOCK_105_DEVICE_ID}")
    print("   Headers: Content-Type: application/json, X-Authorization: Bearer {JWT_TOKEN}")
    
    print("\n4. 💡 Các RPC methods có thể test:")
    print("   📍 setLockState:")
    print("      {\"method\": \"setLockState\", \"params\": \"unlocked\"}")
    print("   📍 getLockState:")
    print("      {\"method\": \"getLockState\", \"params\": {}}")
    print("   📍 getLockInfo:")
    print("      {\"method\": \"getLockInfo\", \"params\": {}}")
    
    print("\n5. 🔄 Flow hoạt động (QUAN TRỌNG):")
    print("   Postman → ThingsBoard API → Lock Device RPC")
    print("   ThingsBoard → Gateway RPC topic (v1/gateway/rpc) → Gateway")
    print("   Gateway → Xử lý RPC → Gửi response → ThingsBoard → Postman")
    print("="*80 + "\n")

# ==================== CALLBACKS MQTT ====================
def on_connect(client, userdata, flags, rc):
    config = BROKERS[ACTIVE_BROKER]
    if rc == 0:
        print(f"[{DEVICE_NAME}] ✅ Kết nối MQTT thành công tới {ACTIVE_BROKER.upper()}")
        client.subscribe(config["rpc_request_topic"])
        print(f"[{DEVICE_NAME}] 🔔 Đã subscribe RPC topic: {config['rpc_request_topic']}")
        
        if ACTIVE_BROKER == "thingsboard":
            # 🔹 QUAN TRỌNG: Subscribe Gateway RPC topic
            gateway_rpc_topic = f"{config['gateway_rpc_topic']}"
            client.subscribe(gateway_rpc_topic)
            print(f"[GATEWAY] 🔔 Đã subscribe Gateway RPC topic: {gateway_rpc_topic}")
            
            print(f"[GATEWAY] 🚀 Bắt đầu kết nối {len(virtual_lock_devices)} lock devices...")
            time.sleep(3)
            lock_device_connect_all()
            
    else:
        print(f"[{DEVICE_NAME}] ❌ Kết nối thất bại, mã lỗi {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        config = BROKERS[ACTIVE_BROKER]

        print(f"\n📨 Nhận message từ topic: {topic}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")

        # 🔹 XỬ LÝ GATEWAY RPC - THEO ĐÚNG CHUẨN GATEWAY API
        if topic == config['gateway_rpc_topic']:
            print("\n" + "="*60 + " GATEWAY RPC (FROM THINGSBOARD) " + "="*60)
            
            # 🔹 FORMAT CHUẨN: {"device": "Device A", "data": {"id": $request_id, "method": "method", "params": {}}}
            device_id = payload.get("device")
            data = payload.get("data", {})
            req_id = data.get("id")
            method = data.get("method")
            params = data.get("params")
            
            print(f"[GATEWAY] 🔍 Gateway RPC: device={device_id}, method={method}, req_id={req_id}, params={params}")
            
            if device_id and device_id in virtual_lock_devices:
                print(f"[GATEWAY] 🎯 Xử lý RPC cho {device_id}")
                response = handle_lock_rpc(device_id, method, params, req_id)
                gateway_send_rpc_response(device_id, req_id, response)
                print(f"[GATEWAY] ✅ Đã xử lý RPC cho {device_id}")
            else:
                print(f"[GATEWAY] ❌ Device không tồn tại: {device_id}")
                error_response = {"success": False, "error": f"Device not found: {device_id}"}
                if device_id and req_id:
                    gateway_send_rpc_response(device_id, req_id, error_response)
            
            print("="*140 + "\n")
            return

        # 🔹 XỬ LÝ RPC THÔNG THƯỜNG (CHO GATEWAY DEVICE)
        if "rpc/request" in topic:
            request_id = topic.split("/")[-1]
            method = payload.get("method")
            params = payload.get("params", {})

            print("\n" + "="*20 + " GATEWAY DEVICE RPC " + "="*20)
            print(f"[{DEVICE_NAME}] 📨 method = {method}")
            print(f"[{DEVICE_NAME}] 📦 params = {params}")

            response = {"success": False}

            if method == "setPowerSaverState":
                response = set_power_saver_state(params)
            elif method == "getPowerSaverState":
                response = get_power_saver_state()
            elif method == "setPowerSaverConfig":
                response = set_power_saver_config(params)
            elif method == "getPowerSaverConfig":
                response = get_power_saver_config()
            else:
                print(f"[{DEVICE_NAME}] ❌ Method không được hỗ trợ: {method}")
                response = {"success": False, "error": "Method not supported"}

            publish_message(f"response:{request_id}", response)
            print(f"[{DEVICE_NAME}] 🔁 RPC response gửi về request_id={request_id}")
            print(f"[{DEVICE_NAME}] 📤 Payload: {response}")
            print("="*60 + "\n")

    except Exception as e:
        print(f"[{DEVICE_NAME}] ⚠️ Lỗi xử lý message: {e}")
        import traceback
        traceback.print_exc()

# ==================== KẾT NỐI MQTT ====================
def connect_broker():
    global client
    config = BROKERS[ACTIVE_BROKER]

    client = mqtt.Client()
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    if ACTIVE_BROKER == "thingsboard":
        client.username_pw_set(config["access_token"])
    else:
        client.username_pw_set(config["username"], config["password"])

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[{DEVICE_NAME}] 🚀 Đang kết nối tới {ACTIVE_BROKER.upper()} MQTT...")
    print(f"[{DEVICE_NAME}] 📍 Host: {config['host']}:{config['port']}")
    try:
        client.connect(config["host"], config["port"], keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[{DEVICE_NAME}] ❌ Lỗi kết nối: {e}")

# ==================== MAIN ====================
if __name__ == "__main__":
    connect_broker()
    last_telemetry_time = 0
    try:
        print(f"[{DEVICE_NAME}] 🟢 Simulator đang chạy (broker: {ACTIVE_BROKER})")
        print(f"[GATEWAY] 🔐 Virtual locks: {list(virtual_lock_devices.keys())}")
        
        time.sleep(5)
        print_rpc_test_instructions()
        
        while True:
            current_time = time.time()
            if current_time - last_telemetry_time > 30:
                if ACTIVE_BROKER == "thingsboard":
                    print(f"[GATEWAY] 📊 Gửi periodic telemetry...")
                    simulate_lock_telemetry()
                last_telemetry_time = current_time
                
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{DEVICE_NAME}] 🛑 Dừng simulator...")
        for device_id in virtual_lock_devices:
            gateway_disconnect_device(device_id)
        client.loop_stop()
        client.disconnect()