from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import requests
import os
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# %%
def get_top_feeds(**context):
    url = "https://medium2.p.rapidapi.com/topfeeds/data-science/top_week"

    headers = {
        "x-rapidapi-key": os.getenv("x-rapidapi-key"),
    	"x-rapidapi-host": "medium2.p.rapidapi.com",
    	"Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    return response.json()['topfeeds'][:10]

def get_my_previous_articles(**context):
    url = "https://medium2.p.rapidapi.com/user/2396262649cc/articles"

    #querystring = {"next":"1625519209064"}

    headers = {
    	"x-rapidapi-key": os.getenv("x-rapidapi-key"),
    	"x-rapidapi-host": "medium2.p.rapidapi.com",
    	"Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    return response.json()['associated_articles']

def get_article_text_top(**context):
    articles = context['task_instance'].xcom_pull(task_ids='extract_TOP_10.extract_task_TOP_10')
    texts = str()
    for article in articles:
        url = f"https://medium2.p.rapidapi.com/article/{article}"

        headers = {
        	"x-rapidapi-key": os.getenv("x-rapidapi-key"),
        	"x-rapidapi-host": "medium2.p.rapidapi.com",
        	"Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        print(response.json())
        texts += response.json()['title'] + " " + response.json()['subtitle'] + "\n"

    return texts

def get_article_text_previous(**context):
    articles = context['task_instance'].xcom_pull(task_ids='extract_previous_articles.extract_task_previous_articles')
    texts = str()
    for article in articles:
        url = f"https://medium2.p.rapidapi.com/article/{article}"

        headers = {
        	"x-rapidapi-key": os.getenv("x-rapidapi-key"),
        	"x-rapidapi-host": "medium2.p.rapidapi.com",
        	"Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        print(response.json())
        texts += response.json()['title'] + " " + response.json()['subtitle'] + "\n"

    return texts

def get_article(**context):
    texts = context['task_instance'].xcom_pull(task_ids='body_TOP_10.body_task_TOP_10')
    previous_articles = context['task_instance'].xcom_pull(task_ids='body_previous_articles.body_task_previous_articles')
    client = OpenAI(api_key=os.getenv("openai_api_key"))
    message = client.chat.completions.create(
        max_completion_tokens=2000,
        messages=[{
            "content": f"create an new article, of only one topic, the article must develop a solution in python, include code examples. Don't use any hook phrases and don't make it sound it is AI written. Don't writre about what I have previously written:{previous_articles}, considering what people are writing about in the top 10 data science articles on medium this week, using the following information format it to be published in Medium: {texts}.\
                The article should be original and not copy any of the content from the top 10 articles, but it should be inspired by the topics and themes that are being discussed in those articles. The article should be well-written and engaging, and it should provide value to readers who are interested in data science.\
                Follow these rules: Do NOT use Markdown headings (#, ##, ###) or HTML tags. Write headings as plain text lines that look like titles. Leave one blank line between paragraphs. Use Unicode symbols for decoration (e.g., ✦ ⸻ → ✓). Use short paragraphs, clean spacing, and Medium-friendly formatting. Use bullet points with simple characters like “•” or “–”. Do not wrap text in code blocks unless it is actual code. Do not include any Markdown formatting like **bold** or _italic_. The output must be fully ready to paste into Medium with no further editing.",
            "role": "user",
        }],
        model="gpt-5.4",
        temperature=0.6)
    return message.choices[0].message.to_dict()['content']

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
to_email="matedataandai@gmail.com"
subject="this weeks article for medium"

def send_email(to_email=to_email, subject=subject, **context):
    body = context['task_instance'].xcom_pull(task_ids='write_article.write_task')
    # Create the email
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    # Connect to Gmail SMTP server
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


with DAG(
    dag_id="etl_single_dag",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:

    # ---- EXTRACT TOP 10----
    with TaskGroup("extract_TOP_10") as extract_top_group:
        extract_task_TOP_10 = PythonOperator(
            task_id="extract_task_TOP_10",
            python_callable=get_top_feeds,
        )

    # ---- BODY TOP 10----
    with TaskGroup("body_TOP_10") as body_top_group:
        body_task_TOP_10 = PythonOperator(
            task_id="body_task_TOP_10",
            python_callable=get_article_text_top,
        )

    # ---- EXTRACT PREVIOUS ARTICLES----
    with TaskGroup("extract_previous_articles") as extract_previous_group:
        extract_task_previous_articles = PythonOperator(
            task_id="extract_task_previous_articles",
            python_callable=get_my_previous_articles,
        )

    # ---- BODY body_task_previous----
    with TaskGroup("body_previous_articles") as body_previous_group:
        body_task_previous_articles = PythonOperator(
            task_id="body_task_previous_articles",
            python_callable=get_article_text_previous,
        )

    # ---- WRITE ARTICLE ----
    with TaskGroup("write_article") as write_article_group:
        write_task = PythonOperator(
            task_id="write_task",
            python_callable=get_article,
        )

    # ---- LOAD ----
    with TaskGroup("send_email") as send_email_group:
        send_email_task = PythonOperator(
            task_id="send_email_task",
            python_callable=send_email,
        )

    extract_top_group >> body_top_group
    extract_previous_group >> body_previous_group
    [body_top_group, body_previous_group] >> write_article_group >> send_email_group