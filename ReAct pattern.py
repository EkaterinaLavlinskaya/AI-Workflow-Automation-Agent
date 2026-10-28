import json
from typing import Any

# ---------- ЗАГЛУШКИ ----------

def stub_llm(messages: list[dict]) -> str:
    """
    Заглушка LLM. В реальности здесь вызов OpenAI-compatible API.
    Для демонстрации: если в контексте ещё нет результата инструмента,
    модель «просит» вызвать echo; после получения результата — завершает.
    """
    has_tool_result = any(m["role"] == "tool" for m in messages)
    if not has_tool_result:
        # Имитация ответа с вызовом инструмента (OpenAI tools format)
        return json.dumps({
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "echo",
                    "arguments": json.dumps({"text": "hello from stub"})
                }
            }]
        })
    else:
        # Финальный ответ после получения результата
        return json.dumps({"content": "Задача выполнена: инструмент echo вернул данные."})

# Реестр заглушек-инструментов
TOOLS = {
    "echo": lambda text: f"ECHO: {text}",
}

# ---------- КОНТРОЛЛЕР ЦИКЛА ----------

def run_react_loop(user_query: str, max_iterations: int = 5) -> str:
    """
    Базовый цикл ReAct с заглушками.
    Возвращает финальный ответ или сообщение о превышении лимита.
    """
    messages = [
        {"role": "system", "content": "Ты — ассистент. Используй инструменты, если нужно."},
        {"role": "user", "content": user_query},
    ]

    for step in range(max_iterations):
        print(f"\n--- Шаг {step + 1} ---")

        # 1. ЗАПРОС К LLM (заглушка)
        raw_response = stub_llm(messages)
        print(f"LLM raw: {raw_response}")

        # 2. ПАРСИНГ ОТВЕТА
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            return f"Ошибка парсинга ответа LLM: {raw_response}"

        # 3. ВЕТВЛЕНИЕ: есть вызов инструмента?
        tool_calls = parsed.get("tool_calls")
        if not tool_calls:
            # Финальный ответ
            final = parsed.get("content", "Нет ответа")
            print(f"ФИНАЛ: {final}")
            return final

        # 4. ВЫПОЛНЕНИЕ ИНСТРУМЕНТА (с проверкой по реестру)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = json.loads(call["function"]["arguments"])

            if fn_name not in TOOLS:
                # Ошибка как observation — модель может исправиться
                result = f"ERROR: инструмент '{fn_name}' не найден"
            else:
                try:
                    result = TOOLS[fn_name](**fn_args)
                except Exception as e:
                    result = f"ERROR: {e}"

            print(f"Tool `{fn_name}` -> {result}")

            # 5. ВОЗВРАТ РЕЗУЛЬТАТА В КОНТЕКСТ
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [call],  # эхо вызова
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })

    # Лимит исчерпан
    return "Достигнут лимит итераций. Задача не завершена."

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    answer = run_react_loop("Проверь работу заглушки")
    print(f"\nОтвет агента: {answer}")
