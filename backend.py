import requests
import urllib.parse
import json


class VSTUAuth:
    def __init__(self):
        self.session = requests.Session()
        # Добавляем стандартные заголовки
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        })

    def login(self, username, password):
        # Используем URL со скриншота
        auth_url = "https://auth.vstu.by/login?redirectUrl="

        # ВАЖНО: Используем именно те ключи, что на скриншоте Payload
        payload = {
            "username": username,
            "password": password
        }

        try:
            # Отправляем как Form Data (data=payload)
            response = self.session.post(auth_url, data=payload, allow_redirects=True)

            # Смотрим куки
            cookies = self.session.cookies.get_dict()
            if "token" in cookies:
                # Декодируем токен из куки
                raw_token = urllib.parse.unquote(cookies["token"])
                token_data = json.loads(raw_token)
                access_token = token_data.get("access_token")

                if access_token:
                    # Устанавливаем Bearer токен для всех GET запросов
                    self.session.headers.update({
                        "Authorization": f"Bearer {access_token}"
                    })
                    print("Авторизация успешна!")
                    return True

            print(f"Ошибка: статус {response.status_code}, токен в куках не найден.")
            return False
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            return False

    def get_statements(self):
        url = "https://student.vstu.by/api/v1/student/account/statements?studentId=undefined&semester=-1&selectPractisesParam=false"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка получения оценок: {response.status_code}")
                return None
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            return None