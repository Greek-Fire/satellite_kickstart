import requests
import yaml
import argparse
import csv
from urllib3.exceptions import InsecureRequestWarning


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

            self.base_url = config['aap_url']
            self.verify_ssl = config['verify_ssl']
            self.report_path = config.get('report_path', 'report.csv') 
            self.token = config['token']

            # Create a session object
            self.session = requests.Session()
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})  # Set token in session headers
            self.session.verify = self.verify_ssl  # Set SSL verification

        except FileNotFoundError:
            print(f"Error: The file '{config_path}' was not found.")
            exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in '{config_path}': {e}")
            exit(1)
        except KeyError as e:
            print(f"Error: The key '{e}' is missing in the configuration file.")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            exit(1)

    def count_hosts_and_statuses(self, log_content, job):
        time = job['finished'].split('T')
        host_status_counts = {

            'id': job['id'], 
            'name': job['name'], 
            'date': time[0],
            'time': time[1][:8],
            'total_hosts': 0,
            'success': 0, 
            'unreachable': 0, 
            'failed': 0,
            'skipped': 0,
            'rescued': 0,
            'ignored': 0,
            'canceled': 'false',
            'inventory_failed': 'false',
            'project_failed': 'false',
            'ansible_failed': 'false'
        }

        lines = log_content.split('\n')

        # Check if the log contains any hosts
        if lines == ['']:
            host_status_counts['inventory_failed'] = "inventory_update" in job['job_explanation']
            host_status_counts['project_failed'] = "project_update" in job['job_explanation']
            print(job['id'], job['job_explanation'])
            return host_status_counts

        if not any("PLAY RECAP" in line for line in lines):
            host_status_counts['ansible_failed'] = 'true'
            return host_status_counts

        for line in lines:
            # Check for lines indicating host status
            if 'changed=' in line or 'ok=' in line or 'unreachable=' in line or 'failed=' in line or 'ignored=' in line or 'skipped=' in line or 'rescued=' in line:
                host_status_counts['total_hosts'] += 1

                # Extract values for ok, unreachable, and failed
                ok_count = int(line.split('ok=')[1].split()[0])
                unreachable_count = int(line.split('unreachable=')[1].split()[0])
                failed_count  = int(line.split('failed=')[1].split()[0])
                skipped_count = int(line.split('skipped=')[1].split()[0])
                rescued_count = int(line.split('rescued=')[1].split()[0])
                ignored_count = int(line.split('ignored=')[1].split()[0])

                if unreachable_count > 0:
                    host_status_counts['unreachable'] += 1

                if failed_count > 0:
                    host_status_counts['failed'] += 1

                if ok_count > 0 and unreachable_count == 0 and failed_count == 0:
                    host_status_counts['success'] += 1

                if ok_count == 0 and unreachable_count == 0 and failed_count == 0 and skipped_count > 0:
                    host_status_counts['skipped'] += 1

                if rescued_count > 0:
                    host_status_counts['rescued'] += 1

                if ignored_count > 0:
                    host_status_counts['ignored'] += 1

        return host_status_counts

    def get_data(self):
        results = []
        pages = None

        while True:

            if pages is None:
                pages = '/api/v2/jobs?page_size=100'

            url = f'{self.base_url}/{pages}'
            response = self.session.get(url)
            data = response.json()

            for job in data['results']:
                time = job['finished'].split('T')
                if job['status'] == 'canceled':
                    results.append({
                                    'id': job['id'], 
                                    'name': job['name'], 
                                    'date': time[0],
                                    'time': time[1][:8],
                                    'total_hosts': 0,
                                    'success': 0, 
                                    'unreachable': 0, 
                                    'failed': 0,
                                    'skipped': 0,
                                    'rescued': 0,
                                    'ignored': 0,
                                    'canceled': 'true',
                                    'inventory_failed': 'false',
                                    'project_failed': 'false',
                                    'ansible_failed': 'false'
                                    })
                    continue

                job_stdout_url = f'{self.base_url}/api/v2/jobs/{job["id"]}/stdout/?format=txt'
                job_response = self.session.get(job_stdout_url)
                count = self.count_hosts_and_statuses(job_response.text, job)

                if count:  # Skip jobs with no hosts
                    results.append(count)
                    #print(count)

            pages = data['next']

            if pages is None:
                break

        return results

class ReportGenerator:
    def __init__(self, data, report_path):
        self.data = data
        self.report_path = report_path

    def generate_report(self):
        # Use self.report_path to determine the full path
        full_file_path = f'{self.report_path}'

        headers = ['ID','Name', 'Date','Time', 'total_hosts', 'success', 'unreachable', 'failed','skipped','rescued','ignored','canceled','inventory_failed','project_failed','ansible_failed']
        with open(full_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

            for job in self.data:
                row = [job['id'], job['name'], job['date'], job['time'], job['total_hosts'], job['success'], job['unreachable'], job['failed'], job['skipped'], job['rescued'], job['ignored'],job['canceled'], job['inventory_failed'], job['project_failed'], job['ansible_failed']]
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