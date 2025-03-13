import requests
import sys
import urllib.request
import urllib.parse
import subprocess
import json

def run_tests():
    base_url = "https://post-pitch-fork.onrender.com"
    test_url = "https://example.com"
    results = {}
    
    # Record environment info
    results["environment"] = {
        "python_version": sys.version,
        "requests_version": requests.__version__,
        "platform": sys.platform
    }
    
    # Test 1: Basic connectivity
    try:
        url = f"{base_url}/test"
        response = requests.get(url, timeout=30)
        results["basic_test"] = {
            "url": url,
            "status_code": response.status_code,
            "content": response.text
        }
    except Exception as e:
        results["basic_test"] = {"error": str(e)}
    
    # Test 2: Simple URL parameter
    try:
        url = f"{base_url}/email_data_lenient?url={test_url}"
        response = requests.get(url, timeout=30)
        results["simple_test"] = {
            "url": url,
            "status_code": response.status_code,
            "content_preview": response.text[:200] if response.status_code == 200 else response.text
        }
    except Exception as e:
        results["simple_test"] = {"error": str(e)}
    
    # Test 3: Encoded URL parameter
    try:
        encoded_url = urllib.parse.quote_plus(test_url)
        url = f"{base_url}/email_data_lenient?url={encoded_url}"
        response = requests.get(url, timeout=30)
        results["encoded_test"] = {
            "url": url,
            "encoded_param": encoded_url,
            "status_code": response.status_code,
            "content_preview": response.text[:200] if response.status_code == 200 else response.text
        }
    except Exception as e:
        results["encoded_test"] = {"error": str(e)}
    
    # Test 4: Minimal headers
    try:
        url = f"{base_url}/email_data_lenient?url={test_url}"
        headers = {
            'User-Agent': 'curl/7.68.0',
            'Accept': '*/*'
        }
        response = requests.get(url, headers=headers, timeout=30)
        results["headers_test"] = {
            "url": url,
            "headers": headers,
            "status_code": response.status_code,
            "content_preview": response.text[:200] if response.status_code == 200 else response.text
        }
    except Exception as e:
        results["headers_test"] = {"error": str(e)}
    
    # Test 5: Curl subprocess
    try:
        url = f"{base_url}/email_data_lenient?url={test_url}"
        process = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        results["curl_test"] = {
            "url": url,
            "return_code": process.returncode,
            "stdout": process.stdout[:200],
            "stderr": process.stderr
        }
    except Exception as e:
        results["curl_test"] = {"error": str(e)}
    
    # Test 6: Urllib
    try:
        url = f"{base_url}/email_data_lenient?url={test_url}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            results["urllib_test"] = {
                "url": url,
                "status_code": response.status,
                "content_preview": content[:200]
            }
    except Exception as e:
        results["urllib_test"] = {"error": str(e)}
    
    return results

if __name__ == "__main__":
    results = run_tests()
    print(json.dumps(results, indent=2)) 