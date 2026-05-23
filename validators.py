import re


LOGIN_RE = re.compile(r"^[A-Za-z0-9]{5,}$")
PASSWORD_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9~!?@#$%^&*_\-+()[\]{}></\\|\"'.,:;]+$")


def validate_login(login):
    errors = []
    if not login:
        errors.append("Поле не может быть пустым.")
    elif not LOGIN_RE.fullmatch(login):
        errors.append("Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов.")
    return errors


def validate_required(value):
    return [] if value else ["Поле не может быть пустым."]


def validate_password(password):
    errors = []

    if not password:
        return ["Поле не может быть пустым."]

    if len(password) < 8:
        errors.append("Пароль должен содержать не менее 8 символов.")
    if len(password) > 128:
        errors.append("Пароль должен содержать не более 128 символов.")
    if re.search(r"\s", password):
        errors.append("Пароль не должен содержать пробелов.")
    if not re.search(r"[A-ZА-ЯЁ]", password):
        errors.append("Пароль должен содержать как минимум одну заглавную букву.")
    if not re.search(r"[a-zа-яё]", password):
        errors.append("Пароль должен содержать как минимум одну строчную букву.")
    if not re.search(r"[0-9]", password):
        errors.append("Пароль должен содержать как минимум одну арабскую цифру.")
    if not PASSWORD_RE.fullmatch(password):
        errors.append("Пароль содержит недопустимые символы.")

    return errors


def form_value(form, key):
    return (form.get(key) or "").strip()
