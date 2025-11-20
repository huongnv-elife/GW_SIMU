import paho.mqtt.client as mqtt
import json
import time

# ==================== CẤU HÌNH ====================
DEVICE_NAME = "GW_101"

BROKERS = {
    "thingsboard": {
        "host": "192.168.44.135",
        "port": 1883,
        "access_token": "n7BmJhDNjvygUSQydw7f",
        "rpc_request_topic": "v1/devices/me/rpc/request/+",
        "telemetry_topic": "v1/devices/me/telemetry",
        "attributes_topic": "v1/devices/me/attributes",
        "response_template": "v1/devices/me/rpc/response/{}"
    },
    "nanomq": {
        "host": "192.168.1.254",  # IP của PRC_101
        "port": 1883,
        "username": "guest",
        "password": "guest",
        # 🔹 Đảm bảo không trùng topic nếu có nhiều GW cùng kết nối NanoMQ
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

    client.publish(topic, json.dumps(payload))
    print(f"[{DEVICE_NAME}] 📤 Publish → {topic} | Payload: {payload}")


# ==================== XỬ LÝ RPC ====================
def set_power_saver_state(state):
    global power_saver_state

    if state not in ["on", "off"]:
        print(f"[{DEVICE_NAME}] ❌ Trạng thái không hợp lệ: {state}")
        return {"code": 1}

    print(f"[{DEVICE_NAME}] ⚙️ Đang chuyển Power Saver → {state.upper()}")
    time.sleep(0.5)
    power_saver_state = state
    print(f"[{DEVICE_NAME}] ✅ Power Saver hiện đang {state.upper()}")

    telemetry = {"powerState": state}
    publish_message("telemetry", telemetry)

    attributes = {"powerState": state}
    publish_message("attributes", attributes)

    print(f"[{DEVICE_NAME}] 📡 Đã gửi Telemetry + Attribute: powerState = {state}")
    return {"code": 0}


def get_power_saver_state():
    global power_saver_state
    if power_saver_state not in ["on", "off"]:
        print(f"[{DEVICE_NAME}] ⚠️ State không hợp lệ: {power_saver_state}")
        return {"code": 1}
    print(f"[{DEVICE_NAME}] 🔍 Trả về trạng thái Power Saver: {power_saver_state}")
    return {"code": 0, "result": power_saver_state}


def set_power_saver_config(params):
    global power_saver_config

    if not isinstance(params, dict):
        return {"code": 1}

    # relayOffTimeout
    if "relayOffTimeout" in params:
        try:
            power_saver_config["relayOffTimeout"] = int(params["relayOffTimeout"])
        except Exception:
            print(f"[{DEVICE_NAME}] ⚠️ relayOffTimeout không hợp lệ")
            return {"code": 1}

    # powerMode
    if "powerMode" in params:
        if params["powerMode"] in ["public", "private"]:
            power_saver_config["powerMode"] = params["powerMode"]
        else:
            print(f"[{DEVICE_NAME}] ⚠️ powerMode không hợp lệ")
            return {"code": 1}

    print(f"[{DEVICE_NAME}] ✅ Đã cập nhật cấu hình: {power_saver_config}")
    publish_message("attributes", power_saver_config)
    return {"code": 0}


def get_power_saver_config():
    global power_saver_config
    print(f"[{DEVICE_NAME}] 🔍 Trả về cấu hình Power Saver: {power_saver_config}")
    return {"code": 0, "result": power_saver_config}


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
        config = BROKERS[ACTIVE_BROKER]

        if "rpc/request" in topic:
            request_id = topic.split("/")[-1]
            method = payload.get("method")
            params = payload.get("params", {})

            print("\n================ RPC NHẬN ĐƯỢC ================")
            print(f"[{DEVICE_NAME}] 📨 method = {method}")
            print(f"[{DEVICE_NAME}] 📦 params = {params}")
            print("================================================")

            response = {"code": 1}  # mặc định lỗi

            # Xử lý RPC tương ứng
            if method == "setPowerSaverState":
                response = set_power_saver_state(params.get("state"))
            elif method == "getPowerSaverState":
                response = get_power_saver_state()
            elif method == "setPowerSaverConfig":
                response = set_power_saver_config(params)
            elif method == "getPowerSaverConfig":
                response = get_power_saver_config()

            # Gửi phản hồi
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
        print(f"[{DEVICE_NAME}] 🟢 Simulator đang chạy (broker: {ACTIVE_BROKER})")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{DEVICE_NAME}] 🛑 Dừng simulator...")
        client.loop_stop()
        client.disconnect()
