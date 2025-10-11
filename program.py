import getpass # для получения имени пользователя
import socket  # для получения hostname
import shlex   # для команды split - разделение строки на токены
import sys     # для доступа к аргументам командной строки
import csv     # для чтения CSV-файла с VFS
import base64  # для декодирования содержимого файлов из base64
from pathlib import PurePosixPath  # для безопасной работы с путями (без доступа к диску)
import datetime  # для команды date

hostname = socket.gethostname()
username = getpass.getuser()
current_dir = "/" # current_dir будет отслеживать текущую директорию в VFS (начинается с "/")

# supported_commands теперь не используется напрямую, но оставлено для совместимости
supported_commands =  {"ls", "cd", "exit"}

# Парсим аргументы командной строки
vfs_path = None    # путь к Виртуальной Файловой Системе
script_path = None # путь к стартовому скрипту
custom_prompt = None  # пользовательское приглашение к вводу

# sys.argv - это список всего что написали в командной строке
# Например: ['1_repl.py', '--vfs-path', 'C:\data', '--script', 'start.txt']

# Проходим по всем аргументам (кроме первого - имени файла)
i = 1
while i < len(sys.argv):
    # Если видим "--vfs-path" и после него ЕСТЬ еще один аргумент
    if sys.argv[i] == "--vfs-path" and i + 1 < len(sys.argv):
        vfs_path = sys.argv[i + 1]    # Берем следующий аргумент
        i += 2                        # Перескакиваем через два аргумента

     # Если видим "--script" и после него ЕСТЬ еще один аргумент 
    elif sys.argv[i] == "--script" and i + 1 < len(sys.argv):
        script_path = sys.argv[i + 1] # Берем следующий аргумент
        i += 2                        # Перескакиваем через два аргумента

    # Если видим "--prompt" и после него ЕСТЬ еще один аргумент
    elif sys.argv[i] == "--prompt" and i + 1 < len(sys.argv):
        custom_prompt = sys.argv[i + 1]  # Берем следующий аргумент как приглашение
        i += 2                           # Перескакиваем через два аргумента

    else:
        i += 1                        # Переходим к следующему аргументу

# Отладочный вывод параметров
print("=== Параметры эмулятора ===")
print(f"VFS путь: {vfs_path}")
print(f"Скрипт: {script_path}")
print(f"Приглашение: {custom_prompt or 'стандартное'}")
print("===========================")

# === VFS: загрузка и работа с файловой системой ===

# vfs — словарь, хранящий виртуальную файловую систему в памяти
# Ключ: абсолютный путь (например, "/home/user")
# Значение: словарь {'type': 'file' или 'dir', 'content': bytes или None}
vfs = {}

def load_vfs(vfs_file):
    """Загружает VFS из CSV-файла. Формат: path,type,content"""
    global vfs
    vfs = {}
    try:
        with open(vfs_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Нормализуем путь: убираем лишние / в конце, кроме корня
                path = row['path'].rstrip('/') if row['path'] != '/' else '/'
                typ = row['type']
                content = None

                if typ == 'file':
                    # Если есть содержимое — декодируем из base64
                    if row['content']:
                        try:
                            content = base64.b64decode(row['content'])
                        except Exception as e:
                            print(f"Ошибка декодирования base64 для {path}: {e}")
                            sys.exit(1)
                    # Если content пуст — файл без данных (разрешено)
                elif typ != 'dir':
                    print(f"Ошибка: неизвестный тип '{typ}' для {path}")
                    sys.exit(1)

                # Проверяем, что путь начинается с '/' (требование VFS)
                if not row['path'].startswith('/'):
                    print(f"Ошибка: путь должен начинаться с '/': {row['path']}")
                    sys.exit(1)

                vfs[path] = {'type': typ, 'content': content}

        # Обязательно должен быть корень
        if '/' not in vfs:
            print("Ошибка: VFS должен содержать корневую директорию '/'")
            sys.exit(1)

    except FileNotFoundError:
        print(f"Ошибка: VFS файл не найден: {vfs_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка загрузки VFS: {e}")
        sys.exit(1)

def normalize_path(path_str):
    """Приводит путь к каноническому виду (обрабатывает .. и .)"""
    if not path_str.startswith('/'):
        raise ValueError("Путь должен быть абсолютным")
    
    # Разбиваем на части, игнорируя пустые и корень
    parts = [part for part in path_str.split('/') if part not in ('', '.')]
    
    normalized = []
    for part in parts:
        if part == '..':
            if normalized:  # нельзя выйти выше корня
                normalized.pop()
        else:
            normalized.append(part)
    
    return '/' + '/'.join(normalized) if normalized else '/'

def resolve_path(input_path):
    """Преобразует относительный или абсолютный путь в абсолютный"""
    if input_path.startswith('/'):
        return normalize_path(input_path)
    else:
        # Объединяем с текущей директорией
        combined = PurePosixPath(current_dir) / input_path
        return normalize_path(str(combined))

# === Реализация команд с поддержкой VFS ===

def cmd_cd(args):
    """Команда cd: изменяет текущую директорию в VFS"""
    global current_dir
    if not args:
        # cd без аргументов — переход в корень
        current_dir = "/"
        return True

    target = args[0]
    try:
        abs_path = resolve_path(target)
    except Exception:
        print(f"cd: ошибка в пути: {target}")
        return False

    # Проверяем существование пути
    if abs_path not in vfs:
        print(f"cd: нет такого файла или директории: {target}")
        return False

    # Проверяем, что это директория
    if vfs[abs_path]['type'] != 'dir':
        print(f"cd: не является директорией: {target}")
        return False

    current_dir = abs_path
    return True

def cmd_ls(args):
    """Команда ls: выводит содержимое директории из VFS"""
    # Определяем целевую директорию
    if args:
        try:
            target_dir = resolve_path(args[0])
        except Exception:
            print(f"ls: ошибка в пути: {args[0]}")
            return False
    else:
        target_dir = current_dir

    # Проверяем существование
    if target_dir not in vfs:
        print(f"ls: нет такого файла или директории: {args[0] if args else ''}")
        return False

    # Проверяем, что это директория
    if vfs[target_dir]['type'] != 'dir':
        print(f"ls: не является директорией: {args[0] if args else ''}")
        return False

    # Собираем прямых потомков (файлы и папки на один уровень глубже)
    contents = []
    for path in vfs:
        if path == target_dir:
            continue
        # Путь является прямым потомком, если он начинается с target_dir/ и не содержит других /
        if path.startswith(target_dir + '/') or (target_dir == '/' and path.startswith('/')):
            rel_part = path[len(target_dir):].lstrip('/')
            if '/' not in rel_part:  # только прямые дети
                contents.append(rel_part)

    contents.sort()
    if contents:
        print('\n'.join(contents))
    
    return True

def cmd_cat(args):
    """Команда cat: выводит содержимое файла из VFS"""
    if not args:
        print("cat: отсутствует операнд")
        return False

    target = args[0]
    try:
        abs_path = resolve_path(target)
    except Exception:
        print(f"cat: ошибка в пути: {target}")
        return False

    if abs_path not in vfs:
        print(f"cat: нет такого файла или директории: {target}")
        return False

    if vfs[abs_path]['type'] != 'file':
        print(f"cat: {target}: это директория")
        return False

    content = vfs[abs_path]['content']
    if content is not None:
        # Пытаемся декодировать как UTF-8; если не получится — выводим как есть (или пропускаем)
        try:
            print(content.decode('utf-8'), end='')
        except UnicodeDecodeError:
            # выводим содержимое.
            print(content.decode('utf-8', errors='replace'), end='')
    
    return True

def cmd_touch(args):
    """Команда touch: создаёт пустой файл в VFS, если он не существует."""
    if not args:
        print("touch: отсутствует операнд")
        return False

    target = args[0]
    try:
        abs_path = resolve_path(target)
    except Exception:
        print(f"touch: ошибка в пути: {target}")
        return False

    # Проверяем, что файл ещё не существует
    if abs_path in vfs:
        # Если уже существует — ничего не делаем (как в реальном touch)
        return True

    # Определяем родительскую директорию
    parent_path = str(PurePosixPath(abs_path).parent)
    if parent_path == '.':
        parent_path = '/'

    # Проверяем, что родительская директория существует и это dir
    if parent_path not in vfs or vfs[parent_path]['type'] != 'dir':
        print(f"touch: невозможно создать '{abs_path}': Нет такого файла или каталога")
        return False

    # Создаём пустой файл
    vfs[abs_path] = {'type': 'file', 'content': None}
    return True
    
def cmd_date(args):
    """Команда date: выводит текущую дату и время в формате, похожем на системный"""
    # Пример: Thu Jun  5 12:34:56 MSK 2025
    # Python не даёт напрямую "MSK", но можно использовать tzname или просто локальное время
    now = datetime.datetime.now()
    # Форматируем вручную, чтобы было похоже на `date` в Linux
    # %a — сокращённое имя дня, %b — сокращённое имя месяца
    formatted = now.strftime("%a %b %d %H:%M:%S %Z %Y")
    # Если %Z пустой (часто бывает), подставим "LOCAL"
    if "%Z" in formatted or not formatted.split()[-2].strip():
        # Простой fallback: убираем %Z и вставляем "LOCAL"
        formatted = now.strftime("%a %b %d %H:%M:%S LOCAL %Y")
    print(formatted)
    return True

# === Выполнение команды (обновлённая версия) ===

def execute_command(tokens):
    """Выполняет одну команду. Возвращает True, если нужно завершить работу."""
    if not tokens:
        return False, True

    command = tokens[0]
    args = tokens[1:] if len(tokens) > 1 else []

    success = True

    if command == "exit":
        return True, True

    elif command == "cd":
        success = cmd_cd(args)

    elif command == "ls":
        success = cmd_ls(args)

    elif command == "cat":
        success = cmd_cat(args)

    elif command == "date":
        success = cmd_date(args)

    elif command == "touch":
        success = cmd_touch(args)

    else:
        print(f"Ошибка: команда '{command}' не найдена")
        # При выполнении скрипта — останавливаемся при первой ошибке
        success = False
    
    return False, success  # Не завершать работу, но вернуть статус

# === Выполнение скрипта (обновлённая версия) ===

def run_script(script_file):
    """Выполняет команды из файла, имитируя диалог с пользователем."""
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Ошибка: скрипт не найден: {script_file}")
        sys.exit(1)

    # Определяем, какое приглашение показывать при выводе команд из скрипта
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        # Пропускаем пустые строки и комментарии
        if not stripped or stripped.startswith('#'):
            continue

        # Формируем приглашение с текущей директорией (как в REPL)
        display_dir = current_dir if current_dir != '/' else '~'
        if custom_prompt:
            display_prompt = custom_prompt
        else:
            display_prompt = f"{username}@{hostname}:{display_dir}$ "

        # Имитируем ввод пользователя: сначала печатаем команду, как будто её ввели
        print(f"{display_prompt}{stripped}")

        # Парсим команду с поддержкой кавычек
        try:
            tokens = shlex.split(stripped)
        except ValueError as e:
            print(f"Ошибка синтаксиса в скрипте (строка {line_num}): {e}")
            sys.exit(1)

        # Выполняем команду
        should_exit, success = execute_command(tokens)

        # ОСТАНАВЛИВАЕМСЯ ПРИ ЛЮБОЙ ОШИБКЕ
        if not success:
            sys.exit(1)

        if should_exit:
            break

# === Загрузка VFS перед запуском ===

if vfs_path:
    load_vfs(vfs_path)
else:
    # Если VFS не задан — создаём минимальную (только корень)
    vfs['/'] = {'type': 'dir', 'content': None}

# Если задан путь к скрипту — выполняем его
if script_path:
    run_script(script_path)
else:
    # Иначе запускаем интерактивный режим (REPL)
    while True:
        try:
            # Используем кастомное приглашение, если оно задано
            # Отображаем текущую директорию: "/" → "~"
            display_dir = current_dir if current_dir != '/' else '~'
            if custom_prompt:
                current_prompt = custom_prompt
            else:
                current_prompt = f"{username}@{hostname}:{display_dir}$ "

            user_input = input(current_prompt).strip()
            if not user_input:
                continue

            # Парсинг с поддержкой кавычек
            try:
                tokens = shlex.split(user_input)
            except ValueError as e: # shlex выдаст ошибку при неправильном вводе кавычек
                print(f"Ошибка синтаксиса: {e}")
                continue

            should_exit, success = execute_command(tokens)
            if should_exit:
                break

        except KeyboardInterrupt:
            print("\nВыход по Ctrl+C")
            break