import subprocess
import csv
import re
import time
from datetime import datetime


CSV_FILENAME = "docker_all_containers_stats.csv"
COLLECTION_INTERVAL = 10   
DURATION_MINUTES = 15      



def convert_memory_to_mib(mem_str):
    """Конвертирует строку объема памяти ('4.424GiB', '512MiB', '200KiB') в MiB."""
    mem_str = mem_str.upper().replace(',', '').strip()
    if 'GIB' in mem_str:
        return float(mem_str.replace('GIB', '')) * 1024
    elif 'MIB' in mem_str:
        return float(mem_str.replace('MIB', ''))
    elif 'KIB' in mem_str:
        return float(mem_str.replace('KIB', '')) / 1024
    elif 'B' in mem_str:
        return float(mem_str.replace('B', '')) / (1024 * 1024)
    else:
        raise ValueError(f"Неизвестный формат памяти: {mem_str}")

def parse_docker_stats(stats_output):
    """
    Разбирает вывод `docker stats --no-stream --format ...` и возвращает 
    словарь { container_name: { ...метрики... }, ... }.
    """
    lines = stats_output.strip().split("\n")


    if len(lines) < 2:
        return {}

    # Регулярка для обработки данных
    pattern = re.compile(
        r'^(\S+)\s+'                                     # Container name
        r'([\d.]+%)\s+'                                  # CPU %
        r'([\d.]+[KMGT]?i?B)\s*/\s*([\d.]+[KMGT]?i?B)\s+' # Used / Limit Mem
        r'([\d.]+%)\s+'                                  # Mem %
        r'([\d.]+[KMGT]?B)\s*/\s*([\d.]+[KMGT]?B)\s+'     # Net I/O
        r'([\d.]+[KMGT]?B)\s*/\s*([\d.]+[KMGT]?B)\s+'     # Block I/O
        r'(\d+)$'                                        # PIDs
    )

    stats_dict = {}
    for line in lines[1:]:
        match = pattern.match(line)
        if not match:
            # Если какая-то строка не подходит под шаблон
            continue

        container_name = match.group(1)
        cpu_percent = match.group(2).replace('%', '').strip()
        mem_usage = convert_memory_to_mib(match.group(3))
        mem_limit = convert_memory_to_mib(match.group(4))
        mem_percent = match.group(5).replace('%', '').strip()
        net_io = match.group(6) + " / " + match.group(7)
        block_io = match.group(8) + " / " + match.group(9)
        pids = match.group(10)

        stats_dict[container_name] = {
            "Container": container_name,
            "CPU %": float(cpu_percent),
            "Memory Usage (MiB)": mem_usage,
            "Memory Limit (MiB)": mem_limit,
            "Memory %": float(mem_percent),
            "Net I/O": net_io,
            "Block I/O": block_io,
            "PIDs": int(pids)
        }

    return stats_dict

def collect_docker_stats():
    """
    Вызывает `docker stats --no-stream` и возвращает словарь с данными.
    Форматируем вывод, чтобы упростить парсинг.
    """
    cmd = (
        "docker stats --no-stream "
        "--format 'table {{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.MemPerc}} "
        "{{.NetIO}} {{.BlockIO}} {{.PIDs}}'"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0 and result.stdout:
        return parse_docker_stats(result.stdout)
    else:
        print(f"[ERROR] Ошибка выполнения docker stats: {result.stderr}")
        return {}

# --------------------- Парсинг docker ps ---------------------

def parse_docker_ps(ps_output):
    """
    Разбирает вывод `docker ps --format ...` и возвращает 
    словарь { container_name: { 'Image': ..., 'State': ..., 'Status': ..., 'Ports': ...}, ... }.
    """
    lines = ps_output.strip().split("\n")
    if len(lines) < 2:
        return {}

    # Первая строка — это заголовок (table ...)
    data_dict = {}
    for line in lines[1:]:
        # Ожидаем формат: NAME|IMAGE|STATE|STATUS|PORTS (через разделитель)
        parts = line.split("|")
        if len(parts) < 5:
            continue
        name, image, state, status, ports = parts
        data_dict[name] = {
            "Image": image.strip(),
            "State": state.strip(),
            "Status": status.strip(),
            "Ports": ports.strip()
        }
    return data_dict

def collect_docker_ps():
    """
    Вызывает `docker ps` в отформатированном виде и парсит результат.
    """
    cmd = (
        "docker ps --format "
        "'table {{.Names}}|{{.Image}}|{{.State}}|{{.Status}}|{{.Ports}}'"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0 and result.stdout:
        return parse_docker_ps(result.stdout)
    else:
        print(f"[ERROR] Ошибка выполнения docker ps: {result.stderr}")
        return {}

# --------------------- Сохранение в CSV ---------------------

def save_to_csv(collected_data):
    """
    Сохраняет объединённые данные (словарь) в CSV-файл.
    collected_data = {
        container_name: {
            "Container": ...
            "CPU %": ...
            "Memory Usage (MiB)": ...
            "Memory Limit (MiB)": ...
            "Memory %": ...
            "Net I/O": ...
            "Block I/O": ...
            "PIDs": ...
            "Image": ...
            "State": ...
            "Status": ...
            "Ports": ...
        },
        ...
    }
    """
    fieldnames = [
        "Timestamp",
        "Container",
        "Image",
        "CPU %",
        "Memory Usage (MiB)",
        "Memory Limit (MiB)",
        "Memory %",
        "Net I/O",
        "Block I/O",
        "PIDs",
        "State",
        "Status",
        "Ports",
    ]

    with open(CSV_FILENAME, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for container_name, data in collected_data.items():
            row = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Container": data.get("Container", container_name),
                "Image": data.get("Image", ""),
                "CPU %": data.get("CPU %", 0.0),
                "Memory Usage (MiB)": data.get("Memory Usage (MiB)", 0.0),
                "Memory Limit (MiB)": data.get("Memory Limit (MiB)", 0.0),
                "Memory %": data.get("Memory %", 0.0),
                "Net I/O": data.get("Net I/O", ""),
                "Block I/O": data.get("Block I/O", ""),
                "PIDs": data.get("PIDs", 0),
                "State": data.get("State", ""),
                "Status": data.get("Status", ""),
                "Ports": data.get("Ports", ""),
            }
            writer.writerow(row)

    print(f"[INFO] Данные сохранены в файл: {CSV_FILENAME}")

# --------------------- Основной цикл мониторинга ---------------------

def main():
    print("[INFO] Начало сбора статистики контейнеров...")

    total_duration = DURATION_MINUTES * 60  # Преобразуем минуты в секунды
    start_time = time.time()

    # Собираем все результаты за несколько итераций.
    # Если нужно накопить статистику за всё время, можно хранить списком.
    # Ниже — пример, как можно хранить итоговую «последнюю» метрику каждого контейнера.
    # Если хочется всё сложить построчно, нужно изменить логику сохранения.
    combined_data = {}

    while time.time() - start_time < total_duration:
        # 1. Собираем данные из docker stats
        stats_data = collect_docker_stats()  # {container_name: {...}}
        # 2. Собираем данные из docker ps
        ps_data = collect_docker_ps()        # {container_name: {...}}

        # 3. Объединяем по имени контейнера
        #   Для всех контейнеров, которые нашли в stats_data и ps_data
        all_containers = set(stats_data.keys()) | set(ps_data.keys())
        for c in all_containers:
            combined_data.setdefault(c, {})
            combined_data[c].update(stats_data.get(c, {}))
            combined_data[c].update(ps_data.get(c, {}))

        time.sleep(COLLECTION_INTERVAL)

    print("[INFO] Сбор данных завершён.")

    # Сохраняем то, что получилось
    save_to_csv(combined_data)

if __name__ == "__main__":
    main()
