import flet as ft
from flet import ScrollMode

from backend import VSTUAuth
import json
import os
import urllib.parse
import requests

CONFIG_FILE = "config.json"

BOT_TOKEN = "укажите токен бота"
CHAT_ID = "узнать у BotFather"

def send_to_telegram(name, topic, message):
    text = f"📬 <b>Обратная связь ВГТУ Зачетка</b>\n\n"
    text += f"<b>От:</b> {name or 'Аноним'}\n"
    text += f"<b>Тема:</b> {topic or 'Без темы'}\n"
    text += f"<b>Сообщение:</b>\n{message}"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def get_stipend_status(avg_grade):
    if avg_grade >= 9.0:
        return "💰 Повышенная стипендия (x1.6)", ft.Colors.CYAN_ACCENT
    elif avg_grade >= 8.0:
        return "💰 Повышенная стипендия (x1.4)", ft.Colors.GREEN_ACCENT
    elif avg_grade >= 6.0:
        return "✅ Стипендия (x1.2)", ft.Colors.BLUE_GREY_200
    elif avg_grade >= 5.0:
        return "✅ Минимальная стипендия (x1)", ft.Colors.AMBER_100
    else:
        return "⚠️ Без стипендии", ft.Colors.RED_ACCENT


def save_credentials(login, password, data=None):
    payload = {"login": login, "pass": password}
    if data:
        payload["last_data"] = data
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main(page: ft.Page):
    page.title = "ВГТУ Зачетка"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_width = 450
    page.window_height = 800
    page.scroll = ScrollMode.HIDDEN

    auth_service = VSTUAuth()
    creds = load_credentials()

    def switch_tab(index):
        page.navigation_bar.selected_index = index
        if index == 0:
            if hasattr(page, '_grades_data'):
                show_grades(page._grades_data, page._grades_offline)
            else:
                show_login()
        else:
            show_feedback()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=lambda e: switch_tab(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.SCHOOL_OUTLINED, selected_icon=ft.Icons.SCHOOL, label="Зачётка"),
            ft.NavigationBarDestination(icon=ft.Icons.FEEDBACK_OUTLINED, selected_icon=ft.Icons.FEEDBACK, label="Обратная связь"),
        ],
        bgcolor="#1E1E1E",
        indicator_color=ft.Colors.CYAN_ACCENT,
    )

    def show_grades(data, is_offline=False):
        try:
            page.clean()
            page.appbar = ft.AppBar(
                title=ft.Text("ВГТУ Зачетка"),
                bgcolor="#1E1E1E",
            )
            if is_offline:
                page.appbar.title = ft.Text("Оффлайн режим (кэш)")

            semesters = {}
            v_grades = {}

            for item in data.get("statements", []):
                sem = item.get("semesterNumber", "—")
                if sem not in semesters:
                    semesters[sem] = []
                semesters[sem].append(item)

            sorted_nums = sorted(semesters.keys(), reverse=True)
            results_view = ft.Column(spacing=10, scroll="adaptive", expand=True)

            avg_all_val = float(data.get("average", 0.0))

            prog_ring_overall = ft.ProgressRing(
                value=avg_all_val / 10, stroke_width=6,
                color=ft.Colors.AMBER_ACCENT, bgcolor=ft.Colors.WHITE10,
                width=140, height=140
            )

            prog_ring_semester = ft.ProgressRing(
                value=0.0, stroke_width=10,
                color=ft.Colors.CYAN_ACCENT, bgcolor=ft.Colors.GREY_800,
                width=110, height=110
            )

            ring_text = ft.Text("0.0", size=24, weight="bold")

            ring_container = ft.Container(
                content=ft.Stack([
                    prog_ring_overall,
                    ft.Container(prog_ring_semester, padding=15),
                    ft.Container(
                        content=ft.Column([
                            ring_text,
                            ft.Text(f"Общий: {avg_all_val}", size=11, color=ft.Colors.GREY_500)
                        ], spacing=-5, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER),
                        width=140, height=140
                    )
                ], alignment=ft.alignment.Alignment.CENTER),
                alignment=ft.alignment.Alignment.CENTER,
                margin=ft.Margin(top=10, bottom=10),
                height=160
            )

            def update_semester_view(sem_num):
                results_view.controls.clear()
                subjects = semesters[sem_num]
                combined_grades, actually_pending = [], []

                for s in subjects:
                    s_key = f"{s.get('disciplineName')}_{s.get('examType')}"
                    grade_val = str(s.get("grade", ""))
                    if grade_val.isdigit():
                        combined_grades.append(int(grade_val))
                    elif s_key in v_grades:
                        combined_grades.append(v_grades[s_key])
                    elif "зачет" not in str(s.get("examType")).lower() or "дифф" in str(s.get("examType")).lower():
                        actually_pending.append(s)

                current_avg = sum(combined_grades) / len(combined_grades) if combined_grades else 0.0
                prog_ring_semester.value = current_avg / 10
                prog_ring_semester.color = ft.Colors.CYAN_ACCENT if current_avg >= 8 else ft.Colors.AMBER_ACCENT
                ring_text.value = f"{current_avg:.2f}"

                stipend_text, stipend_color = get_stipend_status(current_avg)
                sum_current = sum(combined_grades)
                count_total = len(combined_grades) + len(actually_pending)

                def get_combos(target):
                    needed = (target * count_total) - sum_current
                    if needed <= 0: return "Достигнуто! ✅"
                    if not actually_pending or (needed / len(actually_pending)) > 10: return "—"
                    base, rem = int(needed // len(actually_pending)), int(needed % len(actually_pending))
                    return " + ".join(
                        map(str, sorted([base + 1] * rem + [base] * (len(actually_pending) - rem), reverse=True)))

                results_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.CYAN_ACCENT, size=20),
                                    ft.Text("АНАЛИЗ И СТИПЕНДИЯ", weight="bold", size=14, color=ft.Colors.CYAN_ACCENT)],
                                   alignment=ft.MainAxisAlignment.CENTER),
                            ft.Divider(height=1, color=ft.Colors.WHITE24),
                            ft.Row([ft.Icon(ft.Icons.PAYMENT, color=stipend_color, size=18),
                                    ft.Text(stipend_text, color=stipend_color, weight="bold", size=14)],
                                   alignment=ft.MainAxisAlignment.CENTER),
                            ft.Text(f"🎯 Для 8.0: {get_combos(8.0)}", size=13, color=ft.Colors.GREY_300),
                            ft.Text(f"🎯 Для 9.0: {get_combos(9.0)}", size=13, color=ft.Colors.GREY_300),
                        ], spacing=8),
                        padding=15, border_radius=15, bgcolor="#1E1E1E", border=ft.Border.all(1, ft.Colors.CYAN_700),
                    )
                )

                def set_grade_internal(e, key):
                    if e.control.data == "clear":
                        v_grades.pop(key, None)
                    else:
                        v_grades[key] = int(e.control.data)
                    update_semester_view(sem_num)

                def create_subject_card(s):
                    name, stype = s.get("disciplineName"), s.get("examType")
                    key = f"{name}_{stype}"
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")

                    def show_selector_internal(e):
                        e.control.content = ft.Column([
                            ft.ListTile(title=ft.Text(name, size=12, weight="bold"),
                                        subtitle=ft.Text("Оценка:", size=10)),
                            ft.Row([ft.IconButton(ft.Icons.CLOSE, data="clear",
                                                  on_click=lambda ev: set_grade_internal(ev, key), icon_color="red"),
                                    *[ft.TextButton(str(i), data=i, on_click=lambda ev: set_grade_internal(ev, key)) for
                                      i in range(4, 11)]], wrap=True, alignment=ft.MainAxisAlignment.CENTER)
                        ])
                        e.control.update()

                    return ft.Container(
                        content=ft.ListTile(
                            title=ft.Text(name, size=14, color=ft.Colors.WHITE if not is_p or v_grades.get(
                                key) else ft.Colors.GREY_400),
                            subtitle=ft.Text(stype, size=11, color=ft.Colors.GREY_500),
                            trailing=ft.Text(
                                f"{v_grades.get(key)}*" if v_grades.get(key) else ("?" if is_p else str(grade)),
                                color=ft.Colors.CYAN_ACCENT if v_grades.get(key) else (
                                    ft.Colors.GREEN_ACCENT if not is_p else ft.Colors.WHITE70), size=18,
                                weight="bold")),
                        bgcolor="#1A1A1A" if is_p else ft.Colors.BLACK, border_radius=12,
                        on_click=show_selector_internal if is_p else None
                    )

                for s in subjects: results_view.controls.append(create_subject_card(s))
                page.update()

            page.add(
                ft.Column([
                    ft.Container(height=10),
                    ring_container,
                    ft.Container(
                        content=ft.Row([
                            ft.FilledTonalButton(f"Сем {n}", on_click=lambda e, num=n: update_semester_view(num))
                            for n in sorted_nums
                        ], scroll=ft.ScrollMode.HIDDEN, spacing=10),
                        padding=ft.padding.Padding(10, 0, 10, 10)
                    ),
                    results_view
                ], expand=True)
            )
            if sorted_nums: update_semester_view(sorted_nums[0])

        except Exception as ex:
            print(f"Error in show_grades: {ex}")

    def show_feedback():
        page.clean()
        page.appbar = ft.AppBar(
            title=ft.Text("Обратная связь"),
            bgcolor="#1E1E1E",
        )

        name_field = ft.TextField(label="Ваше имя", border_color=ft.Colors.BLUE_400)
        group_field = ft.TextField(label="Группа", border_color=ft.Colors.BLUE_400)
        msg_field = ft.TextField(
            label="Сообщение",
            multiline=True, min_lines=4, max_lines=8,
            border_color=ft.Colors.BLUE_400
        )
        status_text = ft.Text("", color=ft.Colors.GREEN_ACCENT)

        def send_feedback(e):
            if not msg_field.value:
                status_text.value = "Введите сообщение"
                status_text.color = ft.Colors.RED_ACCENT
                page.update()
                return

            if CHAT_ID == "8842029258:AAGFHwRs77gHgl-tZZJkLKLp4FCOvId3kZM":
                status_text.value = "Ошибка: не настроен chat_id"
                status_text.color = ft.Colors.RED_ACCENT
                page.update()
                return

            ok = send_to_telegram(name_field.value, group_field.value, msg_field.value)
            if ok:
                status_text.value = "Отправлено! ✅"
                status_text.color = ft.Colors.GREEN_ACCENT
                name_field.value = ""
                group_field.value = ""
                msg_field.value = ""
            else:
                status_text.value = "Ошибка отправки"
                status_text.color = ft.Colors.RED_ACCENT

            page.update()

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.FEEDBACK, size=50, color=ft.Colors.BLUE_400),
                    ft.Text("Нашли баг? Есть идея?", size=18, weight="bold"),
                    ft.Text("Напишите — отвечу как можно скорее", size=12, color=ft.Colors.GREY_500),
                    ft.Container(height=20),
                    name_field,
                    group_field,
                    msg_field,
                    ft.Container(height=10),
                    ft.FilledButton("Отправить", icon=ft.Icons.SEND, on_click=send_feedback, width=page.window_width - 40),
                    ft.Container(height=10),
                    status_text,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.Alignment.CENTER,
            )
        )

    def show_login():
        page.clean()
        page.appbar = None
        page.navigation_bar.visible = False

        login_input = ft.TextField(label="Логин", value=creds.get("login", "") if creds else "",
                                   border_color=ft.Colors.BLUE_400)
        pass_input = ft.TextField(label="Пароль", password=True, value=creds.get("pass", "") if creds else "",
                                  can_reveal_password=True)
        remember_me = ft.Checkbox(label="Запомнить меня", value=True if creds else False)
        error_text = ft.Text("", color=ft.Colors.RED_ACCENT)
        loading_ring = ft.ProgressRing(visible=False, width=20, height=20)

        def login_click(e):
            error_text.value = ""
            login_button.disabled = True
            loading_ring.visible = True
            page.update()

            l, p = login_input.value, pass_input.value
            try:
                if auth_service.login(l, p):
                    data = auth_service.get_statements()
                    if data:
                        if creds and "last_data" in creds:
                            old_count = len(creds["last_data"].get("statements", []))
                            new_count = len(data.get("statements", []))

                            if new_count > old_count:
                                page.snack_bar = ft.SnackBar(
                                    ft.Text(f"🔥 Ура! Появились новые оценки ({new_count - old_count} шт.)"),
                                    bgcolor=ft.Colors.GREEN_800
                                )
                                page.snack_bar.open = True
                            elif data.get("statements") != creds["last_data"].get("statements"):
                                page.snack_bar = ft.SnackBar(
                                    ft.Text("🔔 Есть изменения в оценках!"),
                                    bgcolor=ft.Colors.BLUE_800
                                )
                                page.snack_bar.open = True

                        if remember_me.value:
                            save_credentials(l, p, data)

                        page._grades_data = data
                        page._grades_offline = False
                        page.navigation_bar.visible = True
                        switch_tab(0)
                        return

                if creds and "last_data" in creds:
                    page.snack_bar = ft.SnackBar(ft.Text("Вход через кэш"), bgcolor=ft.Colors.ORANGE_800)
                    page.snack_bar.open = True
                    page._grades_data = creds["last_data"]
                    page._grades_offline = True
                    page.navigation_bar.visible = True
                    switch_tab(0)
                else:
                    error_text.value = "Ошибка сервера / Нет кэша"
                    reset_login_state()
            except Exception as ex:
                print(f"Login error: {ex}")
                if creds and "last_data" in creds:
                    page._grades_data = creds["last_data"]
                    page._grades_offline = True
                    page.navigation_bar.visible = True
                    switch_tab(0)
                else:
                    error_text.value = "Ошибка сети"
                    reset_login_state()

        def reset_login_state():
            login_button.disabled = False
            loading_ring.visible = False
            page.update()

        login_button = ft.FilledButton("Войти", on_click=login_click)

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(height=80),
                    ft.Icon(ft.Icons.SCHOOL, size=50, color=ft.Colors.BLUE_400),
                    ft.Text("ВГТУ Зачетка", size=24, weight="bold"),
                    ft.Container(height=40),
                    login_input,
                    pass_input,
                    ft.Row([remember_me], alignment=ft.MainAxisAlignment.CENTER),
                    error_text,
                    ft.Row([login_button, loading_ring], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.Alignment.CENTER,
                padding=20
            )
        )

    show_login()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
