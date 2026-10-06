def question_results(answers: list[int], questions: list[dict]) -> list[dict]:
    return [
        {
            "id": question["id"],
            "selected": answer,
            "correct_answer": question["answer"],
            "is_correct": answer == question["answer"],
        }
        for answer, question in zip(answers, questions)
    ]
