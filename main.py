import requests
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import threading

# Function to extract parameters from a URL

visited_urls = set()


def extract_parameters(url):
    parsed_url = urlparse(url)
    query = parsed_url.query

    # Initialize a dictionary with a default value of "SHDRM" for empty parameters
    default_value = "SHDRM"

    # Parse the query parameters and handle empty parameters
    query_params = {}
    for param in query.split('&'):
        if '=' in param:
            param_name, param_value = param.split('=')
            query_params[param_name] = default_value

    return query_params

# Function to extract parameters from form input elements
def extract_parameters_from_form(form):
    params = []
    for input_element in form.find_all('input', {'name': True}):
        param_name = input_element['name']
        params.append(param_name)
    return params

def check_and_convert_url(url):
    if 'https://' not in url:
        if 'http://' not in url:
            url = 'https://' + url
        else:
            url = url

    return url

def has_three_levels(url):
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip('/').split('/')
    if len(path_segments) >=3:
        return True

# Function to check a URL, extract parameters, and follow links within the same domain (1 level deep)
def check_and_extract_parameters(url, output_file):
    try:
        url = check_and_convert_url(url)
        # Check if the URL has already been visited to prevent infinite loops
        if url in visited_urls:
            return

        visited_urls.add(url)  # Mark the URL as visited

        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract parameters from the current URL
            params = extract_parameters(url)

            if params:
                xxx = urlparse(url)
                newURL = f"{xxx.scheme}://{xxx.netloc}"
                qry = ''
                for param in params:
                    qry = f'?{param}=SHDRM' + '&'
                output_file.write(f'{newURL.strip()}{qry.strip()}' + '\n')

            # Check forms and extract parameters
            if 'method="GET"' in str(soup.find_all('form')):
                method = 'GET'
            else:
                method = 'get'

            for form in soup.find_all('form', method=method):
                form_url = urljoin(url, form['action'])
                form_params = extract_parameters_from_form(form)
                if form_params:
                    qry = ''
                    for param in form_params:
                        qry = f'?{param}=SHDRM' + '&'
                    output_file.write(f'{form_url.strip()}{qry.strip()}' + '\n')

            base_url = url

            # Check href links
            for link in soup.find_all(['a'], href=True):
                next_url = urljoin(base_url, link.get('href'))
                if urlparse(next_url).netloc == urlparse(url).netloc:
                    if (next_url in visited_urls) or (has_three_levels(next_url)):
                        return
                    else:
                        check_and_extract_parameters(next_url, output_file)

            # Check src attributes of iframes
            for iframe in soup.find_all('iframe', src=True):
                iframe_url = urljoin(base_url, iframe.get('src'))
                if urlparse(iframe_url).netloc == urlparse(url).netloc:
                    if (iframe_url in visited_urls) or (has_three_levels(iframe_url)):
                        return
                    else:
                        check_and_extract_parameters(iframe_url, output_file)

    except Exception as e:
        pass

# Function to process a list of URLs from a file
def process_urls_from_file(file_path, output_file_path, num_threads):
      # Keep track of visited URLs to prevent infinite loops
    urls_lock = threading.Lock()  # Lock for accessing the list of URLs

    with open(file_path, "r") as url_file:
        urls = url_file.read().splitlines()

    # Create a list to hold threads
    threads = []

    def worker():
        while True:
            with urls_lock:
                if not urls:
                    break  # No more URLs to process

                url = urls.pop()

            with open(output_file_path, "a") as output_file:
                check_and_extract_parameters(url, output_file)

    # Create and start multiple threads
    for _ in range(num_threads):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="URL Parameter Extractor (1 Level Deep with Nested Links and Forms)")
    parser.add_argument("url_file", help="Path to a file containing a list of seed URLs")
    parser.add_argument("--threads", type=int, default=50, help="Number of threads to use (default: 50)")
    args = parser.parse_args()

    output_file_path = "PARAM_READY.txt"
    process_urls_from_file(args.url_file, output_file_path, args.threads)

    print(f"Finished checking parameters of the URLs from {args.url_file} and their 1-level deep links. Results saved in {output_file_path}.")
