import paho.mqtt.client as mqtt
import json
import time

# ==================== CẤU HÌNH ====================
DEVICE_NAME = "LOCK_101"

BROKERS = {
    "thingsboard": {
        "host": "192.168.44.135", # tbcanopi
        #"host": "192.168.1.62", # tbgiang
        "port": 1883,
        "access_token": "piyvZtE3DOLb6Wd7NEPe", # tbcanopi
        #"access_token": "658D830E657FE2305830B8AC9F8C6FBA", # tbgiang 
        "rpc_request_topic": "v1/devices/me/rpc/request/+",
        "telemetry_topic": "v1/devices/me/telemetry",
        "attributes_topic": "v1/devices/me/attributes",
        "response_template": "v1/devices/me/rpc/response/{}"
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

# ==================== BIẾN GIẢ LẬP TRẠNG THÁI ====================
lock_state = "close"
lock_config = {
    "autoLockTime": 10,
    "soundLevel": 3,
    "alarmSound": "on",
    "tamperAlert": "off"
}
lock_battery = 88
lock_timestamp = int(time.time())

client = None


# ==================== HÀM GỬI MQTT ====================
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

    client.publish(topic, json.dumps(payload))
    print(f"[{DEVICE_NAME}] 📤 Publish → {topic} | Payload: {payload}")


# ==================== RPC HANDLERS ====================
def set_lock_state(params):
    global lock_state
    state = params.get("state")

    if state not in ["open", "close"]:
        print(f"[{DEVICE_NAME}] ❌ Trạng thái không hợp lệ: {state}")
        return {"code": 1}

    print(f"[{DEVICE_NAME}] ⚙️ Đang chuyển khóa sang trạng thái {state.upper()}")
    time.sleep(0.3)
    lock_state = state
    publish_message("telemetry", {"lockState": state})
    publish_message("attributes", {"lockState": state})
    print(f"[{DEVICE_NAME}] ✅ Đã chuyển sang trạng thái {state.upper()}")
    return {"code": 0}


def get_lock_state():
    print(f"[{DEVICE_NAME}] 🔍 Trả về trạng thái khóa: {lock_state}")
    if lock_state not in ["open", "close"]:
        return {"code": 1}
    return {"code": 0, "result": lock_state}


def get_lock_current_time():
    ts = int(time.time())
    print(f"[{DEVICE_NAME}] ⏱️ Thời gian hiện tại: {ts}")
    return {"code": 0, "result": ts}


def set_lock_current_time(params):
    global lock_timestamp
    try:
        ts = int(params.get("deviceTs"))
        lock_timestamp = ts
        print(f"[{DEVICE_NAME}] ⏱️ Đã set thời gian khóa = {ts}")
        return {"code": 0}
    except Exception as e:
        print(f"[{DEVICE_NAME}] ⚠️ Lỗi setLockCurrentTime: {e}")
        return {"code": 1}


def get_lock_config():
    print(f"[{DEVICE_NAME}] 🔧 Cấu hình hiện tại: {lock_config}")
    return {"code": 0, "result": lock_config}


def set_lock_config(params):
    global lock_config
    try:
        # Duyệt từng key được truyền vào và cập nhật nếu hợp lệ
        for key, value in params.items():
            if key == "autoLockTime":
                lock_config["autoLockTime"] = int(value)
            elif key == "soundLevel":
                if 0 <= int(value) <= 5:
                    lock_config["soundLevel"] = int(value)
                else:
                    print(f"[{DEVICE_NAME}] ⚠️ soundLevel không hợp lệ: {value}")
                    return {"code": 1}
            elif key == "alarmSound":
                if value in ["on", "off"]:
                    lock_config["alarmSound"] = value
                else:
                    return {"code": 1}
            elif key == "tamperAlert":
                if value in ["on", "off"]:
                    lock_config["tamperAlert"] = value
                else:
                    return {"code": 1}
            else:
                print(f"[{DEVICE_NAME}] ⚠️ Bỏ qua param không hợp lệ: {key}")

        publish_message("attributes", lock_config)
        print(f"[{DEVICE_NAME}] ✅ Đã cập nhật cấu hình: {lock_config}")
        return {"code": 0}
    except Exception as e:
        print(f"[{DEVICE_NAME}] ⚠️ Lỗi setLockConfig: {e}")
        return {"code": 1}


def get_lock_battery():
    print(f"[{DEVICE_NAME}] 🔋 Dung lượng pin hiện tại: {lock_battery}%")
    return {"code": 0, "result": lock_battery}


# ==================== CALLBACKS MQTT ====================
def on_connect(client, userdata, flags, rc):
    config = BROKERS[ACTIVE_BROKER]
    if rc == 0:
        print(f"[{DEVICE_NAME}] ✅ Kết nối MQTT thành công tới {ACTIVE_BROKER.upper()}")
        client.subscribe(config["rpc_request_topic"])
        print(f"[{DEVICE_NAME}] 🔔 Đã subscribe RPC topic: {config['rpc_request_topic']}")
    else:
        print(f"[{DEVICE_NAME}] ❌ Kết nối thất bại, mã lỗi {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        if "rpc/request" not in topic:
            return

        request_id = topic.split("/")[-1]
        method = payload.get("method")
        params = payload.get("params", {})

        print("\n================ RPC NHẬN ĐƯỢC ================")
        print(f"[{DEVICE_NAME}] 📨 method = {method}")
        print(f"[{DEVICE_NAME}] 📦 params = {params}")
        print("================================================")

        response = {"code": 1}

        # Gọi hàm xử lý tương ứng
        if method == "setLockState":
            response = set_lock_state(params)
        elif method == "getLockState":
            response = get_lock_state()
        elif method == "getLockCurrentTime":
            response = get_lock_current_time()
        elif method == "setLockCurrentTime":
            response = set_lock_current_time(params)
        elif method == "getLockConfig":
            response = get_lock_config()
        elif method == "setLockConfig":
            response = set_lock_config(params)
        elif method == "getLockBattery":
            response = get_lock_battery()

        publish_message(f"response:{request_id}", response)
        print(f"[{DEVICE_NAME}] 🔁 RPC response gửi về request_id={request_id}")
        print(f"[{DEVICE_NAME}] 📤 Payload: {response}")
        print("================================================\n")

    except Exception as e:
        print(f"[{DEVICE_NAME}] ⚠️ Lỗi xử lý message: {e}")


# ==================== KẾT NỐI MQTT ====================
def connect_broker():
    global client
    config = BROKERS[ACTIVE_BROKER]

    client = mqtt.Client()
    if ACTIVE_BROKER == "thingsboard":
        client.username_pw_set(config["access_token"])
    else:
        client.username_pw_set(config["username"], config["password"])

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[{DEVICE_NAME}] 🚀 Đang kết nối tới {ACTIVE_BROKER.upper()} MQTT...")
    client.connect(config["host"], config["port"], keepalive=60)
    client.loop_start()


# ==================== MAIN ====================
if __name__ == "__main__":
    connect_broker()
    try:
        print(f"[{DEVICE_NAME}] 🟢 Lock simulator đang chạy (broker: {ACTIVE_BROKER})")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{DEVICE_NAME}] 🛑 Dừng simulator...")
        client.loop_stop()
        client.disconnect()
