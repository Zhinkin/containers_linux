import subprocess
import os
import time

###############################################################################
# НАСТРОЙКИ
###############################################################################
# Группа эмуляторов с noVNC
vnc_configs = [
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Samsung Galaxy S10"
    },
    {
        "image": "budtmo/docker-android:emulator_13.0",
        "device": "Samsung Galaxy S10"
    },
    {
        "image": "budtmo/docker-android:emulator_12.0",
        "device": "Samsung Galaxy S10"
    },
    {
        "image": "budtmo/docker-android:emulator_12.0",
        "device": "Samsung Galaxy S10"
    },
    {
        "image": "budtmo/docker-android:emulator_10.0",
        "device": "Samsung Galaxy S9"
    },     
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Samsung Galaxy S8"
    },
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Samsung Galaxy S7 Edge"
    }, 
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Nexus 7"
    },
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Nexus 5"
    },
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Nexus 4"
    },
    {
        "image": "budtmo/docker-android:emulator_14.0",
        "device": "Nexus S"
    }
    
    
]

# Группа эмуляторов без noVNC (доступных через ADB + scrcpy)
scrcpy_configs = [
    {
        "image": "halimqarroum/docker-android:api-33",
        "device": "Android 33 (Без noVNC)"
    },
    {
        "image": "halimqarroum/docker-android:api-32",
        "device": "Android 32 (Без noVNC)"
    },
    {
        "image": "halimqarroum/docker-android:api-28",
        "device": "Android 28 (Без noVNC)"
    }
]




base_port = 5554         
base_vnc_port = 5900     
base_web_port = 6080     
base_appium_port = 4723  

current_dir = os.getcwd()
log_file_path = os.path.join(current_dir, "emulator_log.txt")
html_index_path = os.path.join(current_dir, "index.html")
html_stats_path = os.path.join(current_dir, "stats.html")


def container_exists(container_name: str) -> bool:
    """Проверяет, существует ли контейнер с данным именем."""
    result = subprocess.run(
        f"docker ps -a -q -f name=^{container_name}$",
        shell=True,
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())

def remove_container(container_name: str):
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[INFO] Удаляем контейнер: {container_name}\n")
    subprocess.run(f"docker rm -f {container_name}", shell=True, check=False)

def run_docker_container(image_name: str, device_name: str, index: int, group: str):
    container_name = f"android-container-{group}-{index+1}"


    console_port = base_port + 2 * index      # 5554, 5556...
    adb_port     = base_port + 2 * index + 1  # 5555, 5557...
    vnc_port     = base_vnc_port + index      # 5900, 5901...
    web_port     = base_web_port + index      # 6080, 6081...
    appium_port  = base_appium_port + index   # 4723, 4724...

    port_args = " ".join([
        f"-p {appium_port}:4723",
        f"-p {console_port}:5554",
        f"-p {adb_port}:5555",
        f"-p {vnc_port}:5900",
        f"-p {web_port}:6080",
    ])

    # Удаляем, если уже есть контейнер с таким именем
    if container_exists(container_name):
        remove_container(container_name)

    cmd = (
        f"docker run -d "
        f"--name {container_name} "
        f"--gpus all "
        f"--privileged "
        f"--device /dev/kvm "
        f"{port_args} "
        f"-e EMULATOR_DEVICE='{device_name}' "
        f"-e WEB_VNC=true "  
        f"-e APPIUM=true "
        f"-e ANDROID_EMULATOR_USE_GPU=host " 
        f"--shm-size=2g "
        f"{image_name}"
    )


    # Логируем команду
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[INFO] Запускается контейнер: {container_name}\n")
        log_file.write(f"       Образ: {image_name}\n")
        log_file.write(f"       Устройство: {device_name}\n")
        log_file.write(f"       Команда: {cmd}\n")

    # Запускаем контейнер
    process_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Пишем результат в лог
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[DEBUG] Return code: {process_result.returncode}\n")
        if process_result.stdout:
            log_file.write(f"[DEBUG] STDOUT:\n{process_result.stdout}\n")
        if process_result.stderr:
            log_file.write(f"[DEBUG] STDERR:\n{process_result.stderr}\n")

    if process_result.returncode == 0:
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[SUCCESS] Контейнер {container_name} успешно запущен.\n")
        print(f"Контейнер {container_name} (ADB={adb_port}, VNC={vnc_port}, WEB={web_port}) запущен.")
        return container_name, adb_port, web_port
    else:
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[ERROR] Не удалось запустить контейнер {container_name}.\n")
        print(f"Ошибка при запуске {container_name}. Подробности см. в {log_file_path}")
        return None, None, None

###############################################################################
# 1. Подготовка лог-файла
###############################################################################
with open(log_file_path, "w", encoding="utf-8") as log_file:
    log_file.write("=== Запуск скрипта эмуляторов (VNC и SCRCPY) ===\n")

###############################################################################
# 2. Запуск эмуляторов VNC
###############################################################################
vnc_container_info = []
for i, config in enumerate(vnc_configs):
    image_name = config["image"]
    device_name = config["device"]
    container_name, adb_port, web_port = run_docker_container(
        image_name, device_name, i, group="vnc"
    )
    if container_name:
        vnc_container_info.append((container_name, device_name, adb_port, web_port))

###############################################################################
# 3. Запуск эмуляторов SCRCPY
###############################################################################
offset = len(vnc_configs)  # чтобы не пересекать порты
scrcpy_container_info = []
for i, config in enumerate(scrcpy_configs):
    image_name = config["image"]
    device_name = config["device"]
    # index = offset + i
    container_name, adb_port, web_port = run_docker_container(
        image_name, device_name, offset + i, group="scrcpy"
    )
    if container_name:
        scrcpy_container_info.append((container_name, device_name, adb_port, web_port))

###############################################################################
# 4. Генерация index.html
###############################################################################
vnc_list_items = []
for (cname, dname, adb_p, web_p) in vnc_container_info:
    vnc_list_items.append(
        f'<li>{cname} ({dname}) — <a href="http://localhost:{web_p}" target="_blank">noVNC</a> (ADB: {adb_p})</li>'
    )

scrcpy_list_items = []
for (cname, dname, adb_p, web_p) in scrcpy_container_info:
    scrcpy_list_items.append(
        f'<li>{cname} ({dname}) — ADB: {adb_p}, '
        f'<code>adb connect 127.0.0.1:{adb_p}</code> и <code>scrcpy -s 127.0.0.1:{adb_p}</code></li>'
    )

index_html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Android Emulators Index</title>
</head>
<body>
    <h1>Список эмуляторов</h1>

    <h2>Эмуляторы с noVNC</h2>
    <ul>
        {''.join(vnc_list_items)}
    </ul>

    <h2>Эмуляторы для SCRCPY</h2>
    <ul>
        {''.join(scrcpy_list_items)}
    </ul>

    <hr>
    
</body>
</html>
"""

with open(html_index_path, "w", encoding="utf-8") as f:
    f.write(index_html_content)

print(f"\nindex.html создан: {html_index_path}")



print("Готово! Откройте index.html в браузере, чтобы увидеть эмуляторы и перейти к статистике.")
