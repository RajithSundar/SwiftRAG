import sys

with open('query.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", prompts.ADVICE_SYSTEM_PROMPT.format(
            country=state.get("selected_country", "Unknown"),
            visa=state.get("visa_type", "Unknown"),
            age=info.get('age'),
            nationality=info.get('nationality'),
            financials=info.get('financials'),
            purpose=info.get('purpose'),
            context=context
        )),
        MessagesPlaceholder("messages")
    ])'''

replacement = '''    completed_steps = str(state.get("completed_steps", "Not provided"))

    advice_content = (prompts.ADVICE_SYSTEM_PROMPT
        .replace("{country}", str(state.get("selected_country", "Unknown")))
        .replace("{visa}", str(state.get("visa_type", "Unknown")))
        .replace("{age}", str(info.get('age', 'Unknown')))
        .replace("{nationality}", str(info.get('nationality', 'Unknown')))
        .replace("{financials}", str(info.get('financials', 'Unknown')))
        .replace("{purpose}", str(info.get('purpose', 'Unknown')))
        .replace("{education}", str(info.get('education', 'Not provided')))
        .replace("{employment}", str(info.get('employment', 'Not provided')))
        .replace("{english_proficiency}", str(info.get('english_proficiency', 'Not provided')))
        .replace("{ties_to_home_country}", str(info.get('ties_to_home_country', 'Not provided')))
        .replace("{completed_steps}", completed_steps)
        .replace("{context}", str(context))
    )

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", advice_content),
        MessagesPlaceholder("messages")
    ])'''

if target in text:
    text = text.replace(target, replacement)
    with open('query.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done safely")
else:
    print("Target not found. Something is wrong with the exact text.")
