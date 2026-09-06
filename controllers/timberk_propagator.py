import argparse
import time
import os
import sys
import paho.mqtt.client as mqtt
import json  # Для работы с JSON сообщениями
import random
from datetime import datetime

# Определяем путь к файлу блокировки
LOCKFILE = os.getenv("TIMBERK_PROPAGATOR_LOCKFILE", "timberk_propagator.lock")
# Файл для хранения последнего отправленного кода
LAST_IR_CODE_FILE = os.getenv("TIMBERK_PROPAGATOR_LAST_IR_CODE_FILE", "timberk_propagator-last-ir-code.txt")
# Логи
LOG_FILE = os.getenv("TIMBERK_PROPAGATOR_LOG_FILE", "timberk_propagator.log")

# Определяем доступные режимы увлажнителя
MODES = ["Auto", "Low", "Medium", "High"]

# Определяем состояния пар и ионизации
STEAM_ION_STATES = [
    {"steam": "off", "ion": "off"},  # Состояние 1: выкл. пар, выкл. ионизация
    {"steam": "on", "ion": "off"},   # Состояние 2: вкл. пар, выкл. ионизация
    {"steam": "on", "ion": "on"},    # Состояние 3: вкл. пар, вкл. ионизация
    {"steam": "off", "ion": "on"},   # Состояние 4: выкл. пар, вкл. ионизация
]

# Глобальные переменные для хранения текущих состояний
current_power = None
current_mode = "Auto"
current_steam = None
current_ion = None
current_physical_power = None  # Состояние физического питания увлажнителя
current_light = None  # Состояние света
current_night_mode = None  # Состояние ночного режима

# Глобальная переменная для таймаута между сигналами
TIMEOUT = 15  # Значение по умолчанию, можно изменить через аргумент командной строки

# Настройки MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_KEEPALIVE = 30
MQTT_QOS = 2  # QoS уровень доставки сообщений

# MQTT топики
MQTT_TOPIC_POWER = os.getenv("MQTT_TOPIC_POWER", "portfolio/timberk_propagator/power")
MQTT_TOPIC_MODE = os.getenv("MQTT_TOPIC_MODE", "portfolio/timberk_propagator/mode")
MQTT_TOPIC_ION = os.getenv("MQTT_TOPIC_ION", "portfolio/timberk_propagator/ion")
MQTT_TOPIC_STEAM = os.getenv("MQTT_TOPIC_STEAM", "portfolio/timberk_propagator/steam")
MQTT_TOPIC_LIGHT = os.getenv("MQTT_TOPIC_LIGHT", "portfolio/timberk_propagator/light")
MQTT_TOPIC_NIGHT_MODE = os.getenv("MQTT_TOPIC_NIGHT_MODE", "portfolio/timberk_propagator/night_mode")
MQTT_TOPIC_IR_SEND = os.getenv("MQTT_TOPIC_IR_SEND", "portfolio/timberk_propagator/ir_send")
MQTT_TOPIC_LOG = os.getenv("MQTT_TOPIC_LOG", "portfolio/timberk_propagator/log")
MQTT_TOPIC_LAST_IR_CODE = os.getenv("MQTT_TOPIC_LAST_IR_CODE", "portfolio/timberk_propagator/last_ir_code")
MQTT_TOPIC_PHYSICAL_POWER = os.getenv("MQTT_TOPIC_PHYSICAL_POWER", "portfolio/timberk_propagator/physical_power")

# Списки сигналов для различных состояний
IR_SIGNALS_MODE = [
    "CW8joBE5ArQGOQLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB6+bbyPPCDkC",
    "CW0jgBE3ArgGNwLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7abbSPtCDcC",
    "CWUjohE5ArQGOQLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7ubZSPKCDkC",
    "CVsjihE0Ar8GNALgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB8KbWyP2CDQC",
    "CWgjnRE5ArYGOQLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB76baCPECDkC",
    "CW0jgBE3ArgGNwLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7abbSPtCDcC",
    "CWUjohE5ArQGOQLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7ubZSPKCDkC",
    "CWkjoxE7Aq0GOwLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7ibaSPUCDsC",
    "CVsjihE0Ar8GNALgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB8KbWyP2CDQC",
    "CWgjphE7ArAGOwLgEwFAH+ADA0AB4AcPQAFAE+ALAUAXQANAAUAH4AcDB7GbaCO4CDsC"
]
IR_SIGNALS_ION = [
    "CWYjnhE5ArMGOQLgEwFAH+ADA0AB4A8P4AsBQCvAAUAL4AcDB7SbZiPRCDkC",
    "CW0jgBE3ArgGNwLgEwFAH+ADA0AB4A8P4AsBQCvAAUAL4AcDB66bXyPPCDkC"
]
IR_SIGNALS_POWER = [
    "CXkjhxE5ArUGOQLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwe0m3kjtgg5Ag==",
    "CWkjpxE4ArUGOALgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwe0m2kj3Qg4Ag==",
    "CUQjpRE1ArsGNQLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwfHm0QjAAk1Ag==",
    "CW4joBE7AqsGOwLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAweym24j6Ag7Ag==",
    "CWUjrRE6Aq8GOgLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwewm2Ujwgg6Ag==",
    "CWIjohE3ArsGNwLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwezm2Ijygg3Ag==",
    "CWUjrBE5ArIGOQLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwesm2Uj2gg5Ag==",
    "CVAjvBE1ArwGNQLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwfFm1Aj8Ag1Ag==",
    "CWYjoRE5ArYGOQLgEwFAH+ADA0AB4AMPQAvgFwFAI+APAwe0m2YjsAg5Ag=="
]
IR_SIGNALS_LIGHT = [
    "CWMjjhE7Aq0GOwLgEwFAH+ADA0AB4AsPQAFAF+AHAcAT4AMHQAvAAweem2Mj0Qg7Ag==",
    "CWYjnRE4ArUGOALgEwFAH+ADA0AB4AsPQAFAF+AHAcAT4AMHQAvgAAMGm2Yjzwg4Ag=="
]
IR_SIGNALS_NIGHT_MODE = [
    "CWQjrhE8AqcGPALgEwFAH+ADA0AB4AcPQAHAE+AHAeAHF8APwAcHqJtkI9AIPAI=",
    "CXAjsxE+AqAGPgLgEwFAH+ADA0AB4AcPQAHAE+AHAeAHF8APwAcHo5twI9EIPgI="
]

def log_message(client, message):
    """Функция для отправки логов в MQTT и запись в файл в формате JSON с датой и временем."""
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "message": message
    }

    # Публикация сообщения в MQTT
    if client is not None:
        client.publish(MQTT_TOPIC_LOG, message, qos=MQTT_QOS)
    
    # Запись логов в файл
    try:
        with open(LOG_FILE, 'a') as logfile:  # Открытие файла в режиме добавления
            logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")  # Записываем лог в JSON формате
    except Exception as e:
        print(f"Ошибка записи в файл лога: {e}")
    
    # Вывод в консоль
    print(json.dumps(log_entry, ensure_ascii=False))

def check_lock():
    """Функция для проверки и ожидания освобождения блокировки. Удаляет файл блокировки после 6 обнаружений."""
    lock_attempts = 0  # Счётчик обнаружений блокировки

    while os.path.exists(LOCKFILE):
        lock_attempts += 1
        log_message(None, f"Обнаружена блокировка. Ожидание завершения работы другого экземпляра... Попытка {lock_attempts}/6")
        time.sleep(15)  # Ожидание перед повторной проверкой
        
        if lock_attempts >= 6:  # Если 6 попыток завершились неудачей
            log_message(None, f"Удаление файла блокировки после {lock_attempts} попыток.")
            remove_lock()  # Удаляем файл блокировки
            break  # Прекращаем ожидание

    # Если блокировки нет, создаем её
    try:
        open(LOCKFILE, 'w').close()
    except Exception as e:
        log_message(None, f"Ошибка при создании блокировки: {str(e)}")
        remove_lock()
        sys.exit()

def remove_lock(client=None):
    """Функция для удаления блокировки."""
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)
    log_message(client, "Блокировка снята. Продолжаем выполнение.")

def on_connect(client, userdata, flags, rc):
    """Функция при подключении к MQTT."""
    log_message(client, "Подключено к MQTT брокеру")
    client.subscribe([(MQTT_TOPIC_POWER, MQTT_QOS), 
                      (MQTT_TOPIC_MODE, MQTT_QOS), 
                      (MQTT_TOPIC_ION, MQTT_QOS), 
                      (MQTT_TOPIC_STEAM, MQTT_QOS),
                      (MQTT_TOPIC_LIGHT, MQTT_QOS),
                      (MQTT_TOPIC_NIGHT_MODE, MQTT_QOS),
                      (MQTT_TOPIC_PHYSICAL_POWER, MQTT_QOS)])
    log_message(client, "Подписка на топики выполнена")

def on_message(client, userdata, msg):
    """Функция для обработки входящих сообщений MQTT."""
    global current_power, current_mode, current_steam, current_ion, current_light, current_night_mode, current_physical_power

    if msg.topic == MQTT_TOPIC_POWER:
        current_power = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние питания: {'on' if current_power else 'off'}")
    elif msg.topic == MQTT_TOPIC_MODE:
        current_mode = msg.payload.decode()
        log_message(client, f"Получено сообщение: Текущий режим: {current_mode}")
    elif msg.topic == MQTT_TOPIC_STEAM:
        current_steam = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние пара: {'on' if current_steam else 'off'}")
    elif msg.topic == MQTT_TOPIC_ION:
        current_ion = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние ионизации: {'on' if current_ion else 'off'}")
    elif msg.topic == MQTT_TOPIC_LIGHT:
        current_light = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние света: {'on' if current_light else 'off'}")
    elif msg.topic == MQTT_TOPIC_NIGHT_MODE:
        current_night_mode = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние ночного режима: {'on' if current_night_mode else 'off'}")
    elif msg.topic == MQTT_TOPIC_PHYSICAL_POWER:
        # Парсим JSON-сообщение и получаем значение "state"
        payload = json.loads(msg.payload.decode())
        current_physical_power = payload.get("state") == "ON"
        log_message(client, f"Физическое питание: {'ON' if current_physical_power else 'OFF'}")
        if not current_physical_power:  # Питание отключено
            reset_states(client)      

def calculate_signals(current_state, target_state, state_list):
    """
    Функция для расчета количества сигналов, необходимых для переключения с текущего состояния на целевое.
    """
    current_index = state_list.index(current_state)
    target_index = state_list.index(target_state)

    if target_index >= current_index:
        signals_needed = target_index - current_index
    else:
        signals_needed = len(state_list) - current_index + target_index

    return signals_needed

def get_last_ir_code():
    """Получает последний отправленный IR код из файла."""
    if os.path.exists(LAST_IR_CODE_FILE):
        with open(LAST_IR_CODE_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_last_ir_code(ir_code):
    """Сохраняет последний отправленный IR код в файл."""
    with open(LAST_IR_CODE_FILE, 'w') as f:
        f.write(ir_code)

def choose_random_signal(signals_list):
    """
    Функция для выбора случайного сигнала из списка.
    Проверяет, отличается ли новый сигнал от последнего отправленного.
    """
    last_ir_code = get_last_ir_code()
    
    available_signals = [signal for signal in signals_list if signal != last_ir_code]
    
    if not available_signals:
        log_message(None, "Все сигналы уже были отправлены ранее. Используем последний отправленный сигнал.")
        return last_ir_code  # Возвращаем последний сигнал, если нет других вариантов
    
    ir_code = random.choice(available_signals)
    log_message(None, f"Выбран уникальный IR сигнал: {ir_code}")
    
    save_last_ir_code(ir_code)  # Сохраняем новый код в файл
    
    return ir_code

def send_ir_signals(client, signals_list, signal_count, topic, state):
    """
    Функция для отправки IR сигналов с задержкой через MQTT и обновления состояния.
    Выбирает случайный сигнал из списка и отправляет его.
    """
    if not signals_list:
        log_message(client, "Ошибка: список сигналов пуст.")
        return

    for i in range(signal_count):
        ir_code = choose_random_signal(signals_list)
        
        if ir_code:
            time.sleep(TIMEOUT)  # Таймаут после каждого сигнала
            client.publish(MQTT_TOPIC_IR_SEND, ir_code, qos=MQTT_QOS)
            log_message(client, f"Отправлен IR сигнал для состояния: {state} с кодом {ir_code}")
        else:
            log_message(client, "Не удалось выбрать IR сигнал для отправки.")
    
    # После отправки сигналов, публикуем новое состояние
    client.publish(topic, state, qos=MQTT_QOS, retain=True)
    log_message(client, f"Опубликовано обновленное состояние '{state}' в топик: {topic}")

    # Завершаем цикл отправки сигналов
    log_message(client, f"Отправка сигналов завершена для состояния: {state}")

def update_steam_ion_state(client, target_steam, target_ion):
    current_state = {"steam": "on" if current_steam else "off", "ion": "on" if current_ion else "off"}
    target_state = {"steam": target_steam, "ion": target_ion}
    
    # Найдем текущее и целевое состояние в списке
    current_index = next((i for i, state in enumerate(STEAM_ION_STATES) if state == current_state), None)
    target_index = next((i for i, state in enumerate(STEAM_ION_STATES) if state == target_state), None)
    
    if current_index is None or target_index is None:
        raise ValueError(f"Неправильное состояние пара или ионизации.")
    
    # Рассчитываем количество необходимых переключений
    signals_needed = (target_index - current_index) % len(STEAM_ION_STATES)
    
    # Отправляем соответствующее количество сигналов
    if signals_needed > 0:
        send_ir_signals(client, IR_SIGNALS_ION, signals_needed, MQTT_TOPIC_STEAM, target_steam)
        send_ir_signals(client, IR_SIGNALS_ION, signals_needed, MQTT_TOPIC_ION, target_ion)

def reset_states(client):
    """Функция для сброса состояний до стандартных значений."""
    global current_power, current_mode, current_steam, current_ion, current_light, current_night_mode

    current_power = False
    current_mode = "Auto"
    current_steam = False
    current_ion = False
    current_light = False
    current_night_mode = False

    publish_state(client, MQTT_TOPIC_POWER, "off")
    publish_state(client, MQTT_TOPIC_MODE, "Auto")
    publish_state(client, MQTT_TOPIC_STEAM, "off")
    publish_state(client, MQTT_TOPIC_ION, "off")
    publish_state(client, MQTT_TOPIC_LIGHT, "off")
    publish_state(client, MQTT_TOPIC_NIGHT_MODE, "off")
    log_message(client, "Все состояния сброшены до стандартных значений")

def publish_state(client, topic, state):
    """Функция для публикации состояния с QoS 1."""
    client.publish(topic, state, qos=MQTT_QOS, retain=True)
    log_message(client, f"Опубликовано состояние '{state}' в топик: {topic} с флагом retain и QoS {MQTT_QOS}")

def wait_for_states(timeout=60):
    """Ожидание загрузки всех состояний с таймаутом."""
    start_time = time.time()
    
    while not all([current_power is not None, 
                   current_mode is not None, 
                   current_steam is not None, 
                   current_ion is not None, 
                   current_light is not None,
                   current_night_mode is not None,
                   current_physical_power is not None]):
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            print(f"Превышено время ожидания ({timeout} секунд). Завершение работы.")
            return False  # Вернуть False, если таймаут истек
        print("Ожидание загрузки всех состояний...")
        time.sleep(5)  # Ожидание перед новой проверкой
    return True  # Вернуть True, если все состояния загружены

def main():
    global current_power, current_mode, current_steam, current_ion, current_light, current_night_mode, current_physical_power, TIMEOUT

    parser = argparse.ArgumentParser(description="Управление увлажнителем Timberk через MQTT")
    parser.add_argument("--reset", action="store_true", help="Сброс всех состояний до стандартных")
    parser.add_argument("power_state", choices=["on", "off"], nargs="?", help="Состояние питания")
    parser.add_argument("target_mode", choices=MODES, nargs="?", help="Режим увлажнения")
    parser.add_argument("steam_state", choices=["on", "off"], nargs="?", help="Состояние пара")
    parser.add_argument("ion_state", choices=["on", "off"], nargs="?", help="Состояние ионизации")
    parser.add_argument("light_state", choices=["on", "off"], nargs="?", help="Состояние света")
    parser.add_argument("night_mode_state", choices=["on", "off"], nargs="?", help="Состояние ночного режима")
    parser.add_argument("--timeout", type=int, default=20, help="Таймаут между сигналами (по умолчанию 20 секунд)")

    args = parser.parse_args()

    # Инициализация MQTT клиента перед использованием log_message
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    check_lock()

    try:
        # Установка таймаута
        TIMEOUT = max(args.timeout, 30)

        # Если флаг --reset установлен
        if args.reset:
            client.loop_start()
            reset_states(client)
            client.loop_stop()
            time.sleep(3)  # Ожидание перед завершением
            remove_lock()
            return

        client.loop_start()

        # Логирование параметров, переданных скрипту
        log_message(client, f"Получено power_state: {args.power_state}, target_mode: {args.target_mode}, steam_state: {args.steam_state}, ion_state: {args.ion_state}, light_state: {args.light_state}, night_mode_state: {args.night_mode_state}")

        # Ожидание загрузки состояний с таймаутом
        if not wait_for_states(timeout=60):
            log_message(client, "Не удалось загрузить все состояния. Завершение.")
            remove_lock()
            return

        # Если физическое питание отключено, сбросить значения и завершить работу
        if not current_physical_power:
            log_message(client, "Физическое питание отключено. Сбрасываем состояния до стандартных значений.")
            reset_states(client)
            remove_lock()  # Завершаем выполнение после сброса
            return

        # Проверка и управление питанием устройства
        if args.power_state == "on" and current_physical_power:
            # Если физическое питание включено и увлажнитель выключен
            if not current_power:
                log_message(client, "Включение увлажнителя... Начало отправки IR сигнала")
                send_ir_signals(client, IR_SIGNALS_POWER, 1, MQTT_TOPIC_POWER, "on")
                log_message(client, "Увлажнитель включен")
                time.sleep(10)  # Задержка после включения увлажнителя

            # Логика изменения состояния света
            if current_light != (args.light_state == "on"):
                send_ir_signals(client, IR_SIGNALS_LIGHT, 1, MQTT_TOPIC_LIGHT, args.light_state)
                current_light = (args.light_state == "on")

            # Логика изменения ночного режима
            if current_night_mode != (args.night_mode_state == "on"):
                send_ir_signals(client, IR_SIGNALS_NIGHT_MODE, 1, MQTT_TOPIC_NIGHT_MODE, args.night_mode_state)
                current_night_mode = (args.night_mode_state == "on")

            # Установка режимов увлажнения, пара и ионизации после изменения света и ночного режима
            if current_power:
                # Логика изменения режимов
                signals_needed_mode = calculate_signals(current_mode, args.target_mode, MODES)
                if signals_needed_mode > 0:
                    log_message(client, f"Изменение режима с {current_mode} на {args.target_mode}")
                    send_ir_signals(client, IR_SIGNALS_MODE, signals_needed_mode, MQTT_TOPIC_MODE, args.target_mode)
                    current_mode = args.target_mode

                # Логика изменения состояния пара и ионизации
                update_steam_ion_state(client, args.steam_state, args.ion_state)

        # Если поступила команда на выключение и устройство включено
        elif args.power_state == "off" and current_power:
            log_message(client, "Выключение увлажнителя...")
            send_ir_signals(client, IR_SIGNALS_POWER, 1, MQTT_TOPIC_POWER, "off")
            reset_states(client)
            remove_lock()
            return

    finally:
        remove_lock()
        log_message(client, "Скрипт завершен успешно.")
        client.loop_stop()

if __name__ == "__main__":
    main()
