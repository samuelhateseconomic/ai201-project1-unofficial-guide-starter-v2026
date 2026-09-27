def judge(question: str, expects: str, answer: str, result: str) -> bool:
    if not expects:
        return False
    return expects.strip().lower() in(answer or "").lower()

