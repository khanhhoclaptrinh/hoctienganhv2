from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import subprocess
import logging
import requests
from bs4 import BeautifulSoup
import sys
import io
import os

app = Flask(__name__)
CORS(app)

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)

# Đường dẫn đến thư mục data
data_dir = 'data'
DATA_FILE_PATH = 'data/data.json' 
# Đảm bảo thư mục data tồn tại
if not os.path.exists(data_dir):
  os.makedirs(data_dir)

# Đường dẫn đầy đủ đến file data.json
DATA_FILE_PATH = os.path.join(data_dir, 'data.json')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_audio_link(word):
  """
  Hàm này lấy audio link từ Cambridge Dictionary cho một từ vựng.

  Args:
      word: Từ vựng cần lấy audio link.

  Returns:
      Audio link (chuỗi) hoặc None nếu không tìm thấy.
  """
  url = f"https://dictionary.cambridge.org/dictionary/english/{word}"
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
  }
  try:
      response = requests.get(url, headers=headers)
      response.raise_for_status()  # Kiểm tra lỗi HTTP
      soup = BeautifulSoup(response.content, "html.parser")
      audio_element = soup.find("source", type="audio/mpeg")
      if audio_element:
          return "https://dictionary.cambridge.org" + audio_element["src"]
      else:
          return None
  except requests.exceptions.RequestException as e:
      app.logger.error(f"Lỗi khi truy cập trang web cho từ '{word}': {e}")
      return None

def process_audio_links():
  try:
      with open(DATA_FILE_PATH, 'r', encoding='utf-8') as file:
          data = json.load(file)
  except FileNotFoundError:
      app.logger.error(f"File {DATA_FILE_PATH} không tồn tại.")
      return False
  except json.JSONDecodeError:
      app.logger.error(f"Lỗi khi đọc file JSON {DATA_FILE_PATH}.")
      return False

  for word_data in data["words"]:
      word = word_data["word"]
      audio_link = get_audio_link(word)
      if audio_link:
          word_data["audioUrl"] = audio_link
      else:
          app.logger.warning(f"Không tìm thấy audio link cho từ '{word}'")

  with open(DATA_FILE_PATH, 'w', encoding='utf-8') as file:
      json.dump(data, file, ensure_ascii=False, indent=2)
  app.logger.info("Đã cập nhật audioUrl trong file data.json")
  return True

@app.route('/process_vocabulary', methods=['POST'])
def process_vocabulary():
  app.logger.info("Received request to /process_vocabulary")
  try:
      data = request.json
      app.logger.debug(f"Received data: {data}")

      if not data or 'vocabulary' not in data:
          app.logger.error("No vocabulary data provided")
          return jsonify({"error": "No vocabulary data provided", "success": False}), 400

      vocabulary = data['vocabulary']
      
      try:
          vocab_data = json.loads(vocabulary)
          app.logger.debug(f"Parsed vocabulary data: {vocab_data}")
      except json.JSONDecodeError as e:
          app.logger.error(f"Invalid JSON format: {str(e)}")
          return jsonify({"error": "Invalid JSON format", "success": False}), 400

      if "words" not in vocab_data or not isinstance(vocab_data["words"], list):
          app.logger.error("Invalid JSON structure")
          return jsonify({"error": "Invalid JSON structure", "success": False}), 400

      try:
          with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
              json.dump(vocab_data, f, ensure_ascii=False, indent=2)
          app.logger.info("Data written to data.json successfully")
      except IOError as e:
          app.logger.error(f"Error writing to file: {str(e)}")
          return jsonify({"error": "Error writing to file", "success": False}), 500

      if process_audio_links():
          return jsonify({
              "message": "Data processed and updated successfully. You can now download the file.",
              "success": True
          })
      else:
          return jsonify({"error": "Error processing audio links", "success": False}), 500

  except Exception as e:
      app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
      return jsonify({"error": "An unexpected error occurred", "success": False}), 500

@app.route('/download_vocabulary', methods=['GET'])
def download_vocabulary():
  try:
      return send_file(DATA_FILE_PATH, as_attachment=True, download_name='data.json')
  except Exception as e:
      app.logger.error(f"Error downloading file: {str(e)}")
      return jsonify({"error": "Error downloading file", "success": False}), 500

if __name__ == '__main__':
  app.run(debug=True, port=5000)

# Created/Modified files during execution:
print(DATA_FILE_PATH)