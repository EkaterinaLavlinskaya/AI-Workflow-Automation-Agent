import subprocess
import json
import shlex
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool
    oom_killed: bool

def run_sandboxed(
    command: str,
    work_dir: Optional[str] = None,       # директория для записи (если нужна)
    read_only_mounts: Optional[list] = None, # список путей для ro-монтирования
    timeout_sec: int = 30,
    memory_mb: int = 512,
) -> ExecutionResult:
    """
    Запускает команду через cocoon-sandbox.
    command: строка команды (НЕ передавайте сюда сырой вывод LLM без валидации!)
    """
    # Базовые аргументы cocoon
    args = ["cocoon", "run", "--json"]
    
    # Лимиты
    args.extend(["--timeout", str(timeout_sec)])
    args.extend(["--mem", str(memory_mb)])
    
    # Монтирование
    if read_only_mounts:
        for ro_path in read_only_mounts:
            args.extend(["--ro", ro_path])
    
    if work_dir:
        args.extend(["--work", work_dir])
    
    # Runtime и команда. 
    # Внимание: здесь мы используем shell для простоты, но в production
    # лучше передавать argv-список и использовать --runtime.
    # Для bash/powershell команд используем соответствующий runtime.
    args.extend(["--runtime", "bash", "-c", command])
    
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_sec + 5,  # запас на запуск cocoon
        )
        # cocoon с --json выводит структурированный результат
        try:
            result = json.loads(proc.stdout)
            return ExecutionResult(
                exit_code=result.get("exit_code", -1),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                duration_ms=result.get("duration_ms", 0.0),
                timed_out=result.get("timed_out", False),
                oom_killed=result.get("oom_killed", False),
            )
        except json.JSONDecodeError:
            # Fallback если cocoon вернул не JSON (ошибка запуска)
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr or "cocoon failed to produce JSON",
                duration_ms=0.0,
                timed_out=False,
                oom_killed=False,
            )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr="Sandbox process timed out (outer guard)",
            duration_ms=timeout_sec * 1000.0,
            timed_out=True,
            oom_killed=False,
        )
