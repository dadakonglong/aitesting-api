import requests
import json

def do_import():
    url = "http://127.0.0.1:8000/api/v1/import/swagger"
    project_id = "ms-增值项目"
    file_path = r"d:\testc\aitesting-api\Swagger_Api_增值项目.json"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'project_id': project_id}
        response = requests.post(url, files=files, data=data)
        print(response.json())

if __name__ == "__main__":
    do_import()
