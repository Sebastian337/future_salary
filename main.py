import os
import time
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable

LANGUAGES = ["Python", "Java", "JavaScript", "C++", "C#", "PHP", "Ruby", "Go", "1С"]

SALARY_MULTIPLIER_ONLY_FROM = 1.2
SALARY_MULTIPLIER_ONLY_TO = 0.8


HH_MOSCOW_AREA = 1
HH_PERIOD_DAYS = 30
HH_VACANCIES_PER_PAGE = 100


SJ_MOSCOW_ID = 4
SJ_IT_CATALOGUE = 48
SJ_VACANCIES_PER_PAGE = 100


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    if salary_from:
        return salary_from * SALARY_MULTIPLIER_ONLY_FROM
    if salary_to:
        return salary_to * SALARY_MULTIPLIER_ONLY_TO
    return None


def predict_rub_salary_hh(vacancy):
    salary = vacancy.get("salary")
    if not salary or salary.get("currency") != "RUR":
        return None
    return predict_salary(salary.get("from"), salary.get("to"))


def predict_rub_salary_sj(vacancy):
    if vacancy.get("currency") != "rub":
        return None
    return predict_salary(vacancy.get("payment_from"), vacancy.get("payment_to"))


def fetch_all_vacancies(make_request, extract_items, get_total):
    all_items = []
    page = 0
    total_found = 0
    
    while True:
        response = make_request(page)
        items = extract_items(response)
        
        if page == 0:
            total_found = get_total(response)
            
        all_items.extend(items)
        
        if not items:
            break
        page += 1
        time.sleep(0.3)
    
    return all_items, total_found


def extract_hh_items(response):
    return response.get("items", [])


def get_hh_total(response):
    return response.get("found", 0)


def extract_sj_items(response):
    return response.get("objects", [])


def get_sj_total(response):
    return response.get("total", 0)


def collect_statistics(make_request, extract_items, get_total, extract_salary):
    all_vacancies, total_found = fetch_all_vacancies(
        make_request,
        extract_items,
        get_total
    )
    
    salaries = []
    for vacancy in all_vacancies:
        salary = extract_salary(vacancy)
        if salary:
            salaries.append(salary)

    if not salaries:
        avg_salary = 0
    else:
        avg_salary = int(sum(salaries) / len(salaries))

    return {
        "vacancies_found": total_found,
        "vacancies_processed": len(salaries),
        "average_salary": avg_salary
    }


def fetch_hh_vacancies(language, page):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": f"ПРОГРАММИСТ {language}",
        "area": HH_MOSCOW_AREA,
        "period": HH_PERIOD_DAYS,
        "search_field": "name",
        "per_page": HH_VACANCIES_PER_PAGE,
        "page": page
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_sj_vacancies(language, api_key, page):
    url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {"X-Api-App-Id": api_key}
    params = {
        "town_id": SJ_MOSCOW_ID,
        "catalogues": SJ_IT_CATALOGUE,
        "keyword": f"программист {language} разработчик {language}",
        "count": SJ_VACANCIES_PER_PAGE,
        "page": page
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def print_statistics_table(statistics, site_name):
    table_data = [
        ["Язык программирования", "Найдено вакансий", "Обработано вакансий", "Средняя зарплата"]
    ]
    for language, language_stat in statistics.items():
        if language_stat["vacancies_found"]:  # Избавились от > 0
            table_data.append([
                language,
                language_stat["vacancies_found"],
                language_stat["vacancies_processed"],
                language_stat["average_salary"]
            ])
    table = AsciiTable(table_data)
    table.title = f"{site_name} Moscow"
    print(table.table)
    print()


def main():
    load_dotenv()
    superjob_api_key = os.getenv("SUPERJOB_SECRET_KEY")

    print("Сбор статистики с HeadHunter...\n")
    hh_statistics = {}
    for language in LANGUAGES:
        print(f"HeadHunter: {language}")
        hh_statistics[language] = collect_statistics(
            lambda page, lang=language: fetch_hh_vacancies(lang, page),
            extract_hh_items,
            get_hh_total,
            predict_rub_salary_hh
        )
        time.sleep(0.5)

    print("\nСбор статистики с SuperJob...\n")
    sj_statistics = {}
    for language in LANGUAGES:
        print(f"SuperJob: {language}")
        sj_statistics[language] = collect_statistics(
            lambda page, lang=language: fetch_sj_vacancies(lang, superjob_api_key, page),
            extract_sj_items,
            get_sj_total,
            predict_rub_salary_sj
        )
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print_statistics_table(hh_statistics, "HeadHunter")
    print_statistics_table(sj_statistics, "SuperJob")


if __name__ == "__main__":
    main()