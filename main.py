import flet as ft
from backend import VSTUAuth


def main(page: ft.Page):
    # Вместо ft.app используем рекомендации новых версий (хотя ft.app пока работает)
    page.title = "ВГТУ Зачетка"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 800
    page.scroll = "adaptive"

    auth_service = VSTUAuth()

    # Поля ввода
    login_input = ft.TextField(label="Логин", value="")  # Можно вписать свой для тестов
    pass_input = ft.TextField(label="Пароль", password=True, can_reveal_password=True)

    # Сюда будем выводить ошибки
    error_text = ft.Text("", color=ft.Colors.RED_400)

    def show_grades(data):
        page.clean()

        # Считаем средний балл прямо здесь
        avg_val = data.get("average", "0.0")

        # ... (весь твой код отрисовки карточек, который мы писали выше) ...
        # Обязательно используй ft.colors (маленькая 'c')

        page.add(ft.Text(f"Средний балл: {avg_val}", size=30))
        # Добавь сюда цикл по semesters, который у тебя уже есть

        page.update()

    def login_click(e):
        error_text.value = "Загрузка..."
        page.update()

        if auth_service.login(login_input.value, pass_input.value):
            data = auth_service.get_statements()
            if data:
                show_grades(data)  # Здесь отрисуется твоя красота из первого скриншота
            else:
                error_text.value = "Ошибка 401: Не удалось получить данные"
                page.update()
        else:
            error_text.value = "Неверный логин или пароль"
            page.update()

    # Начальный экран
    page.add(
        ft.Column([
            ft.Text("ВГТУ Авторизация", size=25, weight="bold"),
            login_input,
            pass_input,
            ft.ElevatedButton("Войти", on_click=login_click),
            error_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )


# Исправляем DeprecationWarning
if __name__ == "__main__":
    ft.app(target=main)