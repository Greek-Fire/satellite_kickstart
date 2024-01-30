import requests
import yaml
import argparse
import csv
from urllib3.exceptions import InsecureRequestWarning


class APIClient:
    def __init__(self, config_path):
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            self.base_url    = config['aap_url']
            self.verify_ssl  = config['verify_ssl']
            self.report_path = config.get('report_path', '') 

            self.username = config['username']
            self.password = config['password']

        except FileNotFoundError:
            print(f"Error: The file '{config_path}' was not found.")
            exit(1)  # Exit the program
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in '{config_path}': {e}")
            exit(1)
        except KeyError as e:
            print(f"Error: The key '{e}' is missing in the configuration file.")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            exit(1)

    def count_hosts_and_statuses(self, log_content):
        host_status_counts = {
            'total_hosts': 0,
            'total_unreachable': 0,
            'total_failed': 0,
            'success': 0
        }
        lines = log_content.split('\n')

        if not any("PLAY RECAP" in line for line in lines):
            print("No hosts found in the log.")
            return {}

        for line in lines:
            # Check for lines indicating host status
            if 'fatal=' in line or 'changed=' in line or 'ok=' in line:
                host_status_counts['total_hosts'] += 1
                if 'unreachable=' in line:
                    host_status_counts['total_unreachable'] += 1
                elif 'failed=' in line and not 'failed=0' in line:
                    host_status_counts['total_failed'] += 1

        # Calculating hosts not unreachable or failed
        host_status_counts['success'] = \
            host_status_counts['total_hosts'] - host_status_counts['total_unreachable'] - host_status_counts['total_failed']

        return host_status_counts

    def get_data(self):
        results = []
        pages = None

        while True:

            if pages is None:
                pages = '/api/v2/jobs?page_size=100'

            url = f'{self.base_url}/{pages}'
            response = requests.get(url, auth=(self.username, self.password), verify=self.verify_ssl)
            data = response.json()

            for job in data['results']:
                job_stdout_url = f'{self.base_url}/api/v2/jobs/{job["id"]}/stdout/?format=txt'
                job_response = requests.get(job_stdout_url, auth=(self.username,self.password), verify=self.verify_ssl)
                count = self.count_hosts_and_statuses(job_response.text)

                if count:  # Skip jobs with no hosts
                    count['name'] = job['name']
                    count['id'] = job['id']
                    results.append(count)
                    print(count)

            pages = data['next']

            if pages is None:
                break

        return results

class ReportGenerator:
    def __init__(self, data, report_path):
        self.data = data
        self.report_path = report_path

    def generate_report(self, file_name='report.csv'):
        # Use self.report_path to determine the full path
        full_file_path = f'{self.report_path}/{file_name}' if self.report_path else file_name

        headers = ['Name', 'total_hosts', 'success', 'total_unreachable', 'total_failed','job_id']
        with open(full_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

            for job in self.data:
                row = [job['name'], job['total_hosts'], job['success'], job['total_unreachable'], job['total_failed'], job['id']]
                writer.writerow(row)

        print(f"Report generated: {full_file_path}")

class CLI:
    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        parser = argparse.ArgumentParser(description="CLI tool to fetch data from AAP API and generate reports")
        parser.add_argument("--config", type=str, default='/home/fake_user/.config.yml', help="Path to the config YAML file. Config key options: aap_url, token, verify_ssl, report_path")

        args = parser.parse_args()
        self.config_path = args.config
        self.client = APIClient(self.config_path)

    def run(self):
        data = self.client.get_data()
        report_generator = ReportGenerator(data, self.client.report_path)
        report_generator.generate_report()

def main():
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    main()