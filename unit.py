import subprocess
import sys
import os
import tempfile
import traceback
import difflib


class UnitTester:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.results = []

    def run_tests(
        self, source_code: str, inputs: list[str], expected_outputs: list[str]
    ):
        """
        Запуск тестов для студенческого решения

        Args:
            source_code: исходный код студента
            inputs: список входных данных для тестов
            expected_outputs: список ожидаемых выходных данных

        Returns:
            Словарь с результатами тестирования
        """
        self.results = []

        # Создаем временный файл для кода
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            # Компилируем код для проверки синтаксиса
            try:
                compile(source_code, temp_file, "exec")
            except SyntaxError as e:
                return {
                    "correct": False,
                    "errors": [f"Синтаксическая ошибка: {e}"],
                    "logs": ["Код содержит синтаксические ошибки"],
                    "detailed_results": [],
                }

            # Запускаем тесты
            for i, (input_data, expected_output) in enumerate(
                zip(inputs, expected_outputs)
            ):
                result = self._run_single_test(
                    temp_file, input_data, expected_output, i + 1
                )
                self.results.append(result)

            # Анализируем общие результаты
            total_tests = len(inputs)
            passed_tests = sum(1 for r in self.results if r["correct"])

            return {
                "correct": passed_tests == total_tests,
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "errors": self._get_all_errors(),
                "logs": self._get_all_logs(),
                "detailed_results": self.results,
            }

        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_file)
            except:
                pass

    def _run_single_test(
        self, file_path: str, input_data: str, expected_output: str, test_num: int
    ) -> dict[str, str]:
        """
        Запуск одного теста

        Args:
            file_path: путь к файлу с кодом
            input_data: входные данные
            expected_output: ожидаемый вывод
            test_num: номер теста

        Returns:
            Результат выполнения теста
        """
        try:
            # Запускаем программу с входными данными
            process = subprocess.Popen(
                [sys.executable, file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(
                    input=input_data, timeout=self.timeout
                )
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return {
                    "test_number": test_num,
                    "correct": False,
                    "input": input_data,
                    "expected_output": expected_output,
                    "actual_output": "",
                    "error": f"Таймаут выполнения ({self.timeout} сек)",
                    "log": stdout + stderr,
                    "diff": "",
                }

            # Проверяем наличие ошибок выполнения
            if process.returncode != 0:
                return {
                    "test_number": test_num,
                    "correct": False,
                    "input": input_data,
                    "expected_output": expected_output,
                    "actual_output": stdout,
                    "error": f"Ошибка выполнения (код возврата: {process.returncode}): {stderr}",
                    "log": stdout + stderr,
                    "diff": "",
                }

            # Нормализуем вывод для сравнения (убираем лишние пробелы)
            actual_normalized = self._normalize_output(stdout)
            expected_normalized = self._normalize_output(expected_output)

            # Сравниваем вывод
            is_correct = actual_normalized == expected_normalized

            # Генерируем diff для отображения различий
            diff = ""
            if not is_correct:
                diff = self._generate_diff(expected_output, stdout)

            return {
                "test_number": test_num,
                "correct": is_correct,
                "input": input_data,
                "expected_output": expected_output,
                "actual_output": stdout,
                "error": "" if is_correct else "Вывод не совпадает с ожидаемым",
                "log": stdout + stderr,
                "diff": diff,
            }

        except Exception as e:
            return {
                "test_number": test_num,
                "correct": False,
                "input": input_data,
                "expected_output": expected_output,
                "actual_output": "",
                "error": f"Неожиданная ошибка: {str(e)}",
                "log": traceback.format_exc(),
                "diff": "",
            }

    def _normalize_output(self, output: str) -> str:
        """
        Нормализация вывода для сравнения
        """
        # Убираем пробелы в начале и конце, нормализуем переводы строк
        lines = [line.rstrip() for line in output.splitlines()]
        # Убираем пустые строки в конце
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    def _generate_diff(self, expected: str, actual: str) -> str:
        """
        Генерация diff между ожидаемым и фактическим выводом
        """
        expected_lines = expected.splitlines()
        actual_lines = actual.splitlines()

        diff = difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="Ожидаемый вывод",
            tofile="Фактический вывод",
            lineterm="",
        )

        return "\n".join(diff)

    def _get_all_errors(self) -> list[str]:
        """Получить все ошибки из всех тестов"""
        errors = []
        for result in self.results:
            if result["error"]:
                errors.append(f"Тест {result['test_number']}: {result['error']}")
        return errors

    def _get_all_logs(self) -> list[str]:
        """Получить все логи выполнения"""
        logs = []
        for result in self.results:
            if result["log"]:
                logs.append(f"--- Тест {result['test_number']} ---")
                logs.append(result["log"])
        return logs


def example():
    code = """
print("1", 1)
    """
    const test = UnitTester()
