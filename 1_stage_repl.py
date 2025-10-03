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
    else:
        i += 1                        # Переходим к следующему аргументу

# Отладочный вывод параметров
print("=== Параметры эмулятора ===")
print(f"VFS путь: {vfs_path}")
print(f"Скрипт: {script_path}")
print("===========================")

while True:
    try:
        user_input = input(prompt).strip()
        if not user_input:
            continue

        # Парсинг с поддержкой кавычек
        try:
            tokens = shlex.split(user_input)
        except ValueError as e: # shlex выдаст ошибку при неправильном вводе кавычек
            print(f"Ошибка синтаксиса: {e}")
            continue

        command = tokens[0] if tokens else ""
        args = tokens[1:] if len(tokens) > 1 else []

        if command == "exit":
            break

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

    except KeyboardInterrupt:
        print("\nВыход по Ctrl+C")
        break
