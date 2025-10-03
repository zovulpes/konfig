import getpass # для получения имени пользователя
import socket  # для получения hostname
import shlex   # для команды split - разделение строки на токены

hostname = socket.gethostname()
username = getpass.getuser()
prompt = f"{username}@{hostname}:~$ "

supported_commands =  {"ls", "cd", "exit"}

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
