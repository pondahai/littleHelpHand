import tkinter as tk
from tkinter import scrolledtext
import pyperclip
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 創建主視窗
root = tk.Tk()
root.title("AI助手")
root.geometry("500x600")
root.attributes('-topmost', True)  # 永遠置頂

# 創建 PanedWindow
paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=5, sashrelief=tk.RAISED)
paned_window.pack(fill=tk.BOTH, expand=True)

def check_urls(urls, max_workers=10):
    """
    多线程检查多个网址的响应，返回第一个响应成功的网址。

    Args:
        urls (list): 要检查的网址列表。
        max_workers (int, optional): 线程池中的最大工作线程数。默认为10。

    Returns:
        str: 第一个响应成功的网址，如果全部失败则返回 None。
        dict: 包含每个网址的响应状态和响应时间的字典。
    """

    results = {}

    def check_url(url):
        start_time = time.time()
        try:
            response = requests.get(url)
            response.raise_for_status()
            end_time = time.time()
            return url, True, end_time - start_time
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            return url, False, end_time - start_time

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check_url, url) for url in urls]
        for future in as_completed(futures):
            url, success, duration = future.result()
            results[url] = {'success': success, 'duration': duration}
            if success:
                return url, results

    return None, results


# 定義API請求參數
# API_URL = "http://raspberrypi.local:1234/v1/chat/completions"
# API_URL = "http://ubuntu:1234/v1/chat/completions"
API_URL = ""
HEADERS = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}


def stream_chat_completions(api_payload, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(API_URL, headers=HEADERS, json=api_payload, stream=True)
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data:'):
#                             print(decoded_line[5:])
                            if "[DONE]" in decoded_line[5:]:
                                return
                            json_data = json.loads(decoded_line[5:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                content = json_data['choices'][0]['delta'].get('content')
                                if content:
                                    yield content
                return  # 成功完成，退出循環
            else:
                print(f"Error: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")
        except ValueError as e:
            print("error")
            print(decoded_line[5:])
        retries += 1
        print(f"Retrying ({retries}/{max_retries})...")
        time.sleep(2)  # 等待一段時間再重試

    print("Max retries reached. Giving up.")

# 流式輸出函數
def stream_output(text_widget, api_payload):
#     response = requests.post(API_URL, headers=HEADERS, json=api_payload, stream=True)
    text_widget.delete(1.0, tk.END)
    for chunk in stream_chat_completions(api_payload):
#     for chunk in response.iter_content(chunk_size=8192):
        if chunk:
#             text_widget.insert(tk.END, chunk.decode('utf-8'))
            text_widget.insert(tk.END, chunk)
            text_widget.see(tk.END)  # 自動滾動到最後
            text_widget.update()

# 翻譯區塊
def translate_text_function():
    clipboard_content = pyperclip.paste()
    api_payload = {
#         "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": "以zh_TW回答"}, {"role": "user", "content": clipboard_content + " 翻譯成zh_TW"}],
        "stream": True
    }
    stream_output(translate_text, api_payload)

translate_frame = tk.Frame(paned_window)
paned_window.add(translate_frame)
# translate_frame.pack(pady=10)

translate_label = tk.Label(translate_frame, text="翻譯")
translate_label.pack(anchor='w')

translate_text = scrolledtext.ScrolledText(translate_frame, height=7)
translate_text.pack(fill=tk.BOTH, expand=True)

translate_button = tk.Button(translate_frame, text="執行翻譯", command=translate_text_function)
translate_button.pack(pady=5, anchor='w')

# 總結區塊
def summarize_text_function():
    clipboard_content = pyperclip.paste()
    api_payload = {
#         "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": "以zh_TW回答"}, {"role": "user", "content": clipboard_content + " 以zh_TW做出總結:"}],
        "stream": True
    }
    stream_output(summary_text, api_payload)

summary_frame = tk.Frame(paned_window)
paned_window.add(summary_frame)
# summary_frame.pack(pady=10)

summary_label = tk.Label(summary_frame, text="總結")
summary_label.pack(anchor='w')

summary_text = scrolledtext.ScrolledText(summary_frame, height=7)
summary_text.pack(fill=tk.BOTH, expand=True)

summary_button = tk.Button(summary_frame, text="執行總結", command=summarize_text_function)
summary_button.pack(pady=5, anchor='w')

# 對話區塊
def chat_function():
    user_input = f"\n 基於內容 \n"
    if not chat_history.compare("end-1c", "==", "1.0"):
        user_input += f"上一輪回答\n" + chat_history.get(1.0, tk.END)
    if not translate_text.compare("end-1c", "==", "1.0"):
        user_input += f"翻譯內容\n" + translate_text.get(1.0, tk.END)
    if not summary_text.compare("end-1c", "==", "1.0"):
        user_input += f"總結內容\n" + summary_text.get(1.0, tk.END)
    user_input += chat_input.get(1.0,tk.END)
    user_input += f"\n reply me in zh_TW."
    
    chat_history.insert(tk.END, f"User: {user_input}\n")
    chat_input.delete(1.0, tk.END)
    
    api_payload = {
#         "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_input}],
        "stream": True
    }
#     print(api_payload)
    stream_output(chat_history, api_payload)

chat_frame = tk.Frame(paned_window)
paned_window.add(chat_frame)
# chat_frame.pack(pady=10)

chat_history = scrolledtext.ScrolledText(chat_frame, height=7)
chat_history.pack(fill=tk.BOTH, expand=True)


input_frame = tk.Frame(paned_window)
paned_window.add(input_frame)

chat_input = tk.Text(input_frame, width=20, height=1)
chat_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

chat_button = tk.Button(input_frame, text="發送", command=chat_function)
chat_button.pack(side=tk.LEFT, padx=5)

# 清除按鈕
def clear_all():
    translate_text.delete(1.0, tk.END)
    summary_text.delete(1.0, tk.END)
    chat_history.delete(1.0, tk.END)
    chat_input.delete(1.0, tk.END)

clear_button = tk.Button(root, text="清除所有內容", command=clear_all)
clear_button.pack(pady=10)

# API_URL = "http://raspberrypi.local:1234/v1/chat/completions"
# API_URL = "http://ubuntu:1234/v1/chat/completions"

urls = ["","",""]
urls[0] = "http://raspberrypi.local:1234"
urls[1] = "http://ubuntu:1234"
urls[2] = "http://localhost:1234"
first_response_url, all_results = check_urls(urls)

if first_response_url:
    print(f"第一个响应成功的网址是：{first_response_url}")
    API_URL = first_response_url + "/v1/chat/completions"
    print("所有网址的响应结果：")
    for url, result in all_results.items():
        print(f"{url}: {'成功' if result['success'] else '失败'}, 用时 {result['duration']:.2f} 秒")
else:
    print("所有网址都无法访问")
    
# 啟動主迴圈
root.mainloop()
