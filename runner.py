
import sys
import os
import pytest

# Текущая папка, куда студент положил EXE
current_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

# Добавляем текущую папку в sys.path, чтобы pytest нашёл student's scripts.py
sys.path.insert(0, current_dir)

# Путь к test.py — он будет bundled внутри EXE
if getattr(sys, 'frozen', False):
    # Запущен как EXE: test.py лежит внутри bundl'а
    test_path = os.path.join(sys._MEIPASS, 'test.py')
else:
    # Запущен как обычный скрипт (для разработки)
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.py')

if __name__ == '__main__':
    exit_code = pytest.main(['-x', test_path, '-v'])
    sys.exit(exit_code)