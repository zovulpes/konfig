import getpass # для получения имени пользователя
import socket  # для получения hostname
import shlex   # для команды split - разделение строки на токены
import sys     # для доступа к аргументам командной строки

hostname = socket.gethostname()
username = getpass.getuser()
prompt = f"{username}@{hostname}:~$ "

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


def execute_command(tokens):
    """Выполняет одну команду. Возвращает True, если нужно завершить работу."""
    if not tokens:
        return False

    command = tokens[0]
    args = tokens[1:] if len(tokens) > 1 else []

    if command == "exit":
        return True

    elif command in supported_commands:
        if command in ("ls", "cd"):
            # Заглушка: выводим имя команды и аргументы
            arg_str = " ".join(f'"{a}"' if " " in a else a for a in args)
            print(f"{command} {arg_str}".strip())
        else:
            # На случай, если добавятся другие команды
            print(f"{command} {' '.join(args)}".strip())
    else:
        print(f"Ошибка: команда '{command}' не найдена")
        # При выполнении скрипта — останавливаемся при первой ошибке
        if script_path is not None:
            sys.exit(1)
    return False


def run_script(script_file):
    """Выполняет команды из файла, имитируя диалог с пользователем."""
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Ошибка: скрипт не найден: {script_file}")
        sys.exit(1)

    # Определяем, какое приглашение показывать при выводе команд из скрипта
    display_prompt = custom_prompt if custom_prompt else f"{username}@{hostname}:~$ "

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        # Пропускаем пустые строки и комментарии
        if not stripped or stripped.startswith('#'):
            continue

        # Имитируем ввод пользователя: сначала печатаем команду, как будто её ввели
        print(f"{display_prompt}{stripped}")

        # Парсим команду с поддержкой кавычек
        try:
            tokens = shlex.split(stripped)
        except ValueError as e:
            print(f"Ошибка синтаксиса в скрипте (строка {line_num}): {e}")
            sys.exit(1)

        # Выполняем команду
        should_exit = execute_command(tokens)
        if should_exit:
            break


# Если задан путь к скрипту — выполняем его
if script_path:
    run_script(script_path)
else:
    # Иначе запускаем интерактивный режим (REPL)
    while True:
        try:
            # Используем кастомное приглашение, если оно задано
            current_prompt = custom_prompt if custom_prompt else prompt

            user_input = input(current_prompt).strip()
            if not user_input:
                continue

            # Парсинг с поддержкой кавычек
            try:
                tokens = shlex.split(user_input)
            except ValueError as e: # shlex выдаст ошибку при неправильном вводе кавычек
                print(f"Ошибка синтаксиса: {e}")
                continue

            should_exit = execute_command(tokens)
            if should_exit:
                break

        except KeyboardInterrupt:
            print("\nВыход по Ctrl+C")
            break